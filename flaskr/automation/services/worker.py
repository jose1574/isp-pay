from datetime import date
from flask import current_app
from sqlalchemy import text

from flaskr import conn_mikrotik, db
from flaskr.subscriptions.services.querys import (
	create_receivable_for_overdue_subscription,
	get_due_active_subscriptions,
	get_overdue_active_subscriptions,
	update_subscription_status,
)


def _get_reference_date() -> date | None:
	configured_date = current_app.config.get('AUTOMATION_REFERENCE_DATE')
	if not configured_date:
		return date.today()

	if isinstance(configured_date, date):
		return configured_date

	try:
		return date.fromisoformat(str(configured_date))
	except ValueError:
		current_app.logger.warning(
			'AUTOMATION_REFERENCE_DATE invalida: %s. Se usara CURRENT_DATE.',
			configured_date,
		)
		return date.today()


def log_automation_event(
	automation_name: str,
	action: str,
	status: str,
	message: str,
	*,
	client_code: str | None = None,
	subscription_correlative: int | None = None,
	receivable_correlative: int | None = None,
	route_id: int | None = None,
	mac_address: str | None = None,
):
	db.session.execute(
		text(
			"""
			INSERT INTO genius.automation_event_log (
				automation_name,
				action,
				status,
				message,
				client_code,
				subscription_correlative,
				receivable_correlative,
				route_id,
				mac_address
			)
			VALUES (
				:automation_name,
				:action,
				:status,
				:message,
				:client_code,
				:subscription_correlative,
				:receivable_correlative,
				:route_id,
				:mac_address
			)
			"""
		),
		{
			'automation_name': automation_name,
			'action': action,
			'status': status,
			'message': message,
			'client_code': client_code,
			'subscription_correlative': subscription_correlative,
			'receivable_correlative': receivable_correlative,
			'route_id': route_id,
			'mac_address': mac_address,
		},
	)


def get_recent_automation_events(limit: int = 100):
	return db.session.execute(
		text(
			"""
			SELECT
				id,
				automation_name,
				action,
				status,
				message,
				client_code,
				subscription_correlative,
				receivable_correlative,
				route_id,
				mac_address,
				created_at
			FROM genius.automation_event_log
			ORDER BY created_at DESC, id DESC
			LIMIT :limit
			"""
		),
		{'limit': limit},
	).mappings().all()


def create_due_receivables(reference_date=None):
	reference_date = reference_date if reference_date is not None else _get_reference_date()
	due_subscriptions = get_due_active_subscriptions(reference_date=reference_date)
	processed = 0
	created = 0
	errors: list[str] = []

	for subscription in due_subscriptions:
		processed += 1
		subscription_correlative = getattr(subscription, 'correlative', None)
		client_code = getattr(subscription, 'client_code', None)
		route_id = getattr(subscription, 'route_id', None)

		receivable_ok, receivable_result = create_receivable_for_overdue_subscription(
			subscription,
			reference_date=reference_date,
		)
		if not receivable_ok:
			error_text = str(receivable_result)
			errors.append(error_text)
			log_automation_event(
				automation_name='due_subscription_check',
				action='create_receivable',
				status='error',
				message=error_text,
				client_code=client_code,
				subscription_correlative=subscription_correlative,
				route_id=route_id,
			)
		else:
			if receivable_result is not None:
				created += 1
				log_automation_event(
					automation_name='due_subscription_check',
					action='create_receivable',
					status='success',
					message='Cuenta por cobrar creada automaticamente para suscripcion en fecha de corte.',
					client_code=client_code,
					subscription_correlative=subscription_correlative,
					receivable_correlative=int(receivable_result),
					route_id=route_id,
				)
			else:
				log_automation_event(
					automation_name='due_subscription_check',
					action='create_receivable',
					status='info',
					message='La cuenta por cobrar de la fecha de corte ya existia.',
					client_code=client_code,
					subscription_correlative=subscription_correlative,
					route_id=route_id,
				)

	if processed == 0:
		log_automation_event(
			automation_name='due_subscription_check',
			action='run_summary',
			status='info',
			message='No se encontraron suscripciones en fecha de corte para generar cuentas por cobrar.',
		)
	else:
		log_automation_event(
			automation_name='due_subscription_check',
			action='run_summary',
			status='success',
			message=(
				f'Proceso de generar cuentas por cobrar en fecha de corte finalizado: '
				f'procesadas={processed}, creadas={created}, errores={len(errors)}.'
			),
		)

	return {
		'processed': processed,
		'created': created,
		'errors': errors,
		'reference_date': reference_date,
	}


def process_subscription_billing(reference_date=None):
	reference_date = reference_date if reference_date is not None else _get_reference_date()
	due_result = create_due_receivables(reference_date=reference_date)
	overdue_result = suspend_overdue_subscriptions(reference_date=reference_date)
	return {
		'reference_date': reference_date,
		'due_processed': due_result['processed'],
		'due_created': due_result['created'],
		'overdue_processed': overdue_result['processed'],
		'suspended': overdue_result['suspended'],
		'errors': due_result['errors'] + overdue_result['errors'],
	}


def client_activation(mac_address: str, route_id=None, enabled: bool = True):
	conn_mk = conn_mikrotik(route_id)
	if not mac_address:
		return False, 'La direccion MAC es obligatoria.'

	leases, exito = conn_mk.query('/ip/dhcp-server/lease')
	if not exito:
		return False, leases

	if isinstance(leases, dict):
		leases = [leases]

	if not isinstance(leases, list):
		return False, 'Respuesta invalida del MikroTik al consultar leases DHCP.'

	normalized_mac = mac_address.strip().upper()
	compact_mac = normalized_mac.replace(':', '').replace('-', '')
	if len(compact_mac) == 12:
		normalized_mac = ':'.join(compact_mac[index:index + 2] for index in range(0, 12, 2))

	lease_id = None
	for lease in leases:
		if not isinstance(lease, dict):
			continue

		lease_mac = (lease.get('mac-address') or '').upper()
		if lease_mac == normalized_mac:
			lease_id = lease.get('.id') or lease.get('id')
			break

	if not lease_id:
		return False, f'No se encontro una lease DHCP para la MAC {normalized_mac}.'

	block_access = 'no' if enabled else 'yes'
	ok, error_message = conn_mk.set_dhcp_lease_block_access(lease_id, block_access)
	if not ok:
		return False, error_message

	status_text = 'activado' if enabled else 'desactivado'
	return True, f'Cliente {status_text} correctamente.'


def suspend_overdue_subscriptions(reference_date=None):
	reference_date = reference_date if reference_date is not None else _get_reference_date()
	overdue_subscriptions = get_overdue_active_subscriptions(reference_date=reference_date)
	processed = 0
	suspended = 0
	receivables_created = 0
	errors: list[str] = []

	for subscription in overdue_subscriptions:
		processed += 1
		subscription_correlative = getattr(subscription, 'correlative', None)
		client_code = getattr(subscription, 'client_code', None)
		route_id = getattr(subscription, 'route_id', None)

		receivable_ok, receivable_result = create_receivable_for_overdue_subscription(
			subscription,
			reference_date=reference_date,
		)
		if not receivable_ok:
			error_text = str(receivable_result)
			errors.append(error_text)
			log_automation_event(
				automation_name='overdue_subscription_check',
				action='create_receivable',
				status='error',
				message=error_text,
				client_code=client_code,
				subscription_correlative=subscription_correlative,
				route_id=route_id,
			)
			db.session.commit()
			continue
		else:
			# Si receivable_result es None, ya existia una cuenta por cobrar para esta emision.
			if receivable_result is not None:
				receivables_created += 1
				log_automation_event(
					automation_name='overdue_subscription_check',
					action='create_receivable',
					status='success',
					message='Cuenta por cobrar creada automaticamente para suscripcion vencida.',
					client_code=client_code,
					subscription_correlative=subscription_correlative,
					receivable_correlative=int(receivable_result),
					route_id=route_id,
				)
			else:
				log_automation_event(
					automation_name='overdue_subscription_check',
					action='create_receivable',
					status='info',
					message='La cuenta por cobrar del periodo ya existia; no se genero una nueva.',
					client_code=client_code,
					subscription_correlative=subscription_correlative,
					route_id=route_id,
				)

		mac_address = getattr(subscription, 'installation_mac_address', None)
		if not mac_address:
			error_text = f'Suscripcion {subscription.correlative} sin MAC asociada para suspension automatica.'
			errors.append(error_text)
			log_automation_event(
				automation_name='overdue_subscription_check',
				action='suspend_subscription',
				status='error',
				message=error_text,
				client_code=client_code,
				subscription_correlative=subscription_correlative,
				route_id=route_id,
			)
			db.session.commit()
			continue

		ok, message = client_activation(mac_address, route_id, enabled=False)
		if not ok:
			error_text = f'Suscripcion {subscription.correlative}: {message}'
			errors.append(error_text)
			log_automation_event(
				automation_name='overdue_subscription_check',
				action='suspend_subscription',
				status='error',
				message=error_text,
				client_code=client_code,
				subscription_correlative=subscription_correlative,
				route_id=route_id,
				mac_address=mac_address,
			)
			db.session.commit()
			continue

		updated = update_subscription_status(
			correlative=subscription.correlative,
			status='suspendido_por_falta_de_pago',
		)
		if not updated:
			error_text = (
				f'Suscripcion {subscription.correlative}: se suspendio en el router pero no en la base de datos.'
			)
			errors.append(error_text)
			log_automation_event(
				automation_name='overdue_subscription_check',
				action='suspend_subscription',
				status='error',
				message=error_text,
				client_code=client_code,
				subscription_correlative=subscription_correlative,
				route_id=route_id,
				mac_address=mac_address,
			)
			db.session.commit()
			continue

		suspended += 1
		log_automation_event(
			automation_name='overdue_subscription_check',
			action='suspend_subscription',
			status='success',
			message='Suscripcion suspendida automaticamente por falta de pago.',
			client_code=client_code,
			subscription_correlative=subscription_correlative,
			route_id=route_id,
			mac_address=mac_address,
		)
		db.session.commit()

	if processed == 0:
		log_automation_event(
			automation_name='overdue_subscription_check',
			action='run_summary',
			status='info',
			message='No se encontraron suscripciones vencidas para procesar.',
		)
		db.session.commit()
	else:
		log_automation_event(
			automation_name='overdue_subscription_check',
			action='run_summary',
			status='success',
			message=(
				f'Proceso finalizado: procesadas={processed}, suspendidas={suspended}, '
				f'cx_cobrar_creadas={receivables_created}, errores={len(errors)}.'
			),
		)
		db.session.commit()

	return {
		'processed': processed,
		'suspended': suspended,
		'receivables_created': receivables_created,
		'errors': errors,
		'reference_date': reference_date,
	}


def run_overdue_subscription_check() -> None:
	result = suspend_overdue_subscriptions()

	if result['processed']:
		current_app.logger.info(
			'Revision automatica de suscripciones vencidas: fecha=%s procesadas=%s suspendidas=%s errores=%s',
			result['reference_date'] or 'CURRENT_DATE',
			result['processed'],
			result['suspended'],
			len(result['errors']),
		)

	for error in result['errors']:
		current_app.logger.warning(error)


def process_paid_subscription_reactivations(batch_size: int = 100):
	rows = db.session.execute(
		text(
			"""
			SELECT
				q.id,
				q.subscription_correlative,
				q.receivable_correlative,
				q.client_code,
				s.status AS subscription_status,
				i.mac_address AS installation_mac_address,
				i.route_id
			FROM genius.subscription_reactivation_queue q
			LEFT JOIN genius.subscription s ON s.correlative = q.subscription_correlative
			LEFT JOIN genius.installations i ON i.id = s.installation
			WHERE q.status = 'pending'
			ORDER BY q.queued_at ASC
			LIMIT :batch_size
			FOR UPDATE OF q
			"""
		),
		{'batch_size': batch_size},
	).mappings().all()

	processed = 0
	activated = 0
	already_active = 0
	errors: list[str] = []

	for row in rows:
		processed += 1
		queue_id = row['id']
		subscription_correlative = row['subscription_correlative']
		client_code = row['client_code']

		if not subscription_correlative:
			message = (
				f'Cola #{queue_id}: no se pudo resolver subscription_correlative '
				f'para receivable {row["receivable_correlative"]}.'
			)
			errors.append(message)
			db.session.execute(
				text(
					"""
					UPDATE genius.subscription_reactivation_queue
					SET status = 'error', processed_at = NOW(), error_message = :error_message
					WHERE id = :id
					"""
				),
				{'id': queue_id, 'error_message': message},
			)
			db.session.commit()
			log_automation_event(
				automation_name='paid_subscription_reactivation',
				action='reactivate_subscription',
				status='error',
				message=message,
				client_code=client_code,
				receivable_correlative=row['receivable_correlative'],
			)
			db.session.commit()
			continue

		pending_subscription_debts = db.session.execute(
			text(
				"""
				SELECT COUNT(*)
				FROM genius.subscription_receivable_link l
				JOIN public.receivable r ON r.correlative = l.receivable_correlative
				WHERE l.subscription_correlative = :subscription_correlative
				  AND COALESCE(r.balance, COALESCE(r.total, 0) - COALESCE(r.payment_applied, 0)) > 0
				"""
			),
			{
				'subscription_correlative': subscription_correlative,
			},
		).scalar_one()

		if pending_subscription_debts > 0:
			message = (
				f'Suscripcion {subscription_correlative}: pago aplicado, pero aun tiene '
				f'{pending_subscription_debts} deuda(s) de suscripcion pendiente(s).'
			)
			db.session.execute(
				text(
					"""
					UPDATE genius.subscription_receivable_link
					SET payment_status = 'paid_partial_subscription_debt', updated_at = NOW()
					WHERE receivable_correlative = :receivable_correlative
					"""
				),
				{'receivable_correlative': row['receivable_correlative']},
			)
			db.session.execute(
				text(
					"""
					UPDATE genius.subscription_reactivation_queue
					SET status = 'done', processed_at = NOW(), error_message = :error_message
					WHERE id = :id
					"""
				),
				{'id': queue_id, 'error_message': message},
			)
			db.session.commit()
			log_automation_event(
				automation_name='paid_subscription_reactivation',
				action='reactivate_subscription',
				status='info',
				message=message,
				client_code=client_code,
				subscription_correlative=subscription_correlative,
				receivable_correlative=row['receivable_correlative'],
			)
			db.session.commit()
			continue

		subscription_status = row['subscription_status']
		if subscription_status == 'activo':
			already_active += 1
			db.session.execute(
				text(
					"""
					UPDATE genius.subscription_receivable_link
					SET payment_status = 'activated', updated_at = NOW()
					WHERE receivable_correlative = :receivable_correlative
					"""
				),
				{'receivable_correlative': row['receivable_correlative']},
			)
			db.session.execute(
				text(
					"""
					UPDATE genius.subscription_reactivation_queue
					SET status = 'done', processed_at = NOW(), error_message = NULL
					WHERE id = :id
					"""
				),
				{'id': queue_id},
			)
			db.session.commit()
			log_automation_event(
				automation_name='paid_subscription_reactivation',
				action='reactivate_subscription',
				status='info',
				message='La suscripcion ya estaba activa; se marco la cola como procesada.',
				client_code=client_code,
				subscription_correlative=subscription_correlative,
				receivable_correlative=row['receivable_correlative'],
			)
			db.session.commit()
			continue

		mac_address = row['installation_mac_address']
		if not mac_address:
			message = (
				f'Suscripcion {subscription_correlative}: no tiene MAC asociada para reactivacion automatica.'
			)
			errors.append(message)
			db.session.execute(
				text(
					"""
					UPDATE genius.subscription_reactivation_queue
					SET status = 'error', processed_at = NOW(), error_message = :error_message
					WHERE id = :id
					"""
				),
				{'id': queue_id, 'error_message': message},
			)
			db.session.commit()
			log_automation_event(
				automation_name='paid_subscription_reactivation',
				action='reactivate_subscription',
				status='error',
				message=message,
				client_code=client_code,
				subscription_correlative=subscription_correlative,
				receivable_correlative=row['receivable_correlative'],
			)
			db.session.commit()
			continue

		ok, message = client_activation(mac_address, row['route_id'], enabled=True)
		if not ok:
			error_text = f'Suscripcion {subscription_correlative}: {message}'
			errors.append(error_text)
			db.session.execute(
				text(
					"""
					UPDATE genius.subscription_receivable_link
					SET payment_status = 'activation_error', updated_at = NOW()
					WHERE receivable_correlative = :receivable_correlative
					"""
				),
				{'receivable_correlative': row['receivable_correlative']},
			)
			db.session.execute(
				text(
					"""
					UPDATE genius.subscription_reactivation_queue
					SET status = 'error', processed_at = NOW(), error_message = :error_message
					WHERE id = :id
					"""
				),
				{'id': queue_id, 'error_message': error_text},
			)
			db.session.commit()
			log_automation_event(
				automation_name='paid_subscription_reactivation',
				action='reactivate_subscription',
				status='error',
				message=error_text,
				client_code=client_code,
				subscription_correlative=subscription_correlative,
				receivable_correlative=row['receivable_correlative'],
				route_id=row['route_id'],
				mac_address=mac_address,
			)
			db.session.commit()
			continue

		db.session.execute(
			text(
				"""
				UPDATE genius.subscription
				SET status = 'activo'
				WHERE correlative = :correlative
				"""
			),
			{'correlative': subscription_correlative},
		)

		db.session.execute(
			text(
				"""
				UPDATE genius.subscription_receivable_link
				SET payment_status = 'activated', updated_at = NOW()
				WHERE receivable_correlative = :receivable_correlative
				"""
			),
			{'receivable_correlative': row['receivable_correlative']},
		)

		db.session.execute(
			text(
				"""
				UPDATE genius.subscription_reactivation_queue
				SET status = 'done', processed_at = NOW(), error_message = NULL
				WHERE id = :id
				"""
			),
			{'id': queue_id},
		)

		db.session.commit()
		activated += 1
		log_automation_event(
			automation_name='paid_subscription_reactivation',
			action='reactivate_subscription',
			status='success',
			message='Suscripcion reactivada automaticamente al pagar la deuda vinculada.',
			client_code=client_code,
			subscription_correlative=subscription_correlative,
			receivable_correlative=row['receivable_correlative'],
			route_id=row['route_id'],
			mac_address=mac_address,
		)
		db.session.commit()

	if processed == 0:
		log_automation_event(
			automation_name='paid_subscription_reactivation',
			action='run_summary',
			status='info',
			message='No se encontraron pagos pendientes de procesar para reactivacion.',
		)
		db.session.commit()
	else:
		log_automation_event(
			automation_name='paid_subscription_reactivation',
			action='run_summary',
			status='success',
			message=(
				f'Proceso finalizado: procesadas={processed}, activadas={activated}, '
				f'ya_activas={already_active}, errores={len(errors)}.'
			),
		)
		db.session.commit()

	return {
		'processed': processed,
		'activated': activated,
		'already_active': already_active,
		'errors': errors,
	}

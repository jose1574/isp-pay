from datetime import date
from flask import current_app

from flaskr import conn_mikrotik
from flaskr.subscriptions.services.querys import (
	create_receivable_for_overdue_subscription,
	get_overdue_active_subscriptions,
	update_subscription_status,
)


def _get_reference_date() -> date | None:
	configured_date = current_app.config.get('AUTOMATION_REFERENCE_DATE')
	if not configured_date:
		return None

	if isinstance(configured_date, date):
		return configured_date

	try:
		return date.fromisoformat(str(configured_date))
	except ValueError:
		current_app.logger.warning(
			'AUTOMATION_REFERENCE_DATE invalida: %s. Se usara CURRENT_DATE.',
			configured_date,
		)
		return None


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


def suspend_overdue_subscriptions():
	reference_date = _get_reference_date()
	overdue_subscriptions = get_overdue_active_subscriptions(reference_date=reference_date)
	processed = 0
	suspended = 0
	receivables_created = 0
	errors: list[str] = []

	for subscription in overdue_subscriptions:
		processed += 1

		receivable_ok, receivable_result = create_receivable_for_overdue_subscription(
			subscription,
			reference_date=reference_date,
		)
		if not receivable_ok:
			errors.append(str(receivable_result))
		else:
			# Si receivable_result es None, ya existia una cuenta por cobrar para esta emision.
			if receivable_result is not None:
				receivables_created += 1

		mac_address = getattr(subscription, 'installation_mac_address', None)
		if not mac_address:
			errors.append(
				f'Suscripcion {subscription.correlative} sin MAC asociada para suspension automatica.'
			)
			continue

		route_id = getattr(subscription, 'route_id', None)
		ok, message = client_activation(mac_address, route_id, enabled=False)
		if not ok:
			errors.append(f'Suscripcion {subscription.correlative}: {message}')
			continue

		updated = update_subscription_status(
			correlative=subscription.correlative,
			status='suspendido_por_falta_de_pago',
		)
		if not updated:
			errors.append(
				f'Suscripcion {subscription.correlative}: se suspendio en el router pero no en la base de datos.'
			)
			continue

		suspended += 1

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

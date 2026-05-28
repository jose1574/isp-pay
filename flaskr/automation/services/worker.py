import requests
import urllib3
from datetime import date
from flask import current_app
from requests.auth import HTTPBasicAuth

from flaskr import mk_router
from flaskr.subscriptions.services.querys import (
	get_overdue_active_subscriptions,
	update_subscription_status,
)


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


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


def client_activation(mac_address: str, enabled: bool = True):
	if not mac_address:
		return False, 'La direccion MAC es obligatoria.'

	leases, exito = mk_router.query('/ip/dhcp-server/lease')
	if not exito:
		return False, leases

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

	try:
		patch_response = requests.patch(
			f"{mk_router.base_url}/ip/dhcp-server/lease/{lease_id}",
			auth=HTTPBasicAuth(mk_router.auth.username, mk_router.auth.password),
			verify=False,
			timeout=5,
			json={'block-access': block_access},
		)
	except requests.RequestException as error:
		return False, f'No se pudo actualizar el cliente en el MikroTik: {error}'

	if patch_response.status_code not in (200, 204):
		return False, f'Error del router {patch_response.status_code}: {patch_response.text}'

	status_text = 'activado' if enabled else 'desactivado'
	return True, f'Cliente {status_text} correctamente.'


def suspend_overdue_subscriptions():
	reference_date = _get_reference_date()
	overdue_subscriptions = get_overdue_active_subscriptions(reference_date=reference_date)
	processed = 0
	suspended = 0
	errors: list[str] = []

	for subscription in overdue_subscriptions:
		processed += 1

		mac_address = getattr(subscription, 'installation_mac_address', None)
		if not mac_address:
			errors.append(
				f'Suscripcion {subscription.correlative} sin MAC asociada para suspension automatica.'
			)
			continue

		ok, message = client_activation(mac_address, enabled=False)
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

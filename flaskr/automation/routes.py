from flask import render_template, flash, redirect, url_for, request

from flaskr import mk_router
from flaskr.subscriptions.services.querys import update_subscription_status

from . import automation_bp


def obtener_info_sistema():
    datos, exito = mk_router.query('/system/resource')

    if exito:
        return {
            'status': 'success',
            'modelo': datos.get('board-name'),
            'version': datos.get('version'),
            'uptime': datos.get('uptime'),
        }

    return {
        'status': 'error',
        'message': datos,
    }

def client_activation(mac_address: str, enabled: bool = True):
    if not mac_address:
        return False, 'La direccion MAC es obligatoria.'

    endpoint = '/ip/dhcp-server/lease'
    leases, exito = mk_router.query(endpoint)

    if not exito:
        return False, leases

    if not isinstance(leases, list):
        return False, 'Respuesta invalida del MikroTik al consultar leases DHCP.'

    mac_normalizada = mac_address.strip().upper()
    if len(mac_normalizada.replace(':', '').replace('-', '')) == 12:
        mac_normalizada = ':'.join(
            mac_normalizada.replace(':', '').replace('-', '')[index:index + 2]
            for index in range(0, 12, 2)
        )

    lease_id = None
    for lease in leases:
        if not isinstance(lease, dict):
            continue
        lease_mac = (lease.get('mac-address') or '').upper()
        if lease_mac == mac_normalizada:
            lease_id = lease.get('.id') or lease.get('id')
            break

    if not lease_id:
        return False, f'No se encontro una lease DHCP para la MAC {mac_normalizada}.'

    action = 'no' if enabled else 'yes'
    response = mk_router.query(
        f'/ip/dhcp-server/lease/{lease_id}',
    )

    if isinstance(response, tuple):
        _, ok = response
        if not ok:
            return False, 'No fue posible actualizar block-access en la lease DHCP.'

    try:
        import requests
        from requests.auth import HTTPBasicAuth
        import urllib3

        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        patch_response = requests.patch(
            f"{mk_router.base_url}/ip/dhcp-server/lease/{lease_id}",
            auth=HTTPBasicAuth(mk_router.auth.username, mk_router.auth.password),
            verify=False,
            timeout=5,
            json={'block-access': action},
        )
        if patch_response.status_code not in (200, 204):
            return False, f'Error del router {patch_response.status_code}: {patch_response.text}'
    except Exception as error:
        return False, f'No se pudo actualizar el cliente en el MikroTik: {error}'

    estado = 'activado' if enabled else 'desactivado'
    return True, f'Cliente {estado} correctamente.'
    


@automation_bp.route('/')
def automation():
    info = obtener_info_sistema()
    return render_template('automation.html', info=info)

@automation_bp.route('/activate_client/<mac_address>', methods=['POST'])
def activate_client(mac_address):
    raw_correlative = (request.form.get('correlative') or '').strip()
    resultado, mensaje = client_activation(mac_address, enabled=True)
    if resultado:
        if raw_correlative:
            try:
                correlative = int(raw_correlative)
                update_subscription_status(correlative, 'activo')
            except ValueError:
                pass

        flash(mensaje, 'success')
        return redirect(url_for('subscriptions.subscriptions'))

    flash(mensaje, 'danger')
    return redirect(url_for('subscriptions.subscriptions'))


@automation_bp.route('/deactivate_client/<mac_address>', methods=['POST'])
def deactivate_client(mac_address):
    raw_correlative = (request.form.get('correlative') or '').strip()
    resultado, mensaje = client_activation(mac_address, enabled=False)
    if resultado:
        if raw_correlative:
            try:
                correlative = int(raw_correlative)
                update_subscription_status(correlative, 'suspendido_temporal')
            except ValueError:
                pass

        flash(mensaje, 'warning')
        return redirect(url_for('subscriptions.subscriptions'))

    flash(mensaje, 'danger')
    return redirect(url_for('subscriptions.subscriptions'))
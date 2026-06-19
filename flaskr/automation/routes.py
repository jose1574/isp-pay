from flask import render_template, flash, redirect, url_for, request
from sqlalchemy import text

from flaskr import conn_mikrotik, db
from flaskr.subscriptions.services.querys import update_subscription_status
from .services.worker import (
    client_activation,
    get_recent_automation_events,
    process_paid_subscription_reactivations,
    process_subscription_billing,
)

from . import automation_bp


def obtener_info_sistema():
    route_id = request.args.get('route_id', type=int)
    mk_router = conn_mikrotik(route_id)
    datos, exito = mk_router.query('/system/resource')

    if isinstance(datos, list) and datos:
        datos = datos[0]

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


def obtener_info_routers():
    routes = db.session.execute(
        text(
            """
            SELECT correlative, description, ip_address, api_port, is_active
            FROM genius.routes
            ORDER BY is_active DESC, correlative ASC
            """
        )
    ).mappings().all()

    routers_info = []
    for route in routes:
        route_id = route['correlative']
        item = {
            'route_id': route_id,
            'description': route.get('description'),
            'ip_address': route.get('ip_address'),
            'api_port': route.get('api_port'),
            'is_active': route.get('is_active'),
            'status': 'error',
            'identity': '-',
            'modelo': '-',
            'version': '-',
            'uptime': '-',
            'message': '-',
        }

        try:
            mk_router = conn_mikrotik(route_id)
            identity_data, identity_ok = mk_router.query('/system/identity')
            resource_data, resource_ok = mk_router.query('/system/resource')

            if isinstance(identity_data, list) and identity_data:
                identity_data = identity_data[0]
            if isinstance(resource_data, list) and resource_data:
                resource_data = resource_data[0]

            if identity_ok and isinstance(identity_data, dict):
                item['identity'] = identity_data.get('name') or '-'

            if resource_ok and isinstance(resource_data, dict):
                item['modelo'] = resource_data.get('board-name') or '-'
                item['version'] = resource_data.get('version') or '-'
                item['uptime'] = resource_data.get('uptime') or '-'

            if identity_ok or resource_ok:
                item['status'] = 'success'
                item['message'] = 'Conexion exitosa.'
            else:
                item['message'] = str(resource_data)
        except Exception as error:
            item['message'] = str(error)

        routers_info.append(item)

    return routers_info


@automation_bp.route('/')
def automation():
    info = obtener_info_sistema()
    routers_info = obtener_info_routers()
    events = get_recent_automation_events(limit=100)
    return render_template('automation.html', info=info, routers_info=routers_info, events=events)

@automation_bp.route('/activate_client/', methods=['POST'])
def activate_client():
    raw_correlative = (request.form.get('correlative') or '').strip()
    route_id = request.form.get('route_id', type=int)
    mac_address = request.form.get('mac_address')
    resultado, mensaje = client_activation(mac_address, route_id, enabled=True)
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


@automation_bp.route('/deactivate_client/', methods=['POST'])
def deactivate_client():
    mac_address = request.form.get('mac_address')
    route_id = request.form.get('route_id', type=int)

    ## 1. obtener credenciales del router 
    #  
    ## 2. configurar la funcion de mikrotik para que reciba las credenciales del router desde la base de datos.

    raw_correlative = (request.form.get('correlative') or '').strip()
    resultado, mensaje = client_activation(mac_address, route_id, enabled=False )
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


@automation_bp.route('/run-overdue-check', methods=['POST'])
def run_overdue_check():
    result = process_subscription_billing()

    if result['suspended']:
        flash(
            f"Se crearon {result['due_created']} cuenta(s) por cobrar y se suspendieron {result['suspended']} suscripciones vencidas por falta de pago.",
            'warning',
        )
    elif result['due_created']:
        flash(
            f"Se crearon {result['due_created']} cuenta(s) por cobrar en fecha de cobro. No hubo suspensiones pendientes.",
            'success',
        )
    elif result['overdue_processed']:
        flash('Se revisaron suscripciones vencidas, pero no todas pudieron suspenderse.', 'warning')
    else:
        flash('No hay cuentas por cobrar por crear ni suscripciones vencidas para suspender en este momento.', 'success')

    for error in result['errors'][:3]:
        flash(error, 'danger')

    return redirect(url_for('automation.automation'))


@automation_bp.route('/run-paid-check', methods=['POST'])
def run_paid_check():
    result = process_paid_subscription_reactivations()

    if result['activated']:
        flash(
            f"Se reactivaron {result['activated']} suscripciones con pago completo.",
            'success',
        )
    elif result['processed']:
        flash('Se procesaron pagos, pero no hubo nuevas reactivaciones.', 'warning')
    else:
        flash('No hay pagos pendientes de procesar para reactivacion.', 'success')

    for error in result['errors'][:3]:
        flash(error, 'danger')

    return redirect(url_for('automation.automation'))
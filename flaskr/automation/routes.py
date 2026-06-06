from flask import render_template, flash, redirect, url_for, request

from flaskr import conn_mikrotik
from flaskr.subscriptions.services.querys import update_subscription_status
from .services.worker import client_activation, suspend_overdue_subscriptions

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
@automation_bp.route('/')
def automation():
    info = obtener_info_sistema()
    return render_template('automation.html', info=info)

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
    result = suspend_overdue_subscriptions()

    if result['suspended']:
        flash(
            f"Se suspendieron {result['suspended']} suscripciones vencidas por falta de pago.",
            'warning',
        )
    elif result['processed']:
        flash('Se revisaron suscripciones vencidas, pero no todas pudieron suspenderse.', 'warning')
    else:
        flash('No hay suscripciones vencidas para suspender en este momento.', 'success')

    for error in result['errors'][:3]:
        flash(error, 'danger')

    return redirect(url_for('automation.automation'))
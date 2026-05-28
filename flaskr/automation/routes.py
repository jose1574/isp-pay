from flask import render_template, flash, redirect, url_for, request

from flaskr import mk_router
from flaskr.subscriptions.services.querys import update_subscription_status
from .services.worker import client_activation, suspend_overdue_subscriptions

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
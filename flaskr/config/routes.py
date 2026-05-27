from flask import render_template, request, flash, url_for, redirect

from . import config_bp
from .services.querys import (
    get_routes,
    get_route,
    create_route,
    update_route,
    delete_route,
)


def _build_route_context(correlative=None, new_mode=False):
    routes = get_routes()
    route = None

    if correlative:
        route = get_route(correlative)

    return {
        'routes': routes,
        'route': route,
        'show_form': bool(new_mode or route),
        'new_mode': bool(new_mode),
        'form_enabled': True,
    }


@config_bp.route('/')
def config():
    raw_correlative = (request.args.get('correlative') or '').strip()
    new_mode = (request.args.get('mode') or '').strip().lower() == 'new'

    correlative = None
    if raw_correlative:
        try:
            correlative = int(raw_correlative)
        except ValueError:
            correlative = None

    context = _build_route_context(correlative=correlative, new_mode=new_mode)
    return render_template('config.html', **context)


@config_bp.route('/get_route_form', methods=['GET'])
def get_route_form():
    raw_correlative = (request.args.get('correlative') or '').strip()
    new_mode = (request.args.get('mode') or '').strip().lower() == 'new'

    correlative = None
    if raw_correlative:
        try:
            correlative = int(raw_correlative)
        except ValueError:
            correlative = None

    context = _build_route_context(correlative=correlative, new_mode=new_mode)
    return render_template('partials/route_form.html', **context)


@config_bp.route('/routes/save', methods=['POST'])
def save_route():
    raw_correlative = (request.form.get('correlative') or '').strip()
    ip_address = (request.form.get('ip_address') or '').strip()
    mac_address = (request.form.get('mac_address') or '').strip() or None
    identity = (request.form.get('identity') or '').strip() or None
    description = (request.form.get('description') or '').strip() or None
    raw_api_port = (request.form.get('api_port') or '').strip()
    is_active = request.form.get('is_active') == 'on'
    username = (request.form.get('username') or '').strip()
    password = (request.form.get('password') or '').strip()

    if not ip_address or not raw_api_port or not username or not password:
        flash('IP, puerto API, usuario y clave son obligatorios.', 'warning')
        return redirect(url_for('config.config'))

    try:
        api_port = int(raw_api_port)
    except ValueError:
        flash('El puerto API debe ser numerico.', 'warning')
        return redirect(url_for('config.config'))

    if api_port < 1 or api_port > 65535:
        flash('El puerto API debe estar entre 1 y 65535.', 'warning')
        return redirect(url_for('config.config'))

    if raw_correlative:
        try:
            correlative = int(raw_correlative)
        except ValueError:
            flash('Identificador del router invalido.', 'warning')
            return redirect(url_for('config.config'))

        result = update_route(
            correlative=correlative,
            ip_address=ip_address,
            mac_address=mac_address,
            identity=identity,
            description=description,
            api_port=api_port,
            is_active=is_active,
            username=username,
            password=password,
        )

        if result == 'duplicate_data':
            flash('Ya existe un router con esa IP o MAC.', 'warning')
            return redirect(url_for('config.config', correlative=correlative))

        if not result:
            flash('No fue posible actualizar el router.', 'danger')
            return redirect(url_for('config.config', correlative=correlative))

        flash('Router actualizado correctamente.', 'success')
        return redirect(url_for('config.config', correlative=correlative))

    result = create_route(
        ip_address=ip_address,
        mac_address=mac_address,
        identity=identity,
        description=description,
        api_port=api_port,
        is_active=is_active,
        username=username,
        password=password,
    )

    if result == 'duplicate_data':
        flash('Ya existe un router con esa IP o MAC.', 'warning')
        return redirect(url_for('config.config', mode='new'))

    if not result:
        flash('No fue posible registrar el router.', 'danger')
        return redirect(url_for('config.config', mode='new'))

    flash('Router registrado correctamente.', 'success')
    return redirect(url_for('config.config', correlative=result))


@config_bp.route('/routes/delete', methods=['POST'])
def remove_route():
    raw_correlative = (request.form.get('correlative') or '').strip()

    if not raw_correlative:
        flash('No se encontro el router a eliminar.', 'warning')
        return redirect(url_for('config.config'))

    try:
        correlative = int(raw_correlative)
    except ValueError:
        flash('Identificador del router invalido.', 'warning')
        return redirect(url_for('config.config'))

    deleted = delete_route(correlative=correlative)

    if not deleted:
        flash('No fue posible eliminar el router.', 'danger')
        return redirect(url_for('config.config', correlative=correlative))

    flash('Router eliminado correctamente.', 'warning')
    return redirect(url_for('config.config'))
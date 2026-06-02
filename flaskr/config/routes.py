from flask import render_template, request, flash, url_for, redirect

from . import config_bp
from .services.querys import (
    get_routes,
    get_route,
    create_route,
    update_route,
    delete_route,
    get_nodes,
    get_node,
    create_node,
    update_node,
    delete_node,
    get_area_sales_options,
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


@config_bp.route('/routers')
def config_routers():
    raw_correlative = (request.args.get('correlative') or '').strip()
    new_mode = (request.args.get('mode') or '').strip().lower() == 'new'

    correlative = None
    if raw_correlative:
        try:
            correlative = int(raw_correlative)
        except ValueError:
            correlative = None

    context = _build_route_context(correlative=correlative, new_mode=new_mode)
    return render_template('routers.html', **context)


@config_bp.route('/routers/get_route_form', methods=['GET'])
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


@config_bp.route('/routers/save', methods=['POST'])
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
        return redirect(url_for('config.config_routers'))

    try:
        api_port = int(raw_api_port)
    except ValueError:
        flash('El puerto API debe ser numerico.', 'warning')
        return redirect(url_for('config.config_routers'))

    if api_port < 1 or api_port > 65535:
        flash('El puerto API debe estar entre 1 y 65535.', 'warning')
        return redirect(url_for('config.config_routers'))

    if raw_correlative:
        try:
            correlative = int(raw_correlative)
        except ValueError:
            flash('Identificador del router invalido.', 'warning')
            return redirect(url_for('config.config_routers'))

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
            return redirect(url_for('config.config_routers', correlative=correlative))

        if not result:
            flash('No fue posible actualizar el router.', 'danger')
            return redirect(url_for('config.config_routers', correlative=correlative))

        flash('Router actualizado correctamente.', 'success')
        return redirect(url_for('config.config_routers', correlative=correlative))

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
        return redirect(url_for('config.config_routers', mode='new'))

    if not result:
        flash('No fue posible registrar el router.', 'danger')
        return redirect(url_for('config.config_routers', mode='new'))

    flash('Router registrado correctamente.', 'success')
    return redirect(url_for('config.config_routers', correlative=result))


@config_bp.route('/routers/delete', methods=['POST'])
def remove_route():
    raw_correlative = (request.form.get('correlative') or '').strip()

    if not raw_correlative:
        flash('No se encontro el router a eliminar.', 'warning')
        return redirect(url_for('config.config_routers'))

    try:
        correlative = int(raw_correlative)
    except ValueError:
        flash('Identificador del router invalido.', 'warning')
        return redirect(url_for('config.config_routers'))

    deleted = delete_route(correlative=correlative)

    if not deleted:
        flash('No fue posible eliminar el router.', 'danger')
        return redirect(url_for('config.config_routers', correlative=correlative))

    flash('Router eliminado correctamente.', 'warning')
    return redirect(url_for('config.config_routers'))



#### rutas para operaciones con nodos ###


def _build_node_context(correlative=None, new_mode=False):
    nodes = get_nodes()
    node = None

    if correlative:
        node = get_node(correlative)

    return {
        'nodes': nodes,
        'node': node,
        'area_sales': get_area_sales_options(),
        'show_form': bool(new_mode or node),
        'new_mode': bool(new_mode),
        'form_enabled': True,
    }


@config_bp.route('/nodos')
def config_nodos():
    raw_correlative = (request.args.get('correlative') or '').strip()
    new_mode = (request.args.get('mode') or '').strip().lower() == 'new'

    correlative = None
    if raw_correlative:
        try:
            correlative = int(raw_correlative)
        except ValueError:
            correlative = None

    context = _build_node_context(correlative=correlative, new_mode=new_mode)
    return render_template('nodos.html', **context)


@config_bp.route('/nodos/get_nodo_form', methods=['GET'])
def get_nodo_form():
    raw_correlative = (request.args.get('correlative') or '').strip()
    new_mode = (request.args.get('mode') or '').strip().lower() == 'new'

    correlative = None
    if raw_correlative:
        try:
            correlative = int(raw_correlative)
        except ValueError:
            correlative = None

    context = _build_node_context(correlative=correlative, new_mode=new_mode)
    return render_template('partials/nodo_form.html', **context)


@config_bp.route('/nodos/save', methods=['POST'])
def save_node():
    raw_correlative = (request.form.get('correlative') or '').strip()
    description = (request.form.get('description') or '').strip()
    area_sales_id = (request.form.get('area_sales_id') or '').strip() or None

    if not description:
        flash('La descripcion del nodo es obligatoria.', 'warning')
        return redirect(url_for('config.config_nodos'))

    if raw_correlative:
        try:
            correlative = int(raw_correlative)
        except ValueError:
            flash('Identificador del nodo invalido.', 'warning')
            return redirect(url_for('config.config_nodos'))

        result = update_node(
            correlative=correlative,
            description=description,
            area_sales_id=area_sales_id,
        )

        if result == 'duplicate_data':
            flash('Ya existe un nodo con esos datos.', 'warning')
            return redirect(url_for('config.config_nodos', correlative=correlative))

        if not result:
            flash('No fue posible actualizar el nodo.', 'danger')
            return redirect(url_for('config.config_nodos', correlative=correlative))

        flash('Nodo actualizado correctamente.', 'success')
        return redirect(url_for('config.config_nodos', correlative=correlative))

    result = create_node(
        description=description,
        area_sales_id=area_sales_id,
    )

    if result == 'duplicate_data':
        flash('Ya existe un nodo con esos datos.', 'warning')
        return redirect(url_for('config.config_nodos', mode='new'))

    if not result:
        flash('No fue posible registrar el nodo.', 'danger')
        return redirect(url_for('config.config_nodos', mode='new'))

    flash('Nodo registrado correctamente.', 'success')
    return redirect(url_for('config.config_nodos', correlative=result))


@config_bp.route('/nodos/delete', methods=['POST'])
def remove_node():
    raw_correlative = (request.form.get('correlative') or '').strip()

    if not raw_correlative:
        flash('No se encontro el nodo a eliminar.', 'warning')
        return redirect(url_for('config.config_nodos'))

    try:
        correlative = int(raw_correlative)
    except ValueError:
        flash('Identificador del nodo invalido.', 'warning')
        return redirect(url_for('config.config_nodos'))

    deleted = delete_node(correlative=correlative)

    if not deleted:
        flash('No fue posible eliminar el nodo.', 'danger')
        return redirect(url_for('config.config_nodos', correlative=correlative))

    flash('Nodo eliminado correctamente.', 'warning')
    return redirect(url_for('config.config_nodos'))
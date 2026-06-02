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
    get_naps,
    get_naps_count,
    get_nap,
    get_nap_ports,
    get_nap_options,
    create_nap_with_ports,
    update_nap,
    delete_nap,
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
    routes = get_routes()
    node = None

    if correlative:
        node = get_node(correlative)

    return {
        'nodes': nodes,
        'routes': routes,
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
    raw_route_id = (request.form.get('route_id') or '').strip()
    area_sales_id = (request.form.get('area_sales_id') or '').strip() or None

    if not description or not raw_route_id:
        flash('La descripcion y el router del nodo son obligatorios.', 'warning')
        return redirect(url_for('config.config_nodos'))

    try:
        route_id = int(raw_route_id)
    except ValueError:
        flash('El router seleccionado es invalido.', 'warning')
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
            route_id=route_id,
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
        route_id=route_id,
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


#### rutas para operaciones con NAP ###


def _build_nap_form_context(correlative=None, new_mode=False):
    nap = None
    nap_ports = []

    if correlative:
        nap = get_nap(correlative)
        if nap:
            nap_ports = get_nap_ports(nap.correlative)

    return {
        'nodes': get_nodes(),
        'nap_options': get_nap_options(),
        'nap': nap,
        'nap_ports': nap_ports,
        'new_mode': bool(new_mode),
        'is_edit_mode': bool(nap and not new_mode),
    }


def _build_nap_list_context(page: int, per_page: int, search: str = ''):
    total_naps = get_naps_count(search=search)
    total_pages = max(1, (total_naps + per_page - 1) // per_page)
    page = min(max(1, page), total_pages)

    return {
        'naps': get_naps(page=page, per_page=per_page, search=search),
        'page': page,
        'per_page': per_page,
        'total_pages': total_pages,
        'total_naps': total_naps,
        'search': search,
    }


def _parse_ports_from_request(port_count: int):
    ports = []
    seen_names = set()

    for index in range(1, port_count + 1):
        port_name = (request.form.get(f'port_name_{index}') or '').strip()
        if not port_name:
            return None, 'Todos los puertos deben tener nombre.'

        normalized_name = port_name.lower()
        if normalized_name in seen_names:
            return None, 'No se permiten nombres de puertos duplicados en la misma NAP.'
        seen_names.add(normalized_name)

        port_trunk = request.form.get(f'port_trunk_{index}') == 'on'
        raw_next_nap_id = (request.form.get(f'next_nap_id_{index}') or '').strip()
        next_nap_id = None

        if port_trunk:
            if not raw_next_nap_id:
                return None, f'El puerto {port_name} esta marcado como trunk y requiere NAP destino.'
            try:
                next_nap_id = int(raw_next_nap_id)
            except ValueError:
                return None, f'La NAP destino del puerto {port_name} es invalida.'

        ports.append(
            {
                'port_name': port_name,
                'port_trunk': port_trunk,
                'next_nap_id': next_nap_id,
            }
        )

    return ports, None


@config_bp.route('/nap')
def config_nap():
    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        page = 1

    try:
        per_page = int(request.args.get('per_page', 10))
    except ValueError:
        per_page = 10

    page = max(1, page)
    per_page = min(max(5, per_page), 100)
    search = (request.args.get('search') or '').strip()

    context = _build_nap_list_context(page=page, per_page=per_page, search=search)
    return render_template('nap.html', **context)


@config_bp.route('/nap/form', methods=['GET'])
def config_nap_form():
    raw_correlative = (request.args.get('correlative') or '').strip()
    new_mode = (request.args.get('mode') or '').strip().lower() == 'new'

    correlative = None
    if raw_correlative:
        try:
            correlative = int(raw_correlative)
        except ValueError:
            correlative = None

    context = _build_nap_form_context(correlative=correlative, new_mode=new_mode)
    return render_template('nap_form_page.html', **context)


@config_bp.route('/nap/save', methods=['POST'])
def save_nap():
    raw_correlative = (request.form.get('correlative') or '').strip()
    description = (request.form.get('description') or '').strip()
    location = (request.form.get('location') or '').strip()
    raw_nodo_id = (request.form.get('nodo_id') or '').strip()
    raw_port_count = (request.form.get('port_count') or '').strip()

    is_edit_mode = False
    correlative = None
    if raw_correlative:
        try:
            correlative = int(raw_correlative)
            is_edit_mode = True
        except ValueError:
            flash('Identificador de NAP invalido.', 'warning')
            return redirect(url_for('config.config_nap'))

    if not description or not location:
        flash('Nombre y ubicacion son obligatorios.', 'warning')
        if is_edit_mode:
            return redirect(url_for('config.config_nap_form', correlative=correlative))
        return redirect(url_for('config.config_nap_form', mode='new'))

    nodo_id = None
    if raw_nodo_id:
        try:
            nodo_id = int(raw_nodo_id)
        except ValueError:
            flash('El nodo seleccionado es invalido.', 'warning')
            if is_edit_mode:
                return redirect(url_for('config.config_nap_form', correlative=correlative))
            return redirect(url_for('config.config_nap_form', mode='new'))

    if is_edit_mode:
        result = update_nap(
            correlative=correlative,
            description=description,
            location=location,
            nodo_id=nodo_id,
        )

        if result == 'duplicate_data':
            flash('Hay datos duplicados al actualizar la NAP.', 'warning')
            return redirect(url_for('config.config_nap_form', correlative=correlative))

        if not result:
            flash('No fue posible actualizar la NAP.', 'danger')
            return redirect(url_for('config.config_nap_form', correlative=correlative))

        flash('NAP actualizada correctamente.', 'success')
        return redirect(url_for('config.config_nap_form', correlative=correlative))

    if not raw_port_count:
        flash('La cantidad de puertos es obligatoria para crear una NAP.', 'warning')
        return redirect(url_for('config.config_nap_form', mode='new'))

    try:
        port_count = int(raw_port_count)
    except ValueError:
        flash('La cantidad de puertos debe ser numerica.', 'warning')
        return redirect(url_for('config.config_nap_form', mode='new'))

    if port_count < 1 or port_count > 128:
        flash('La cantidad de puertos debe estar entre 1 y 128.', 'warning')
        return redirect(url_for('config.config_nap_form', mode='new'))

    ports, error = _parse_ports_from_request(port_count)
    if error:
        flash(error, 'warning')
        return redirect(url_for('config.config_nap_form', mode='new'))

    result = create_nap_with_ports(
        description=description,
        location=location,
        nodo_id=nodo_id,
        ports=ports,
    )

    if result == 'duplicate_data':
        flash('Hay datos duplicados al registrar la NAP o sus puertos.', 'warning')
        return redirect(url_for('config.config_nap_form', mode='new'))

    if result == 'invalid_reference':
        flash('El nodo o la NAP destino de un puerto trunk no es valida.', 'warning')
        return redirect(url_for('config.config_nap_form', mode='new'))

    if not result:
        flash('No fue posible registrar la NAP.', 'danger')
        return redirect(url_for('config.config_nap_form', mode='new'))

    flash('NAP registrada correctamente.', 'success')
    return redirect(url_for('config.config_nap'))


@config_bp.route('/nap/delete', methods=['POST'])
def remove_nap():
    raw_correlative = (request.form.get('correlative') or '').strip()
    raw_page = (request.form.get('page') or '').strip()
    raw_per_page = (request.form.get('per_page') or '').strip()
    search = (request.form.get('search') or '').strip()

    redirect_kwargs = {}
    if raw_page.isdigit():
        redirect_kwargs['page'] = max(1, int(raw_page))
    if raw_per_page.isdigit():
        redirect_kwargs['per_page'] = min(max(5, int(raw_per_page)), 100)
    if search:
        redirect_kwargs['search'] = search

    if not raw_correlative:
        flash('No se encontro la NAP a eliminar.', 'warning')
        return redirect(url_for('config.config_nap', **redirect_kwargs))

    try:
        correlative = int(raw_correlative)
    except ValueError:
        flash('Identificador de NAP invalido.', 'warning')
        return redirect(url_for('config.config_nap', **redirect_kwargs))

    deleted = delete_nap(correlative=correlative)

    if not deleted:
        flash('No fue posible eliminar la NAP.', 'danger')
        return redirect(url_for('config.config_nap', **redirect_kwargs))

    flash('NAP eliminada correctamente.', 'warning')
    return redirect(url_for('config.config_nap', **redirect_kwargs))
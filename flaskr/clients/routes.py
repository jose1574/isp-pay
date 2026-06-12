from flask import render_template, request, redirect, url_for, flash
from . import clients_bp  
from .services.querys import (
    get_clients, 
    get_clients_count,
    get_client, 
    get_area_sales, 
    create_client,
    )


@clients_bp.route('/')
def clients():
    q = (request.args.get('q') or '').strip()

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

    total_clients = get_clients_count(search=q)
    total_pages = max(1, (total_clients + per_page - 1) // per_page)

    if page > total_pages:
        page = total_pages

    clients = get_clients(page=page, per_page=per_page, search=q)
    return render_template(
        'clients.html',
        clients=clients,
        q=q,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        total_clients=total_clients,
    )



@clients_bp.route('/client', methods=['GET'])
def client():
    code = request.args.get('code')
    client = get_client(code) if code else None
    area_sales = get_area_sales()
    return render_template(
        'client.html',
        client=client,
        code=client.code if client else code,
        area_sales=area_sales,
        form_enabled=True,
    )


@clients_bp.route('/get_client', methods=['GET'])
def search_client():
    code = request.args.get('code')
    client = get_client(code)
    area_sales = get_area_sales()

    if client:
        if request.headers.get('HX-Request') == 'true':
            return render_template(
                'partials/client_form.html',
                client=client,
                code=client.code,
                area_sales=area_sales,
                form_enabled=True,
            )

        return render_template(
            'client.html',
            client=client,
            code=client.code,
            area_sales=area_sales,
            form_enabled=True,
        )
    else:
        flash("Cliente no encontrado, ingrese datos para crear un nuevo cliente", "warning")
        if request.headers.get('HX-Request') == 'true':
            return (
                '',
                204,
                {'HX-Redirect': url_for('clients.client', code=code)}
            )

        return render_template(
            'client.html',
            client=client,
            code=code,
            area_sales=area_sales,
            form_enabled=True,
        )


@clients_bp.route('/add/save', methods=['POST'])
def save_client():
    code = (request.form.get('code') or '').strip()
    description = request.form.get('description')
    address = request.form.get('address')
    email = request.form.get('email')
    phone = request.form.get('phone')
    area_sales = request.form.get('area_sales')
    credit_days = request.form.get('credit_days')

    if not code:
        flash('Debe ingresar una cédula de cliente antes de guardar.', 'warning')
        return redirect(url_for('clients.client', code=code))

    existing_client = get_client(code)

    try:
        create_client(
            code,
            description,
            address,
            email,
            phone,
            area_sales,
            credit_days,
        )
    except Exception as e:
        flash(f'Error al guardar el cliente: {str(e)}', 'danger')
        return redirect(url_for('clients.client', code=code))

    flash(
        'Se actualizaron correctamente los datos' if existing_client else 'Se guardaron correctamente los datos',
        'success',
    )
    return redirect(url_for('clients.client', code=code))


@clients_bp.route('/modal_clients')
def modal_clients():
    q = (request.args.get('q') or '').strip()

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

    total_clients = get_clients_count(search=q)
    total_pages = max(1, (total_clients + per_page - 1) // per_page)

    if page > total_pages:
        page = total_pages

    clients = get_clients(page=page, per_page=per_page, search=q)
    return render_template(
        'partials/modal_clients.html',
        clients=clients,
        q=q,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        total_clients=total_clients,
    )
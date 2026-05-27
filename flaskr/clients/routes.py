from flask import render_template, request, redirect, url_for, flash
from . import clients_bp  
from .services.querys import (
    get_clients, 
    get_client, 
    get_area_sales, 
    create_client,
    )




@clients_bp.route('/')
def clients():
    clients = get_clients()
    return render_template('clients.html', clients=clients)



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
    code = request.form.get('code')
    description = request.form.get('description')
    address = request.form.get('address')
    email = request.form.get('email')
    phone = request.form.get('phone')
    area_sales = request.form.get('area_sales')
    credit_days = request.form.get('credit_days')
    existing_client = get_client(code) if code else None



    try:
        client_saver = create_client if existing_client else create_client
        client_saver(
            code, 
            description,
            address,
            email,
            phone,
            area_sales,
            credit_days
        )
    except Exception as e:
        flash(f'Error al guardar el cliente: {str(e)}', 'danger')

    flash("Se actualizaron correctamente los datos" if existing_client else "Se guardaron correctamente los datos", 'success')
    return redirect(url_for('clients.client'))


@clients_bp.route('/modal_clients')
def modal_clients():
    clients = get_clients()
    return render_template('partials/modal_clients.html', clients=clients)
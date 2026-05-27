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



@clients_bp.route('/add', methods=['GET'])
def add_client():
    area_sales = get_area_sales()
    client_code = request.args.get('code')
    client = None
    alert_message = None
    alert_type = None

    if client_code:
        client = get_client(client_code)
        if client:
            alert_message = "Cliente encontrado, puedes actualizar sus datos"
            alert_type = "info"
        else:
            alert_message = "No se encontró el cliente, puedes registrar uno nuevo con este código"
            alert_type = "warning"

    context = {
        'area_sales': area_sales,
        'client': client,
        'searched_code': client_code or '',
        'alert_message': alert_message,
        'alert_type': alert_type,
    }

    if request.headers.get('HX-Request') == 'true':
        return render_template('partials/client_form.html', **context)

    return render_template('add_client.html', **context)



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
    return redirect(url_for('clients.add_client'))


@clients_bp.route('/modal_clients')
def modal_clients():
    clients = get_clients()
    return render_template('partials/modal_clients.html', clients=clients)
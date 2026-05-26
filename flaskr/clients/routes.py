from flask import render_template, request, redirect, url_for, flash
from . import clients_bp  
from .services.querys import get_clients, get_area_sales, create_client




@clients_bp.route('/')
def clients():
    clients = get_clients()
    return render_template('clients.html', clients=clients)


#formularuio para agregar un cliente nuevo_BP
@clients_bp.route('/add')
def add_client():
    area_sales = get_area_sales()
    return render_template('add_client.html', area_sales=area_sales)

@clients_bp.route('/add/save', methods=['POST'])
def save_client():
    code = request.form.get('code')
    description = request.form.get('description')
    address = request.form.get('address')
    email = request.form.get('email')
    phone = request.form.get('phone')
    area_sales = request.form.get('area_sales')
    credit_days = request.form.get('credit_days')

    try:
        create_client(
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

    flash("Se guardaron correctamente los datos", 'success')
    return redirect(url_for('clients.add_client'))

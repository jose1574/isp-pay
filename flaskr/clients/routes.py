from flask import render_template
from . import clients_bp  
from .services.querys import get_clients




@clients_bp.route('/')
def clients():
    clients = get_clients()
    return render_template('clients.html', clients=clients)
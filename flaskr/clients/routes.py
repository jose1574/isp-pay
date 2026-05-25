from flask import render_template
from . import clients_bp    

@clients_bp.route('/')
def dashboard():
    return render_template('dashboard/dashboard.html')
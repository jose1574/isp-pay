from flask import render_template

from . import nodos_bp  

@nodos_bp.route('/')
def nodos():
    return render_template('nodos.html')
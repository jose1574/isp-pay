from flask import Blueprint

nodos_bp = Blueprint('nodos', __name__, template_folder='templates')

from . import routes
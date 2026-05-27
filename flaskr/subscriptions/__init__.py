from flask import Blueprint

subscriptions_bp = Blueprint('subscriptions', __name__, template_folder='templates')

from . import routes
from sqlalchemy import text

from flaskr import db

def get_clients():
    clients = db.session.execute(text("SELECT * FROM clients")).fetchall()
    return clients

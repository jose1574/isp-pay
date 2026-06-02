import os

import click
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from .mikrotik_services import MikroTikClient

# Inicializamos el cliente apuntando a tu router (usando http por defecto si no tienes SSL activo)
mk_router = MikroTikClient(
    host="192.168.33.1", 
    user="josegomez", 
    password="jose1574**", 
    use_ssl=False  # Cambia a True si activaste www-ssl en el MikroTik
)

# Hacemos que el objeto mk_router sea accesible o lo importamos donde se necesite

db = SQLAlchemy()
def create_app(test_config=None):
    from .db_bootstrap import bootstrap_database

    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", "dev")
    app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://postgres:root@localhost:5432/cadm_geniusnet"

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config.setdefault('AUTO_INIT_DB', os.environ.get('AUTO_INIT_DB', 'true').lower() in ('1', 'true', 'yes'))
    app.config.setdefault('DB_MIGRATIONS_DIR', os.environ.get('DB_MIGRATIONS_DIR', os.path.join(os.path.dirname(__file__), 'migrations', 'sql')))


    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # a simple page that says hello
    from . import db
    db.init_app(app)

    from . import dashboard 
    from . import clients
    from . import installations
    from . import subscriptions
    from . import config
    from . import automation
    from .automation.services.worker import suspend_overdue_subscriptions
    
    app.register_blueprint(dashboard.dashboard_bp, url_prefix='/')
    app.register_blueprint(clients.clients_bp, url_prefix='/clients')
    app.register_blueprint(installations.installations_bp, url_prefix='/installations')
    app.register_blueprint(subscriptions.subscriptions_bp, url_prefix='/subscriptions')
    app.register_blueprint(config.config_bp, url_prefix='/config')
    app.register_blueprint(automation.automation_bp, url_prefix='/automation')

    app.config.setdefault('AUTOMATION_REFERENCE_DATE', os.environ.get('AUTOMATION_REFERENCE_DATE'))

    if app.config.get('AUTO_INIT_DB', True):
        with app.app_context():
            migration_result = bootstrap_database(db)
            app.logger.info(
                'Inicializacion DB completada | migraciones_aplicadas=%s | migraciones_ya_aplicadas=%s',
                migration_result['applied'],
                migration_result['already_applied'],
            )

    @app.cli.command('init-db')
    def init_db_command():
        result = bootstrap_database(db)
        click.echo(
            'DB inicializada | migraciones_aplicadas={} | migraciones_ya_aplicadas={}'.format(
                result['applied'],
                result['already_applied'],
            )
        )

    @app.cli.command('migrate-db')
    def migrate_db_command():
        result = bootstrap_database(db)
        click.echo(
            'Migracion DB completada | migraciones_aplicadas={} | migraciones_ya_aplicadas={}'.format(
                result['applied'],
                result['already_applied'],
            )
        )

    @app.cli.command('check-overdue-subscriptions')
    def check_overdue_subscriptions_command():
        result = suspend_overdue_subscriptions()
        click.echo(
            'Revision completada | fecha={} | procesadas={} | suspendidas={} | errores={}'.format(
                result['reference_date'] or 'CURRENT_DATE',
                result['processed'],
                result['suspended'],
                len(result['errors']),
            )
        )

        for error in result['errors']:
            click.echo(f'ERROR: {error}')


    return app


app = create_app()
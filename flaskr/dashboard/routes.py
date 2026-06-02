from flask import render_template, current_app
from sqlalchemy import text

from flaskr import db

from . import dashboard_bp  

@dashboard_bp.route('/')
def dashboard():
    def safe_scalar(query: str, params=None, default=0):
        try:
            result = db.session.execute(text(query), params or {}).scalar()
            return result if result is not None else default
        except Exception as error:
            current_app.logger.warning('Dashboard metric query failed: %s', error)
            return default

    total_clients = safe_scalar("SELECT COUNT(*) FROM clients")
    total_installations = safe_scalar("SELECT COUNT(*) FROM genius.installations")
    total_subscriptions = safe_scalar("SELECT COUNT(*) FROM genius.subscription")
    active_subscriptions = safe_scalar(
        "SELECT COUNT(*) FROM genius.subscription WHERE status = 'activo'"
    )
    suspended_subscriptions = safe_scalar(
        """
        SELECT COUNT(*)
        FROM genius.subscription
        WHERE status IN ('suspendido_por_falta_de_pago', 'suspendido_temporal')
        """
    )
    clients_with_subscription = safe_scalar(
        "SELECT COUNT(DISTINCT client_code) FROM genius.subscription WHERE client_code IS NOT NULL"
    )
    active_ratio = round((active_subscriptions / total_subscriptions) * 100, 1) if total_subscriptions else 0
    clients_without_subscription = max(total_clients - clients_with_subscription, 0)

    status_rows = []
    try:
        status_rows = db.session.execute(
            text(
                """
                SELECT status, COUNT(*) AS total
                FROM genius.subscription
                GROUP BY status
                ORDER BY total DESC, status ASC
                LIMIT 6
                """
            )
        ).fetchall()
    except Exception as error:
        current_app.logger.warning('Dashboard status distribution query failed: %s', error)

    recent_installations = []
    try:
        recent_installations = db.session.execute(
            text(
                """
                SELECT client_code, location, install_date
                FROM genius.installations
                ORDER BY install_date DESC NULLS LAST, id DESC
                LIMIT 5
                """
            )
        ).fetchall()
    except Exception as error:
        current_app.logger.warning('Dashboard recent installations query failed: %s', error)

    return render_template(
        'dashboard.html',
        metrics={
            'total_clients': total_clients,
            'total_installations': total_installations,
            'total_subscriptions': total_subscriptions,
            'active_subscriptions': active_subscriptions,
            'suspended_subscriptions': suspended_subscriptions,
            'clients_with_subscription': clients_with_subscription,
            'clients_without_subscription': clients_without_subscription,
            'active_ratio': active_ratio,
        },
        status_rows=status_rows,
        recent_installations=recent_installations,
    )
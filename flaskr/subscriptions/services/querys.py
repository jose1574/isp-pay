from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from flask import current_app

from flaskr import db


def get_plans(page: int | None = None, per_page: int | None = None, search: str | None = None):
    search = (search or '').strip()
    where_clause = ''
    params = {}

    if search:
        where_clause = """
            WHERE code ILIKE :search
               OR description ILIKE :search
               OR COALESCE(comment, '') ILIKE :search
               OR COALESCE(coin, '') ILIKE :search
               OR CAST(COALESCE(price, 0) AS TEXT) ILIKE :search
        """
        params['search'] = f"%{search}%"

    base_query = f"SELECT * FROM genius.plans {where_clause} ORDER BY code"

    if page is None or per_page is None:
        plans = db.session.execute(text(base_query), params).fetchall()
        return plans

    offset = (page - 1) * per_page
    params['limit'] = per_page
    params['offset'] = offset
    plans = db.session.execute(
        text(base_query + " LIMIT :limit OFFSET :offset"),
        params,
    ).fetchall()
    return plans


def get_plans_count(search: str | None = None):
    search = (search or '').strip()
    where_clause = ''
    params = {}

    if search:
        where_clause = """
            WHERE code ILIKE :search
               OR description ILIKE :search
               OR COALESCE(comment, '') ILIKE :search
               OR COALESCE(coin, '') ILIKE :search
               OR CAST(COALESCE(price, 0) AS TEXT) ILIKE :search
        """
        params['search'] = f"%{search}%"

    total = db.session.execute(
        text(f"SELECT COUNT(*) FROM genius.plans {where_clause}"),
        params,
    ).scalar_one()
    return total


def get_plan(code: str):
    plan = db.session.execute(
        text('SELECT * FROM genius.plans WHERE code = :code'),
        {'code': code},
    ).first()
    return plan


def get_coins():
    try:
        return db.session.execute(
            text('SELECT code, description FROM public.coin ORDER BY code')
        ).fetchall()
    except SQLAlchemyError:
        db.session.rollback()

    try:
        return db.session.execute(
            text('SELECT code, name AS description FROM public.coin ORDER BY code')
        ).fetchall()
    except SQLAlchemyError as error:
        db.session.rollback()
        current_app.logger.exception('Error de base de datos al consultar monedas: %s', error)
        return []
    except Exception as error:
        db.session.rollback()
        current_app.logger.exception('Error inesperado al consultar monedas: %s', error)
        return []


def create_plan(code, description, comment, coin, price):
    query = text(
        """
        INSERT INTO genius.plans (
            code,
            description,
            comment,
            coin,
            price
        ) VALUES (
            :code,
            :description,
            :comment,
            :coin,
            :price
        )
        """
    )

    try:
        db.session.execute(
            query,
            {
                'code': code,
                'description': description,
                'comment': comment,
                'coin': coin,
                'price': price,
            },
        )
        db.session.commit()
        return True
    except SQLAlchemyError as error:
        db.session.rollback()
        if getattr(getattr(error, 'orig', None), 'pgcode', None) == '23505':
            return 'duplicate_code'
        if getattr(getattr(error, 'orig', None), 'pgcode', None) == '23503':
            return 'invalid_coin'
        current_app.logger.exception('Error de base de datos al crear plan: %s', error)
        return False
    except Exception as error:
        db.session.rollback()
        current_app.logger.exception('Error inesperado al crear plan: %s', error)
        return False


def update_plan(code, description, comment, coin, price):
    query = text(
        """
        UPDATE genius.plans
        SET
            description = :description,
            comment = :comment,
            coin = :coin,
            price = :price
        WHERE code = :code
        """
    )

    try:
        result = db.session.execute(
            query,
            {
                'code': code,
                'description': description,
                'comment': comment,
                'coin': coin,
                'price': price,
            },
        )
        db.session.commit()
        return result.rowcount > 0
    except SQLAlchemyError as error:
        db.session.rollback()
        if getattr(getattr(error, 'orig', None), 'pgcode', None) == '23503':
            return 'invalid_coin'
        current_app.logger.exception('Error de base de datos al actualizar plan: %s', error)
        return False
    except Exception as error:
        db.session.rollback()
        current_app.logger.exception('Error inesperado al actualizar plan: %s', error)
        return False


def delete_plan(code):
    query = text(
        """
        DELETE FROM genius.plans
        WHERE code = :code
        """
    )

    try:
        result = db.session.execute(query, {'code': code})
        db.session.commit()
        return result.rowcount > 0
    except SQLAlchemyError as error:
        db.session.rollback()
        current_app.logger.exception('Error de base de datos al eliminar plan: %s', error)
        return False
    except Exception as error:
        db.session.rollback()
        current_app.logger.exception('Error inesperado al eliminar plan: %s', error)
        return False


def get_subscriptions(page: int | None = None, per_page: int | None = None, search: str | None = None):
    search = (search or '').strip()
    where_clause = ''
    params = {}

    if search:
        where_clause = """
            WHERE s.client_code ILIKE :search
               OR s.plan_code ILIKE :search
               OR s.status ILIKE :search
               OR CAST(s.installation AS TEXT) ILIKE :search
        """
        params['search'] = f"%{search}%"

    base_query = f"""
        SELECT
            s.*,
            p.description AS plan_description,
            i.location AS installation_location,
            i.install_date AS installation_date,
            i.contract_number AS installation_contract_number
        FROM genius.subscription s
        LEFT JOIN genius.plans p ON p.code = s.plan_code
        LEFT JOIN genius.installations i ON i.id = s.installation
        {where_clause}
        ORDER BY s.correlative DESC
    """

    fallback_query = f"""
        SELECT
            s.*,
            p.description AS plan_description,
            i.location AS installation_location,
            i.install_date AS installation_date,
            NULL::INTEGER AS installation_contract_number
        FROM genius.subscription s
        LEFT JOIN genius.plans p ON p.code = s.plan_code
        LEFT JOIN genius.installations i ON i.id = s.installation
        {where_clause}
        ORDER BY s.correlative DESC
    """

    try:
        if page is None or per_page is None:
            return db.session.execute(text(base_query), params).fetchall()

        offset = (page - 1) * per_page
        params['limit'] = per_page
        params['offset'] = offset
        return db.session.execute(
            text(base_query + " LIMIT :limit OFFSET :offset"),
            params,
        ).fetchall()
    except SQLAlchemyError as error:
        db.session.rollback()
        if getattr(getattr(error, 'orig', None), 'pgcode', None) != '42703':
            raise

        # Compatibilidad temporal: BD sin columna installations.contract_number.
        if page is None or per_page is None:
            return db.session.execute(text(fallback_query), params).fetchall()

        offset = (page - 1) * per_page
        params['limit'] = per_page
        params['offset'] = offset
        return db.session.execute(
            text(fallback_query + " LIMIT :limit OFFSET :offset"),
            params,
        ).fetchall()


def get_subscriptions_count(search: str | None = None):
    search = (search or '').strip()
    where_clause = ''
    params = {}

    if search:
        where_clause = """
            WHERE client_code ILIKE :search
               OR plan_code ILIKE :search
               OR status ILIKE :search
               OR CAST(installation AS TEXT) ILIKE :search
        """
        params['search'] = f"%{search}%"

    return db.session.execute(
        text(f"SELECT COUNT(*) FROM genius.subscription {where_clause}"),
        params,
    ).scalar_one()


def get_installations_by_client(client_code: str):
    query = text(
        """
        SELECT id, client_code, contract_number, install_date, location, mac_address
        FROM genius.installations
        WHERE client_code = :client_code
        ORDER BY contract_number ASC, id ASC
        """
    )

    fallback_query = text(
        """
        SELECT id, client_code, NULL::INTEGER AS contract_number, install_date, location, mac_address
        FROM genius.installations
        WHERE client_code = :client_code
        ORDER BY id ASC
        """
    )

    try:
        return db.session.execute(query, {'client_code': client_code}).fetchall()
    except SQLAlchemyError as error:
        db.session.rollback()
        if getattr(getattr(error, 'orig', None), 'pgcode', None) != '42703':
            raise

        return db.session.execute(fallback_query, {'client_code': client_code}).fetchall()


def get_subscription_by_installation(installation_id: int):
    return db.session.execute(
        text(
            """
            SELECT *
            FROM genius.subscription
            WHERE installation = :installation_id
            LIMIT 1
            """
        ),
        {'installation_id': installation_id},
    ).first()


def create_subscription(
    client_code,
    installation,
    plan_code,
    status,
    cutoff_day,
    credit_day,
    price_applied,
):
    query = text(
        """
        INSERT INTO genius.subscription (
            client_code,
            installation,
            plan_code,
            status,
            cutoff_day,
            credit_day,
            price_applied
        ) VALUES (
            :client_code,
            :installation,
            :plan_code,
            :status,
            :cutoff_day,
            :credit_day,
            :price_applied
        )
        RETURNING correlative
        """
    )

    try:
        result = db.session.execute(
            query,
            {
                'client_code': client_code,
                'installation': installation,
                'plan_code': plan_code,
                'status': status,
                'cutoff_day': cutoff_day,
                'credit_day': credit_day,
                'price_applied': price_applied,
            },
        ).fetchone()
        db.session.commit()
        return result.correlative if result else None
    except SQLAlchemyError as error:
        db.session.rollback()
        if getattr(getattr(error, 'orig', None), 'pgcode', None) == '23505':
            return 'duplicate_installation'
        if getattr(getattr(error, 'orig', None), 'pgcode', None) == '23503':
            return 'invalid_fk'
        current_app.logger.exception('Error de base de datos al crear suscripcion: %s', error)
        return None
    except Exception as error:
        db.session.rollback()
        current_app.logger.exception('Error inesperado al crear suscripcion: %s', error)
        return None


def update_subscription(
    correlative,
    client_code,
    installation,
    plan_code,
    status,
    cutoff_day,
    credit_day,
    price_applied,
):
    query = text(
        """
        UPDATE genius.subscription
        SET
            client_code = :client_code,
            installation = :installation,
            plan_code = :plan_code,
            status = :status,
            cutoff_day = :cutoff_day,
            credit_day = :credit_day,
            price_applied = :price_applied
        WHERE correlative = :correlative
        """
    )

    try:
        result = db.session.execute(
            query,
            {
                'correlative': correlative,
                'client_code': client_code,
                'installation': installation,
                'plan_code': plan_code,
                'status': status,
                'cutoff_day': cutoff_day,
                'credit_day': credit_day,
                'price_applied': price_applied,
            },
        )
        db.session.commit()
        return result.rowcount > 0
    except SQLAlchemyError as error:
        db.session.rollback()
        if getattr(getattr(error, 'orig', None), 'pgcode', None) == '23505':
            return 'duplicate_installation'
        if getattr(getattr(error, 'orig', None), 'pgcode', None) == '23503':
            return 'invalid_fk'
        current_app.logger.exception('Error de base de datos al actualizar suscripcion: %s', error)
        return False
    except Exception as error:
        db.session.rollback()
        current_app.logger.exception('Error inesperado al actualizar suscripcion: %s', error)
        return False

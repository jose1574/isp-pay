from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from flask import current_app

from flaskr import db


def _has_no_installation_column() -> bool:
    exists = db.session.execute(
        text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = 'genius'
                  AND table_name = 'installations'
                  AND column_name = 'no_installation'
            )
            """
        )
    ).scalar_one()
    return bool(exists)


def _has_contract_number_column() -> bool:
    exists = db.session.execute(
        text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = 'genius'
                  AND table_name = 'installations'
                  AND column_name = 'contract_number'
            )
            """
        )
    ).scalar_one()
    return bool(exists)


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

    has_no_installation = _has_no_installation_column()
    has_contract_number = _has_contract_number_column()

    if has_no_installation:
        installation_alias_expr = "i.no_installation"
    elif has_contract_number:
        installation_alias_expr = "('contrato-' || i.contract_number::text)"
    else:
        installation_alias_expr = "NULL::VARCHAR"

    base_query = f"""
        SELECT
            s.*,
            p.description AS plan_description,
            i.location AS installation_location,
            i.install_date AS installation_date,
            i.mac_address AS installation_mac_address,
            {installation_alias_expr} AS installation_no_installation
        FROM genius.subscription s
        LEFT JOIN genius.plans p ON p.code = s.plan_code
        LEFT JOIN genius.installations i ON i.id = s.installation
        {where_clause}
        ORDER BY s.correlative DESC
    """

    if page is None or per_page is None:
        return db.session.execute(text(base_query), params).fetchall()

    offset = (page - 1) * per_page
    params['limit'] = per_page
    params['offset'] = offset
    return db.session.execute(
        text(base_query + " LIMIT :limit OFFSET :offset"),
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


def get_subscriptions_by_client(client_code: str):
    has_no_installation = _has_no_installation_column()
    has_contract_number = _has_contract_number_column()

    if has_no_installation:
        installation_alias_expr = "i.no_installation"
    elif has_contract_number:
        installation_alias_expr = "('contrato-' || i.contract_number::text)"
    else:
        installation_alias_expr = "NULL::VARCHAR"

    return db.session.execute(
        text(
            f"""
            SELECT
                s.*,
                p.description AS plan_description,
                {installation_alias_expr} AS installation_no_installation,
                i.location AS installation_location,
                i.install_date AS installation_date,
                i.mac_address AS installation_mac_address
            FROM genius.subscription s
            LEFT JOIN genius.plans p ON p.code = s.plan_code
            LEFT JOIN genius.installations i ON i.id = s.installation
            WHERE s.client_code = :client_code
            ORDER BY s.correlative DESC
            """
        ),
        {'client_code': client_code},
    ).fetchall()


def get_subscription(correlative: int):
    return db.session.execute(
        text(
            """
            SELECT *
            FROM genius.subscription
            WHERE correlative = :correlative
            LIMIT 1
            """
        ),
        {'correlative': correlative},
    ).first()


def get_installations_by_client(client_code: str):
    has_no_installation = _has_no_installation_column()
    has_contract_number = _has_contract_number_column()

    if has_no_installation:
        query = text(
            """
            SELECT id, client_code, no_installation, install_date, location, mac_address
            FROM genius.installations
            WHERE client_code = :client_code
            ORDER BY COALESCE(NULLIF(regexp_replace(lower(no_installation), '[^0-9]', '', 'g'), '')::INTEGER, 0) ASC, id ASC
            """
        )
    elif has_contract_number:
        query = text(
            """
            SELECT id, client_code, ('contrato-' || contract_number::text) AS no_installation, install_date, location, mac_address
            FROM genius.installations
            WHERE client_code = :client_code
            ORDER BY contract_number ASC, id ASC
            """
        )
    else:
        query = text(
            """
            SELECT id, client_code, NULL::VARCHAR AS no_installation, install_date, location, mac_address
            FROM genius.installations
            WHERE client_code = :client_code
            ORDER BY id ASC
            """
        )

    return db.session.execute(query, {'client_code': client_code}).fetchall()


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


def delete_subscription(correlative, client_code):
    query = text(
        """
        DELETE FROM genius.subscription
        WHERE correlative = :correlative
          AND client_code = :client_code
        """
    )

    try:
        result = db.session.execute(
            query,
            {
                'correlative': correlative,
                'client_code': client_code,
            },
        )
        db.session.commit()
        return result.rowcount > 0
    except SQLAlchemyError as error:
        db.session.rollback()
        current_app.logger.exception('Error de base de datos al eliminar suscripcion: %s', error)
        return False
    except Exception as error:
        db.session.rollback()
        current_app.logger.exception('Error inesperado al eliminar suscripcion: %s', error)
        return False


def update_subscription_status(correlative: int, status: str):
    try:
        result = db.session.execute(
            text(
                """
                UPDATE genius.subscription
                SET status = :status
                WHERE correlative = :correlative
                """
            ),
            {
                'correlative': correlative,
                'status': status,
            },
        )
        db.session.commit()
        return result.rowcount > 0
    except SQLAlchemyError as error:
        db.session.rollback()
        current_app.logger.exception('Error de base de datos al actualizar estado de suscripcion: %s', error)
        return False
    except Exception as error:
        db.session.rollback()
        current_app.logger.exception('Error inesperado al actualizar estado de suscripcion: %s', error)
        return False


def get_overdue_active_subscriptions(reference_date=None):
    params = {}
    date_expression = 'CURRENT_DATE'

    if reference_date is not None:
        date_expression = ':reference_date'
        params['reference_date'] = reference_date

    return db.session.execute(
        text(
            f"""
            SELECT
                s.correlative,
                s.client_code,
                s.installation,
                s.status,
                s.cutoff_day,
                s.credit_day,
                i.mac_address AS installation_mac_address
            FROM genius.subscription s
            LEFT JOIN genius.installations i ON i.id = s.installation
            WHERE s.status = 'activo'
              AND s.cutoff_day IS NOT NULL
              AND s.credit_day IS NOT NULL
              AND {date_expression} > (s.cutoff_day + s.credit_day)
            ORDER BY s.cutoff_day ASC, s.correlative ASC
            """
        )
        ,
        params,
    ).fetchall()

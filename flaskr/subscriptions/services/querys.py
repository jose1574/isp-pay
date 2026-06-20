from datetime import date, timedelta

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


def _subscription_installation_alias_expr(has_no_installation: bool, has_contract_number: bool) -> str:
    if has_no_installation:
        return "i.no_installation"
    if has_contract_number:
        return "('contrato-' || i.contract_number::text)"
    return "NULL::VARCHAR"


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
    has_no_installation = _has_no_installation_column()
    has_contract_number = _has_contract_number_column()
    installation_alias_expr = _subscription_installation_alias_expr(has_no_installation, has_contract_number)

    if search:
        where_clause = f"""
            WHERE s.client_code ILIKE :search
               OR COALESCE(c.description, '') ILIKE :search
               OR s.plan_code ILIKE :search
               OR COALESCE(p.description, '') ILIKE :search
               OR s.status ILIKE :search
               OR CAST(s.installation AS TEXT) ILIKE :search
               OR COALESCE({installation_alias_expr}, '') ILIKE :search
               OR CAST(s.cutoff_day AS TEXT) ILIKE :search
               OR CAST(s.credit_day AS TEXT) ILIKE :search
               OR CAST(s.price_applied AS TEXT) ILIKE :search
        """
        params['search'] = f"%{search}%"

    base_query = f"""
        SELECT
            s.*,
            c.description AS client_name,
            p.description AS plan_description,
            i.location AS installation_location,
            i.install_date AS installation_date,
            i.mac_address AS installation_mac_address,
            i.route_id,
            {installation_alias_expr} AS installation_no_installation
        FROM genius.subscription s
        LEFT JOIN clients c ON c.code = s.client_code
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
    has_no_installation = _has_no_installation_column()
    has_contract_number = _has_contract_number_column()
    installation_alias_expr = _subscription_installation_alias_expr(has_no_installation, has_contract_number)

    if search:
        where_clause = f"""
            WHERE s.client_code ILIKE :search
               OR COALESCE(c.description, '') ILIKE :search
               OR s.plan_code ILIKE :search
               OR COALESCE(p.description, '') ILIKE :search
               OR s.status ILIKE :search
               OR CAST(s.installation AS TEXT) ILIKE :search
               OR COALESCE({installation_alias_expr}, '') ILIKE :search
               OR CAST(s.cutoff_day AS TEXT) ILIKE :search
               OR CAST(s.credit_day AS TEXT) ILIKE :search
               OR CAST(s.price_applied AS TEXT) ILIKE :search
        """
        params['search'] = f"%{search}%"

    return db.session.execute(
        text(
            f"""
            SELECT COUNT(*)
            FROM genius.subscription s
            LEFT JOIN clients c ON c.code = s.client_code
            LEFT JOIN genius.plans p ON p.code = s.plan_code
            LEFT JOIN genius.installations i ON i.id = s.installation
            {where_clause}
            """
        ),
        params,
    ).scalar_one()


def get_subscriptions_by_client(client_code: str):
    has_no_installation = _has_no_installation_column()
    has_contract_number = _has_contract_number_column()

    installation_alias_expr = _subscription_installation_alias_expr(has_no_installation, has_contract_number)

    return db.session.execute(
        text(
            f"""
            SELECT
                s.*,
                c.description AS client_name,
                p.description AS plan_description,
                {installation_alias_expr} AS installation_no_installation,
                i.location AS installation_location,
                i.install_date AS installation_date,
                i.mac_address AS installation_mac_address
            FROM genius.subscription s
            LEFT JOIN clients c ON c.code = s.client_code
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


def _upsert_subscription_receivable_link(
    receivable_correlative: int,
    subscription_correlative: int,
    client_code: str,
    emission_date,
    amount: float,
):
    payment_status_expr = """
        COALESCE(
            (
                SELECT
                    CASE
                        WHEN COALESCE(r.balance, COALESCE(r.total, 0) - COALESCE(r.payment_applied, 0)) <= 0.01 THEN 'paid_pending_activation'
                        WHEN COALESCE(r.payment_applied, 0) > 0 THEN 'partial_payment'
                        ELSE 'pending_payment'
                    END
                FROM public.receivable r
                WHERE r.correlative = :receivable_correlative
                LIMIT 1
            ),
            'pending_payment'
        )
    """

    exists = db.session.execute(
        text(
            """
            SELECT id
            FROM genius.subscription_receivable_link
            WHERE receivable_correlative = :receivable_correlative
            LIMIT 1
            """
        ),
        {'receivable_correlative': receivable_correlative},
    ).first()

    if exists:
        db.session.execute(
            text(
                """
                UPDATE genius.subscription_receivable_link
                SET
                    subscription_correlative = :subscription_correlative,
                    client_code = :client_code,
                    emission_date = :emission_date,
                    amount = :amount,
                    payment_status = {payment_status_expr},
                    updated_at = NOW()
                WHERE receivable_correlative = :receivable_correlative
                """.format(payment_status_expr=payment_status_expr)
            ),
            {
                'receivable_correlative': receivable_correlative,
                'subscription_correlative': subscription_correlative,
                'client_code': client_code,
                'emission_date': emission_date,
                'amount': amount,
            },
        )
        return

    db.session.execute(
        text(
            """
            INSERT INTO genius.subscription_receivable_link (
                receivable_correlative,
                subscription_correlative,
                client_code,
                emission_date,
                amount,
                payment_status,
                created_at,
                updated_at
            )
            VALUES (
                :receivable_correlative,
                :subscription_correlative,
                :client_code,
                :emission_date,
                :amount,
                {payment_status_expr},
                NOW(),
                NOW()
            )
            """.format(payment_status_expr=payment_status_expr)
        ),
        {
            'receivable_correlative': receivable_correlative,
            'subscription_correlative': subscription_correlative,
            'client_code': client_code,
            'emission_date': emission_date,
            'amount': amount,
        },
    )

def get_overdue_active_subscriptions(reference_date=None):
    params = {}
    date_expression = 'CURRENT_DATE'

    if reference_date is not None:
        date_expression = ':reference_date'
        params['reference_date'] = reference_date

    current_cutoff_expr = f"""
        (
            date_trunc('month', {date_expression})::date
            + (
                LEAST(
                    EXTRACT(DAY FROM s.cutoff_day)::int,
                    EXTRACT(
                        DAY FROM (
                            date_trunc('month', {date_expression})
                            + INTERVAL '1 month - 1 day'
                        )
                    )::int
                ) - 1
            ) * INTERVAL '1 day'
        )::date
    """

    previous_cutoff_expr = f"""
        (
            date_trunc('month', (CAST({date_expression} AS DATE) - INTERVAL '1 month'))::date
            + (
                LEAST(
                    EXTRACT(DAY FROM s.cutoff_day)::int,
                    EXTRACT(
                        DAY FROM (
                            date_trunc('month', (CAST({date_expression} AS DATE) - INTERVAL '1 month'))
                            + INTERVAL '1 month - 1 day'
                        )
                    )::int
                ) - 1
            ) * INTERVAL '1 day'
        )::date
    """

    billing_period_cutoff_expr = f"""
        (
            CASE
                WHEN CAST({date_expression} AS DATE) >= ({current_cutoff_expr}) THEN ({current_cutoff_expr})
                ELSE ({previous_cutoff_expr})
            END
        )
    """

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
                {billing_period_cutoff_expr} AS billing_period_cutoff,
                c.description AS client_name,
                c.address AS client_address,
                c.phone AS client_phone,
                p.description AS plan_description,
                COALESCE(s.price_applied, p.price, 0) AS receivable_amount,
                p.coin AS plan_coin,
                i.mac_address AS installation_mac_address,
                i.route_id
            FROM genius.subscription s
            LEFT JOIN clients c ON c.code = s.client_code
            LEFT JOIN genius.plans p ON p.code = s.plan_code
            LEFT JOIN genius.installations i ON i.id = s.installation
            WHERE s.status = 'activo'
              AND s.cutoff_day IS NOT NULL
              AND s.credit_day IS NOT NULL
              AND CAST({date_expression} AS DATE) > ({billing_period_cutoff_expr} + s.credit_day)
              AND (
                  NOT EXISTS (
                      SELECT 1
                      FROM genius.subscription_receivable_link l
                      WHERE l.subscription_correlative = s.correlative
                        AND l.emission_date = ({billing_period_cutoff_expr})
                  )
                  OR EXISTS (
                      SELECT 1
                      FROM genius.subscription_receivable_link l
                      LEFT JOIN public.receivable r ON r.correlative = l.receivable_correlative
                      WHERE l.subscription_correlative = s.correlative
                        AND l.emission_date = ({billing_period_cutoff_expr})
                        AND (
                            CASE
                                WHEN r.correlative IS NULL THEN COALESCE(l.amount, 0)
                                ELSE COALESCE(r.balance, COALESCE(r.total, 0) - COALESCE(r.payment_applied, 0))
                            END
                        ) > 0.01
                  )
              )
            ORDER BY s.cutoff_day ASC, s.correlative ASC
            """
        ),
        params,
    ).fetchall()


def get_due_active_subscriptions(reference_date=None):
    params = {}
    date_expression = 'CURRENT_DATE'

    if reference_date is not None:
        date_expression = ':reference_date'
        params['reference_date'] = reference_date

    current_cutoff_expr = f"""
        (
            date_trunc('month', {date_expression})::date
            + (
                LEAST(
                    EXTRACT(DAY FROM s.cutoff_day)::int,
                    EXTRACT(
                        DAY FROM (
                            date_trunc('month', {date_expression})
                            + INTERVAL '1 month - 1 day'
                        )
                    )::int
                ) - 1
            ) * INTERVAL '1 day'
        )::date
    """

    previous_cutoff_expr = f"""
        (
            date_trunc('month', (CAST({date_expression} AS DATE) - INTERVAL '1 month'))::date
            + (
                LEAST(
                    EXTRACT(DAY FROM s.cutoff_day)::int,
                    EXTRACT(
                        DAY FROM (
                            date_trunc('month', (CAST({date_expression} AS DATE) - INTERVAL '1 month'))
                            + INTERVAL '1 month - 1 day'
                        )
                    )::int
                ) - 1
            ) * INTERVAL '1 day'
        )::date
    """

    billing_period_cutoff_expr = f"""
        (
            CASE
                WHEN CAST({date_expression} AS DATE) >= ({current_cutoff_expr}) THEN ({current_cutoff_expr})
                ELSE ({previous_cutoff_expr})
            END
        )
    """

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
                {billing_period_cutoff_expr} AS billing_period_cutoff,
                c.description AS client_name,
                c.address AS client_address,
                c.phone AS client_phone,
                p.description AS plan_description,
                COALESCE(s.price_applied, p.price, 0) AS receivable_amount,
                p.coin AS plan_coin,
                i.mac_address AS installation_mac_address,
                i.route_id
            FROM genius.subscription s
            LEFT JOIN clients c ON c.code = s.client_code
            LEFT JOIN genius.plans p ON p.code = s.plan_code
            LEFT JOIN genius.installations i ON i.id = s.installation
            WHERE s.status = 'activo'
              AND s.cutoff_day IS NOT NULL
              AND s.credit_day IS NOT NULL
              AND CAST({date_expression} AS DATE) >= ({billing_period_cutoff_expr})
              AND CAST({date_expression} AS DATE) <= ({billing_period_cutoff_expr} + s.credit_day)
            ORDER BY s.cutoff_day ASC, s.correlative ASC
            """
        ),
        params,
    ).fetchall()


def create_receivable_for_overdue_subscription(subscription, reference_date=None):
    emission_date = getattr(subscription, 'billing_period_cutoff', None)
    if emission_date is None:
        emission_date = reference_date or date.today()
    credit_days = int(getattr(subscription, 'credit_day', 0) or 0)
    expiration_date = emission_date + timedelta(days=credit_days)

    client_code = str(getattr(subscription, 'client_code', '') or '').strip()
    if not client_code:
        return False, 'No se pudo crear cuenta por cobrar: client_code vacio.'

    client_name = str(getattr(subscription, 'client_name', '') or '').strip() or client_code
    client_address = str(getattr(subscription, 'client_address', '') or '').strip()
    client_phone = str(getattr(subscription, 'client_phone', '') or '').strip()
    plan_description = str(getattr(subscription, 'plan_description', '') or '').strip()

    raw_amount = getattr(subscription, 'receivable_amount', 0) or 0
    try:
        amount = float(raw_amount)
    except (TypeError, ValueError):
        return False, (
            f'No se pudo crear cuenta por cobrar para suscripcion {subscription.correlative}: '
            f'monto invalido ({raw_amount}).'
        )

    if amount <= 0:
        return False, (
            f'No se pudo crear cuenta por cobrar para suscripcion {subscription.correlative}: '
            'el monto calculado es menor o igual a cero.'
        )

    coin_code = str(getattr(subscription, 'plan_coin', '') or '').strip()
    if not coin_code:
        coin_code = db.session.execute(
            text("SELECT code FROM public.coin ORDER BY code LIMIT 1")
        ).scalar() or 'USD'

    month_names = {
        1: 'enero',
        2: 'febrero',
        3: 'marzo',
        4: 'abril',
        5: 'mayo',
        6: 'junio',
        7: 'julio',
        8: 'agosto',
        9: 'septiembre',
        10: 'octubre',
        11: 'noviembre',
        12: 'diciembre',
    }
    period_month = month_names.get(emission_date.month, str(emission_date.month))
    period_label = f'{period_month} {emission_date.year}'

    service_label = 'Servicio prepago'
    if plan_description:
        service_label = f'{service_label} {plan_description}'

    description = f"{service_label} {period_label} - suscripcion #{subscription.correlative}"
    comments = (
        f"Generada automaticamente por vencimiento de suscripcion #{subscription.correlative}. "
        f"Mes facturado: {period_label}."
    )

    linked_receivable = db.session.execute(
        text(
            """
            SELECT receivable_correlative
            FROM genius.subscription_receivable_link
            WHERE subscription_correlative = :subscription_correlative
              AND emission_date = :emission_date
            LIMIT 1
            """
        ),
        {
            'subscription_correlative': subscription.correlative,
            'emission_date': emission_date,
        },
    ).first()

    if linked_receivable:
        _upsert_subscription_receivable_link(
            receivable_correlative=linked_receivable.receivable_correlative,
            subscription_correlative=subscription.correlative,
            client_code=client_code,
            emission_date=emission_date,
            amount=amount,
        )
        db.session.commit()
        return True, None

    already_exists = db.session.execute(
        text(
            """
            SELECT correlative
            FROM public.receivable
            WHERE operation_type = 'RECEIVABLE'
              AND client_code = :client_code
              AND description = :description
              AND emission_date = :emission_date
            LIMIT 1
            """
        ),
        {
            'client_code': client_code,
            'description': description,
            'emission_date': emission_date,
        },
    ).first()

    if already_exists:
        _upsert_subscription_receivable_link(
            receivable_correlative=already_exists.correlative,
            subscription_correlative=subscription.correlative,
            client_code=client_code,
            emission_date=emission_date,
            amount=amount,
        )
        db.session.commit()
        return True, None

    try:
        receivable_correlative = db.session.execute(
            text(
                """
                SELECT public.set_receivable(
                    :p_correlative,
                    :p_operation_type,
                    :p_document_no,
                    :p_control_no,
                    :p_emission_date,
                    :p_client_code,
                    :p_client_name,
                    :p_client_id,
                    :p_client_address,
                    :p_client_phone,
                    :p_client_name_fiscal,
                    :p_credit_days,
                    :p_expiration_date,
                    :p_description,
                    :p_comments,
                    :p_seller,
                    :p_user_code,
                    :p_station,
                    :p_total_net,
                    :p_total_tax,
                    :p_total,
                    :p_credit,
                    :p_debit,
                    :p_balance,
                    :p_fiscal_impresion,
                    :p_fiscal_printer_serial,
                    :p_fiscal_printer_date,
                    :p_fiscal_printer_document,
                    :p_fiscal_printer_z,
                    :p_coin_code,
                    :p_indexing_factor,
                    :p_indexing,
                    :p_indexing_coin,
                    :p_indexing_correlative_origin,
                    :p_indexing_module_origin,
                    :p_total_exempt,
                    :p_base_igtf,
                    :p_percent_igtf,
                    :p_igtf
                ) AS receivable_correlative
                """
            ),
            {
                'p_correlative': 0,
                'p_operation_type': 'RECEIVABLE',
                'p_document_no': '',
                'p_control_no': '',
                'p_emission_date': emission_date,
                'p_client_code': client_code,
                'p_client_name': client_name,
                'p_client_id': client_code,
                'p_client_address': client_address,
                'p_client_phone': client_phone,
                'p_client_name_fiscal': 0,
                'p_credit_days': credit_days,
                'p_expiration_date': expiration_date,
                'p_description': description,
                'p_comments': comments,
                'p_seller': '00',
                'p_user_code': '00',
                'p_station': '00',
                'p_total_net': amount,
                'p_total_tax': 0.0,
                'p_total': amount,
                'p_credit': 0.0,
                'p_debit': amount,
                'p_balance': amount,
                'p_fiscal_impresion': False,
                'p_fiscal_printer_serial': '',
                'p_fiscal_printer_date': None,
                'p_fiscal_printer_document': '',
                'p_fiscal_printer_z': '',
                'p_coin_code': coin_code,
                'p_indexing_factor': 1.0,
                'p_indexing': False,
                'p_indexing_coin': coin_code,
                'p_indexing_correlative_origin': 0,
                'p_indexing_module_origin': 'AUTOMATION',
                'p_total_exempt': 0.0,
                'p_base_igtf': 0.0,
                'p_percent_igtf': 0.0,
                'p_igtf': 0.0,
            },
        ).scalar_one()

        _upsert_subscription_receivable_link(
            receivable_correlative=receivable_correlative,
            subscription_correlative=subscription.correlative,
            client_code=client_code,
            emission_date=emission_date,
            amount=amount,
        )
        db.session.commit()
        return True, receivable_correlative
    except SQLAlchemyError as error:
        db.session.rollback()
        current_app.logger.exception(
            'Error de base de datos al crear cuenta por cobrar para suscripcion %s: %s',
            getattr(subscription, 'correlative', 'N/A'),
            error,
        )
        return False, (
            f'Error de base de datos al crear cuenta por cobrar para suscripcion '
            f'{getattr(subscription, "correlative", "N/A")}: {error}'
        )
    except Exception as error:
        db.session.rollback()
        current_app.logger.exception(
            'Error inesperado al crear cuenta por cobrar para suscripcion %s: %s',
            getattr(subscription, 'correlative', 'N/A'),
            error,
        )
        return False, (
            f'Error inesperado al crear cuenta por cobrar para suscripcion '
            f'{getattr(subscription, "correlative", "N/A")}: {error}'
        )

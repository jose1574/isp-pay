from decimal import Decimal, InvalidOperation
from datetime import date

from flask import render_template, request, redirect, url_for, flash
from flaskr.clients.services.querys import get_clients, get_clients_count, get_client

from . import subscriptions_bp
from .services.querys import (
    get_coins,
    get_plan,
    get_plans,
    get_subscriptions,
    get_subscriptions_count,
    get_installations_by_client,
    get_subscription_by_installation,
    create_subscription,
    update_subscription,
    create_plan,
    update_plan,
    delete_plan,
)


STATUS_OPTIONS = [
    'activo',
    'suspendido_por_falta_de_pago',
    'suspendido_temporal',
    'retirado',
]


@subscriptions_bp.route('/')
def subscriptions():
    q = (request.args.get('q') or '').strip()

    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        page = 1

    try:
        per_page = int(request.args.get('per_page', 10))
    except ValueError:
        per_page = 10

    page = max(1, page)
    per_page = min(max(5, per_page), 100)

    total_subscriptions = get_subscriptions_count(search=q)
    total_pages = max(1, (total_subscriptions + per_page - 1) // per_page)

    if page > total_pages:
        page = total_pages

    subscriptions = get_subscriptions(page=page, per_page=per_page, search=q)
    return render_template(
        'subscriptions.html',
        subscriptions=subscriptions,
        q=q,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        total_subscriptions=total_subscriptions,
    )


@subscriptions_bp.route('/subscription', methods=['GET'])
def subscription():
    code = (request.args.get('code') or '').strip()
    raw_installation = (request.args.get('installation') or '').strip()

    client = get_client(code) if code else None
    installations = get_installations_by_client(client.code) if client else []

    selected_installation = None
    if raw_installation:
        try:
            selected_installation = int(raw_installation)
        except ValueError:
            selected_installation = None

    installation_ids = [row.id for row in installations]
    if selected_installation not in installation_ids:
        selected_installation = installation_ids[0] if installation_ids else None

    current_subscription = get_subscription_by_installation(selected_installation) if selected_installation else None
    plans_list = get_plans()
    default_credit_day = current_subscription.credit_day if current_subscription and current_subscription.credit_day is not None else (client.credit_days if client and getattr(client, 'credit_days', None) is not None else '')

    return render_template(
        'subscription.html',
        code=client.code if client else code,
        client=client,
        installations=installations,
        selected_installation=selected_installation,
        subscription=current_subscription,
        default_credit_day=default_credit_day,
        plans=plans_list,
        status_options=STATUS_OPTIONS,
        form_enabled=True,
    )


@subscriptions_bp.route('/get_subscription', methods=['GET'])
def search_subscription():
    code = (request.args.get('code') or '').strip()
    raw_installation = (request.args.get('installation') or '').strip()

    if not code:
        context = {
            'code': '',
            'client': None,
            'installations': [],
            'selected_installation': None,
            'subscription': None,
            'plans': get_plans(),
            'status_options': STATUS_OPTIONS,
            'form_enabled': True,
        }

        if request.headers.get('HX-Request') == 'true':
            return render_template('partials/subscription_form.html', **context)

        return render_template('subscription.html', **context)

    client = get_client(code)
    if not client:
        flash('Cliente no encontrado, verifique el codigo.', 'warning')
        if request.headers.get('HX-Request') == 'true':
            return ('', 204, {'HX-Redirect': url_for('subscriptions.subscription', code=code)})

        return redirect(url_for('subscriptions.subscription', code=code))

    installations = get_installations_by_client(client.code)
    selected_installation = None
    if raw_installation:
        try:
            selected_installation = int(raw_installation)
        except ValueError:
            selected_installation = None

    installation_ids = [row.id for row in installations]
    if selected_installation not in installation_ids:
        selected_installation = installation_ids[0] if installation_ids else None

    current_subscription = get_subscription_by_installation(selected_installation) if selected_installation else None
    default_credit_day = current_subscription.credit_day if current_subscription and current_subscription.credit_day is not None else (client.credit_days if getattr(client, 'credit_days', None) is not None else '')
    context = {
        'code': client.code,
        'client': client,
        'installations': installations,
        'selected_installation': selected_installation,
        'subscription': current_subscription,
        'default_credit_day': default_credit_day,
        'plans': get_plans(),
        'status_options': STATUS_OPTIONS,
        'form_enabled': True,
    }

    if request.headers.get('HX-Request') == 'true':
        return render_template('partials/subscription_form.html', **context)

    return render_template('subscription.html', **context)


@subscriptions_bp.route('/subscription/save', methods=['POST'])
def save_subscription():
    code = (request.form.get('code') or '').strip()
    raw_correlative = (request.form.get('correlative') or '').strip()
    raw_installation = (request.form.get('installation') or '').strip()
    plan_code = (request.form.get('plan_code') or '').strip()
    status = (request.form.get('status') or '').strip()
    raw_cutoff_day = (request.form.get('cutoff_day') or '').strip()
    raw_credit_day = (request.form.get('credit_day') or '').strip()
    raw_price_applied = (request.form.get('price_applied') or '').strip()

    if not code:
        flash('Debe indicar un cliente para guardar la suscripcion.', 'warning')
        return redirect(url_for('subscriptions.subscription'))

    if not raw_installation or not plan_code or not status:
        flash('Instalacion, plan y estado son obligatorios.', 'warning')
        return redirect(url_for('subscriptions.subscription', code=code, installation=raw_installation or None))

    if status not in STATUS_OPTIONS:
        flash('El estado seleccionado no es valido.', 'warning')
        return redirect(url_for('subscriptions.subscription', code=code, installation=raw_installation))

    try:
        installation = int(raw_installation)
    except ValueError:
        flash('La instalacion seleccionada no es valida.', 'warning')
        return redirect(url_for('subscriptions.subscription', code=code))

    cutoff_day = None
    if raw_cutoff_day:
        try:
            cutoff_day = date.fromisoformat(raw_cutoff_day)
        except ValueError:
            flash('La fecha de cobro es invalida.', 'warning')
            return redirect(url_for('subscriptions.subscription', code=code, installation=installation))

    credit_day = None
    if raw_credit_day:
        try:
            credit_day = int(raw_credit_day)
        except ValueError:
            flash('Dia de credito invalido.', 'warning')
            return redirect(url_for('subscriptions.subscription', code=code, installation=installation))

        if credit_day < 1 or credit_day > 31:
            flash('Dia de credito debe estar entre 1 y 31.', 'warning')
            return redirect(url_for('subscriptions.subscription', code=code, installation=installation))

    try:
        price_applied = Decimal(raw_price_applied.replace(',', '.')) if raw_price_applied else None
    except InvalidOperation:
        flash('El precio aplicado no es valido.', 'warning')
        return redirect(url_for('subscriptions.subscription', code=code, installation=installation))

    if price_applied is not None and price_applied < 0:
        flash('El precio aplicado no puede ser negativo.', 'warning')
        return redirect(url_for('subscriptions.subscription', code=code, installation=installation))

    client = get_client(code)
    if not client:
        flash('Cliente no encontrado.', 'warning')
        return redirect(url_for('subscriptions.subscription', code=code))

    valid_installations = {row.id for row in get_installations_by_client(code)}
    if installation not in valid_installations:
        flash('La instalacion no pertenece al cliente seleccionado.', 'warning')
        return redirect(url_for('subscriptions.subscription', code=code))

    existing_for_installation = get_subscription_by_installation(installation)

    if raw_correlative:
        try:
            correlative = int(raw_correlative)
        except ValueError:
            flash('Identificador de suscripcion invalido.', 'warning')
            return redirect(url_for('subscriptions.subscription', code=code, installation=installation))

        if existing_for_installation and existing_for_installation.correlative != correlative:
            flash('Ya existe una suscripcion asignada a esta instalacion.', 'warning')
            return redirect(url_for('subscriptions.subscription', code=code, installation=installation))

        result = update_subscription(
            correlative=correlative,
            client_code=code,
            installation=installation,
            plan_code=plan_code,
            status=status,
            cutoff_day=cutoff_day,
            credit_day=credit_day,
            price_applied=price_applied,
        )

        if result == 'duplicate_installation':
            flash('No se puede asignar dos suscripciones a la misma instalacion.', 'warning')
            return redirect(url_for('subscriptions.subscription', code=code, installation=installation))

        if result == 'invalid_fk':
            flash('Plan o instalacion invalida.', 'warning')
            return redirect(url_for('subscriptions.subscription', code=code, installation=installation))

        if not result:
            flash('No fue posible actualizar la suscripcion.', 'danger')
            return redirect(url_for('subscriptions.subscription', code=code, installation=installation))

        flash('Suscripcion actualizada correctamente.', 'success')
        return redirect(url_for('subscriptions.subscription', code=code, installation=installation))

    if existing_for_installation:
        flash('Ya existe una suscripcion para esa instalacion.', 'warning')
        return redirect(url_for('subscriptions.subscription', code=code, installation=installation))

    result = create_subscription(
        client_code=code,
        installation=installation,
        plan_code=plan_code,
        status=status,
        cutoff_day=cutoff_day,
        credit_day=credit_day,
        price_applied=price_applied,
    )

    if result == 'duplicate_installation':
        flash('No se puede asignar dos suscripciones a la misma instalacion.', 'warning')
        return redirect(url_for('subscriptions.subscription', code=code, installation=installation))

    if result == 'invalid_fk':
        flash('Plan o instalacion invalida.', 'warning')
        return redirect(url_for('subscriptions.subscription', code=code, installation=installation))

    if not result:
        flash('No fue posible crear la suscripcion.', 'danger')
        return redirect(url_for('subscriptions.subscription', code=code, installation=installation))

    flash('Suscripcion creada correctamente.', 'success')
    return redirect(url_for('subscriptions.subscription', code=code, installation=installation))


@subscriptions_bp.route('/plans')
def plans():
    code = (request.args.get('code') or '').strip()
    plan = get_plan(code) if code else None
    coins = get_coins()

    return render_template(
        'plans.html',
        plan=plan,
        code=plan.code if plan else code,
        coins=coins,
        form_enabled=True,
    )


@subscriptions_bp.route('/get_plan', methods=['GET'])
def search_plan():
    code = (request.args.get('code') or '').strip()
    plan = get_plan(code) if code else None
    coins = get_coins()

    if plan:
        if request.headers.get('HX-Request') == 'true':
            return render_template(
                'partials/plan_form.html',
                plan=plan,
                code=plan.code,
                coins=coins,
                form_enabled=True,
            )

        return render_template(
            'plans.html',
            plan=plan,
            code=plan.code,
            coins=coins,
            form_enabled=True,
        )

    if request.headers.get('HX-Request') == 'true':
        return render_template(
            'partials/plan_form.html',
            plan=None,
            code=code,
            coins=coins,
            form_enabled=True,
        )

    flash('Plan no encontrado, puede crear uno nuevo.', 'warning')
    return render_template(
        'plans.html',
        plan=None,
        code=code,
        coins=coins,
        form_enabled=True,
    )


@subscriptions_bp.route('/plans/save', methods=['POST'])
def save_plan():
    code = (request.form.get('code') or '').strip()
    description = (request.form.get('description') or '').strip()
    comment = (request.form.get('comment') or '').strip() or None
    coin = (request.form.get('coin') or '').strip()
    raw_price = (request.form.get('price') or '').strip()

    if not code or not description:
        flash('Code y descripcion son obligatorios.', 'warning')
        return redirect(url_for('subscriptions.plans', code=code))

    if not coin:
        flash('Debe seleccionar una moneda.', 'warning')
        return redirect(url_for('subscriptions.plans', code=code))

    if not raw_price:
        flash('Debe ingresar un precio.', 'warning')
        return redirect(url_for('subscriptions.plans', code=code))

    try:
        price = Decimal(raw_price.replace(',', '.'))
    except InvalidOperation:
        flash('El precio ingresado no es valido.', 'warning')
        return redirect(url_for('subscriptions.plans', code=code))

    if price < 0:
        flash('El precio no puede ser negativo.', 'warning')
        return redirect(url_for('subscriptions.plans', code=code))

    existing_plan = get_plan(code)

    if existing_plan:
        saved = update_plan(
            code=code,
            description=description,
            comment=comment,
            coin=coin,
            price=price,
        )

        if saved == 'invalid_coin':
            flash('La moneda seleccionada no existe en la tabla coin.', 'warning')
            return redirect(url_for('subscriptions.plans', code=code))

        if not saved:
            flash('No fue posible actualizar el plan.', 'danger')
            return redirect(url_for('subscriptions.plans', code=code))

        flash('Plan actualizado correctamente.', 'success')
        return redirect(url_for('subscriptions.plans', code=code))

    saved = create_plan(
        code=code,
        description=description,
        comment=comment,
        coin=coin,
        price=price,
    )

    if saved == 'duplicate_code':
        flash('Ya existe un plan con ese codigo.', 'warning')
        return redirect(url_for('subscriptions.plans', code=code))

    if saved == 'invalid_coin':
        flash('La moneda seleccionada no existe en la tabla coin.', 'warning')
        return redirect(url_for('subscriptions.plans', code=code))

    if not saved:
        flash('No fue posible guardar el plan.', 'danger')
        return redirect(url_for('subscriptions.plans', code=code))

    flash('Plan creado correctamente.', 'success')
    return redirect(url_for('subscriptions.plans', code=code))


@subscriptions_bp.route('/plans/delete', methods=['POST'])
def remove_plan():
    code = (request.form.get('code') or '').strip()

    if not code:
        flash('Debe indicar el codigo del plan a eliminar.', 'warning')
        return redirect(url_for('subscriptions.plans'))

    deleted = delete_plan(code)
    if not deleted:
        flash('No fue posible eliminar el plan.', 'danger')
        return redirect(url_for('subscriptions.plans', code=code))

    flash('Plan eliminado correctamente.', 'warning')
    return redirect(url_for('subscriptions.plans'))


@subscriptions_bp.route('/modal_plans')
def modal_plans():
    q = (request.args.get('q') or '').strip()
    plans = get_plans(search=q)

    return render_template(
        'partials/modal_plans.html',
        plans=plans,
        q=q,
        total_plans=len(plans),
    )


@subscriptions_bp.route('/modal_clients', methods=['GET'])
def modal_clients():
    q = (request.args.get('q') or '').strip()

    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        page = 1

    try:
        per_page = int(request.args.get('per_page', 10))
    except ValueError:
        per_page = 10

    page = max(1, page)
    per_page = min(max(5, per_page), 100)

    total_clients = get_clients_count(search=q)
    total_pages = max(1, (total_clients + per_page - 1) // per_page)

    if page > total_pages:
        page = total_pages

    clients = get_clients(page=page, per_page=per_page, search=q)
    return render_template(
        'partials/modal_clients_subscriptions.html',
        clients=clients,
        q=q,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        total_clients=total_clients,
    )


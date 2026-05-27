import base64

from flask import render_template, request, url_for, flash, redirect, current_app
from . import installations_bp
from werkzeug.utils import secure_filename

from flaskr.clients.services.querys import get_clients, get_clients_count, get_client
from .services.querys import (
    get_installations,
    get_installations_count,
    create_installation,
    create_installation_media,
    get_latest_installation_by_client,
    get_installation,
    get_installation_media,
    update_installation,
    upsert_installation_media,
    delete_installation,
)


def _build_installation_context(client_code, installation_id=None):
    installation = None

    if installation_id:
        installation = get_installation(installation_id)
        if installation and client_code and installation.client_code != client_code:
            installation = None

    if installation is None and client_code:
        installation = get_latest_installation_by_client(client_code)

    media_urls = {}

    if installation:
        media_rows = get_installation_media(installation.id)
        for row in media_rows:
            if row.media_type in media_urls:
                continue

            file_data = bytes(row.file_data) if row.file_data is not None else b''
            if not file_data:
                continue

            mime_type = row.mime_type or 'application/octet-stream'
            b64_data = base64.b64encode(file_data).decode('ascii')
            media_urls[row.media_type] = f"data:{mime_type};base64,{b64_data}"

    return {
        'installation': installation,
        'media_urls': media_urls,
    }


@installations_bp.route('/')
def installations():
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

    total_installations = get_installations_count(search=q)
    total_pages = max(1, (total_installations + per_page - 1) // per_page)

    if page > total_pages:
        page = total_pages

    installations = get_installations(page=page, per_page=per_page, search=q)

    return render_template(
        'installations.html',
        installations=installations,
        q=q,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        total_installations=total_installations,
    )

@installations_bp.route('/installation', methods=['GET'])
def installation():
    code = request.args.get('code')
    raw_installation_id = (request.args.get('installation_id') or '').strip()
    installation_id = None
    if raw_installation_id:
        try:
            installation_id = int(raw_installation_id)
        except ValueError:
            installation_id = None

    client = get_client(code) if code else None
    context = _build_installation_context(client.code if client else code, installation_id=installation_id)

    return render_template(
        'installation.html',
        code=client.code if client else code,
        form_enabled=True,
        installation=context['installation'],
        media_urls=context['media_urls'],
    )


@installations_bp.route('/get_client', methods=['GET'])
def search_client():
    raw_code = request.args.get('code') or ''
    code = raw_code.strip()

    # Permite buscar aunque el usuario escriba puntos o guiones en la cedula.
    normalized_code = ''.join(ch for ch in code if ch.isalnum())

    if not code:
        return render_template(
            'partials/installation_form.html',
            code='',
            form_enabled=True,
            installation=None,
            media_urls={},
        )

    client = get_client(code)
    if not client and normalized_code != code:
        client = get_client(normalized_code)

    if client:
        context = _build_installation_context(client.code)

        if request.headers.get('HX-Request') == 'true':
            return render_template(
                'partials/installation_form.html',
                code=client.code,
                form_enabled=True,
                installation=context['installation'],
                media_urls=context['media_urls'],
            )

        return render_template(
            'installation.html',
            code=client.code,
            form_enabled=True,
            installation=context['installation'],
            media_urls=context['media_urls'],
        )

    flash("Cliente no encontrado, ingrese datos para crear un nuevo cliente", "warning")
    if request.headers.get('HX-Request') == 'true':
        return (
            '',
            204,
            {'HX-Redirect': url_for('installations.installation', code=code)}
        )

    return render_template(
        'installation.html',
        code=code,
        form_enabled=True,
        installation=None,
        media_urls={},
    )


@installations_bp.route('/add/save', methods=['POST'])
def save_installation():
    raw_installation_id = (request.form.get('installation_id') or '').strip()
    client_code = request.form.get('code')
    install_date = request.form.get('install_date')
    location = request.form.get('location')
    mac_address = request.form.get('mac_address')
    comment = request.form.get('comment')

    if not client_code:
        flash('Debe ingresar una cedula de cliente antes de guardar.', 'warning')
        return redirect(url_for('installations.installation'))

    if not install_date or not location or not mac_address:
        flash('Complete todos los campos requeridos de la instalacion.', 'warning')
        return redirect(url_for('installations.installation', code=client_code))

    installation_id = None
    if raw_installation_id:
        try:
            installation_id = int(raw_installation_id)
        except ValueError:
            installation_id = None

    was_update = bool(installation_id)

    if was_update:
        update_result = update_installation(
            installation_id=installation_id,
            client_code=client_code,
            install_date=install_date,
            location=location,
            mac_address=mac_address,
            comment=comment,
        )

        if update_result == 'duplicate_client_mac':
            flash('La direccion MAC ya esta registrada en otra instalacion y no puede repetirse.', 'warning')
            return redirect(url_for('installations.installation', code=client_code))

        if not update_result:
            flash('Error al actualizar la instalacion.', 'danger')
            return redirect(url_for('installations.installation', code=client_code))
    else:
        installation_id = create_installation(
            client_code=client_code,
            install_date=install_date,
            location=location,
            mac_address=mac_address,
            comment=comment,
        )

        if installation_id == 'duplicate_client_mac':
            flash('La direccion MAC ya esta registrada en otra instalacion y no puede repetirse.', 'warning')
            return redirect(url_for('installations.installation', code=client_code))

        if not installation_id:
            flash('Error al guardar la instalacion.', 'danger')
            return redirect(url_for('installations.installation', code=client_code))

    media_fields = {
        'image_label_onu': 'image_label_onu',
        'image_installation': 'image_installation',
    }

    for field_name, media_type in media_fields.items():
        uploaded_file = request.files.get(field_name)

        if not uploaded_file or not uploaded_file.filename:
            continue

        safe_name = secure_filename(uploaded_file.filename)
        file_bytes = uploaded_file.read()
        file_size = len(file_bytes) if file_bytes else None

        if not file_bytes:
            continue

        if was_update:
            upsert_installation_media(
                installation_id=installation_id,
                media_type=media_type,
                file_name=safe_name,
                file_data=file_bytes,
                mime_type=uploaded_file.mimetype,
                file_size_bytes=file_size,
            )
        else:
            create_installation_media(
                installation_id=installation_id,
                media_type=media_type,
                file_name=safe_name,
                file_data=file_bytes,
                mime_type=uploaded_file.mimetype,
                file_size_bytes=file_size,
            )

    flash('Se actualizo correctamente la instalacion' if was_update else 'Se guardo correctamente la instalacion', 'success')
    return redirect(url_for('installations.installation', code=client_code))


@installations_bp.route('/delete', methods=['POST'])
def remove_installation():
    raw_installation_id = (request.form.get('installation_id') or '').strip()
    client_code = (request.form.get('code') or '').strip()

    if not raw_installation_id or not client_code:
        flash('No se encontro la instalacion a eliminar.', 'warning')
        return redirect(url_for('installations.installation', code=client_code or None))

    try:
        installation_id = int(raw_installation_id)
    except ValueError:
        flash('Id de instalacion invalido.', 'warning')
        return redirect(url_for('installations.installation', code=client_code))

    deleted = delete_installation(
        installation_id=installation_id,
        client_code=client_code,
    )

    if not deleted:
        flash('No fue posible eliminar la instalacion.', 'danger')
        return redirect(url_for('installations.installation', code=client_code))

    flash('Se elimino correctamente la instalacion.', 'warning')
    return redirect(url_for('installations.installation', code=client_code))


@installations_bp.route('/modal_clients', methods=['GET'])
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
        'partials/modal_clients_installations.html',
        clients=clients,
        q=q,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        total_clients=total_clients,
    )

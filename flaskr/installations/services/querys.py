from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from flask import current_app

from flaskr import db


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




def get_installations(page: int | None = None, per_page: int | None = None, search: str | None = None):
    search = (search or '').strip()
    where_clause = ''
    params = {}
    has_contract_number = _has_contract_number_column()

    if search:
        if has_contract_number:
            where_clause = " WHERE client_code ILIKE :search OR location ILIKE :search OR mac_address ILIKE :search OR comment ILIKE :search OR CAST(contract_number AS TEXT) ILIKE :search"
        else:
            where_clause = " WHERE client_code ILIKE :search OR location ILIKE :search OR mac_address ILIKE :search OR comment ILIKE :search"
        params['search'] = f"%{search}%"

    order_clause = " ORDER BY client_code, contract_number DESC, id DESC" if has_contract_number else " ORDER BY install_date DESC, id DESC"

    if page is None or per_page is None:
        installations = db.session.execute(
            text(f"SELECT * FROM genius.installations{where_clause}{order_clause}"),
            params,
        ).fetchall()
        return installations

    offset = (page - 1) * per_page
    params['limit'] = per_page
    params['offset'] = offset
    installations = db.session.execute(
        text(f"SELECT * FROM genius.installations{where_clause}{order_clause} LIMIT :limit OFFSET :offset"),
        params,
    ).fetchall()
    return installations


def get_installations_count(search: str | None = None):
    search = (search or '').strip()
    where_clause = ''
    params = {}
    has_contract_number = _has_contract_number_column()

    if search:
        if has_contract_number:
            where_clause = " WHERE client_code ILIKE :search OR location ILIKE :search OR mac_address ILIKE :search OR comment ILIKE :search OR CAST(contract_number AS TEXT) ILIKE :search"
        else:
            where_clause = " WHERE client_code ILIKE :search OR location ILIKE :search OR mac_address ILIKE :search OR comment ILIKE :search"
        params['search'] = f"%{search}%"

    total = db.session.execute(
        text(f"SELECT COUNT(*) FROM genius.installations{where_clause}"),
        params,
    ).scalar_one()
    return total



def get_latest_installation_by_client(client_code):
    has_contract_number = _has_contract_number_column()
    order_clause = "contract_number DESC, id DESC" if has_contract_number else "install_date DESC, id DESC"

    query = text(
        f"""
        SELECT *
        FROM genius.installations
        WHERE client_code = :client_code
        ORDER BY {order_clause}
        LIMIT 1
        """
    )

    installation = db.session.execute(
        query,
        {"client_code": client_code},
    ).first()
    return installation


def get_installation_media(installation_id):
    query = text(
        """
        SELECT *
        FROM genius.installation_media
        WHERE installation_id = :installation_id
        ORDER BY id DESC
        """
    )

    media = db.session.execute(
        query,
        {"installation_id": installation_id},
    ).fetchall()
    return media


def create_installation(
    client_code,
    install_date,
    location,
    mac_address,
    comment,
):
    has_contract_number = _has_contract_number_column()

    if has_contract_number:
        query = text(
            """
            INSERT INTO genius.installations (
                client_code,
                contract_number,
                install_date,
                location,
                mac_address,
                comment
            ) VALUES (
                :client_code,
                (
                    SELECT COALESCE(MAX(i.contract_number), 0) + 1
                    FROM genius.installations i
                    WHERE i.client_code = :client_code
                ),
                :install_date,
                :location,
                :mac_address,
                :comment
            )
            RETURNING id
            """
        )
    else:
        query = text(
            """
            INSERT INTO genius.installations (
                client_code,
                install_date,
                location,
                mac_address,
                comment
            ) VALUES (
                :client_code,
                :install_date,
                :location,
                :mac_address,
                :comment
            )
            RETURNING id
            """
        )

    try:
        result = db.session.execute(
            query,
            {
                "client_code": client_code,
                "install_date": install_date,
                "location": location,
                "mac_address": mac_address,
                "comment": comment,
            },
        ).fetchone()
        db.session.commit()
        return result.id if result else None
    except SQLAlchemyError as error:
        db.session.rollback()
        if getattr(getattr(error, 'orig', None), 'pgcode', None) == '23505':
            # Unique violation: MAC duplicada global o contrato repetido por cliente.
            return "duplicate_client_mac"
        current_app.logger.exception("Error de base de datos al crear instalacion: %s", error)
        return None
    except Exception as error:
        db.session.rollback()
        current_app.logger.exception("Error inesperado al crear instalacion: %s", error)
        return None


def create_installation_media(
    installation_id,
    media_type,
    file_name,
    file_data,
    mime_type,
    file_size_bytes,
):
    query = text(
        """
        INSERT INTO genius.installation_media (
            installation_id,
            media_type,
            file_name,
            file_data,
            mime_type,
            file_size_bytes
        ) VALUES (
            :installation_id,
            :media_type,
            :file_name,
            :file_data,
            :mime_type,
            :file_size_bytes
        )
        """
    )

    try:
        db.session.execute(
            query,
            {
                "installation_id": installation_id,
                "media_type": media_type,
                "file_name": file_name,
                "file_data": file_data,
                "mime_type": mime_type,
                "file_size_bytes": file_size_bytes,
            },
        )
        db.session.commit()
        return True
    except SQLAlchemyError as error:
        db.session.rollback()
        current_app.logger.exception("Error de base de datos al crear multimedia de instalacion: %s", error)
        return False
    except Exception as error:
        db.session.rollback()
        current_app.logger.exception("Error inesperado al crear multimedia de instalacion: %s", error)
        return False


def update_installation(
    installation_id,
    client_code,
    install_date,
    location,
    mac_address,
    comment,
):
    query = text(
        """
        UPDATE genius.installations
        SET
            client_code = :client_code,
            install_date = :install_date,
            location = :location,
            mac_address = :mac_address,
            comment = :comment
        WHERE id = :installation_id
        """
    )

    try:
        result = db.session.execute(
            query,
            {
                "installation_id": installation_id,
                "client_code": client_code,
                "install_date": install_date,
                "location": location,
                "mac_address": mac_address,
                "comment": comment,
            },
        )
        db.session.commit()
        return result.rowcount > 0
    except SQLAlchemyError as error:
        db.session.rollback()
        if getattr(getattr(error, 'orig', None), 'pgcode', None) == '23505':
            return "duplicate_client_mac"
        current_app.logger.exception("Error de base de datos al actualizar instalacion: %s", error)
        return False
    except Exception as error:
        db.session.rollback()
        current_app.logger.exception("Error inesperado al actualizar instalacion: %s", error)
        return False


def get_installation(installation_id: int):
    return db.session.execute(
        text("SELECT * FROM genius.installations WHERE id = :installation_id"),
        {'installation_id': installation_id},
    ).first()


def upsert_installation_media(
    installation_id,
    media_type,
    file_name,
    file_data,
    mime_type,
    file_size_bytes,
):
    existing_query = text(
        """
        SELECT id
        FROM genius.installation_media
        WHERE installation_id = :installation_id
          AND media_type = :media_type
        ORDER BY id DESC
        LIMIT 1
        """
    )

    existing_row = db.session.execute(
        existing_query,
        {
            "installation_id": installation_id,
            "media_type": media_type,
        },
    ).first()

    if existing_row:
        update_query = text(
            """
            UPDATE genius.installation_media
            SET
                file_name = :file_name,
                file_data = :file_data,
                mime_type = :mime_type,
                file_size_bytes = :file_size_bytes,
                uploaded_at = NOW()
            WHERE id = :media_id
            """
        )

        try:
            db.session.execute(
                update_query,
                {
                    "media_id": existing_row.id,
                    "file_name": file_name,
                    "file_data": file_data,
                    "mime_type": mime_type,
                    "file_size_bytes": file_size_bytes,
                },
            )
            db.session.commit()
            return True
        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.exception("Error de base de datos al actualizar multimedia de instalacion: %s", error)
            return False
        except Exception as error:
            db.session.rollback()
            current_app.logger.exception("Error inesperado al actualizar multimedia de instalacion: %s", error)
            return False

    return create_installation_media(
        installation_id=installation_id,
        media_type=media_type,
        file_name=file_name,
        file_data=file_data,
        mime_type=mime_type,
        file_size_bytes=file_size_bytes,
    )


def delete_installation(installation_id, client_code):
    query = text(
        """
        DELETE FROM genius.installations
        WHERE id = :installation_id
          AND client_code = :client_code
        """
    )

    try:
        result = db.session.execute(
            query,
            {
                "installation_id": installation_id,
                "client_code": client_code,
            },
        )
        db.session.commit()
        return result.rowcount > 0
    except SQLAlchemyError as error:
        db.session.rollback()
        current_app.logger.exception("Error de base de datos al eliminar instalacion: %s", error)
        return False
    except Exception as error:
        db.session.rollback()
        current_app.logger.exception("Error inesperado al eliminar instalacion: %s", error)
        return False

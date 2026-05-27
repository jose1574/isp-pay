from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from flask import current_app

from flaskr import db


def get_latest_installation_by_client(client_code):
    query = text(
        """
        SELECT *
        FROM genius.installations
        WHERE client_code = :client_code
        ORDER BY install_date DESC, id DESC
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
            # Unique violation: misma MAC para el mismo cliente.
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

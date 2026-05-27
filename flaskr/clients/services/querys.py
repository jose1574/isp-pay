from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from flask import current_app

from flaskr import db

def get_clients():
    clients = db.session.execute(text("SELECT * FROM clients")).fetchall()
    return clients

def get_client(code: str ):
    client = db.session.execute(text('SELECT * FROM clients WHERE code= :code'), {"code": code}).first()
    return client

def get_area_sales():
    area_sales =  db.session.execute(text("SELECT * FROM area_sales")).fetchall()
    return area_sales

def create_client(
        code, 
        description,
        address,
        email,
        phone,
        area_sales,
        credit_days
):
    
    query = """ 
        SELECT set_clients(
            :code,               -- p_code (Código único del cliente)
            :description, -- p_description (Nombre o Razón Social)
            :address, -- p_address
            :code,          -- p_client_id (RIF / Cédula)
            :email,    -- p_email
            :phone,          -- p_phone
            '',            -- p_contact
            '00',             -- p_country
            '00',                  -- p_province
            '00',          -- p_city
            '00',              -- p_town
            :area_sales,           -- p_area_sales
            '00',            -- p_seller
            '00',          -- p_client_group
            :credit_days,                       -- p_credit_days (Los 5 días de prórroga/crédito que mencionabas)
            0,                 -- p_credit_limit
            0,                    -- p_discount
            '01',              -- p_client_type
            0,                       -- p_sale_price (Lista de precios 1, 2, etc.)
            '01',                -- p_status
            '1',                       -- p_name_fiscal
            'f',                   -- p_generic_client
            'C',     -- p_client_classification
            '00',             -- p_cond_property_type
            '00',                -- p_cond_floor
            '0',                    -- p_cond_aliquot
            '0',                    -- p_cond_surface
            'f',                   -- p_allow_expired_balance
            'f',                    -- p_retention_tax_agent (Agente de retención IVA)
            'f',                   -- p_retention_municipal_agent
            'f',                   -- p_retention_islr_agent
            'I'                      -- p_action (¡CRÍTICO! 'I' para insertar/guardar)
        );  
    """

    try:
        result = db.session.execute(text(query), {
            'code': code,
            'description': description,
            'address': address,
            'email': email,
            'phone': phone,
            'area_sales': area_sales,
            'credit_days': credit_days
        }).fetchone()

        if result is not None:
            db.session.commit()

        return result

    except SQLAlchemyError as error:
        db.session.rollback()
        current_app.logger.exception("Error de base de datos al crear cliente: %s", error)
        return None

    except Exception as error:
        db.session.rollback()
        current_app.logger.exception("Error inesperado al crear cliente: %s", error)
        return None

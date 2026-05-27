from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from flask import current_app

from flaskr import db


def get_routes():
	return db.session.execute(
		text(
			"""
			SELECT *
			FROM genius.routes
			ORDER BY correlative DESC
			"""
		)
	).fetchall()


def get_route(correlative: int):
	return db.session.execute(
		text(
			"""
			SELECT *
			FROM genius.routes
			WHERE correlative = :correlative
			LIMIT 1
			"""
		),
		{'correlative': correlative},
	).first()


def create_route(ip_address, mac_address, identity, description, api_port, is_active, username, password):
	query = text(
		"""
		INSERT INTO genius.routes (
			ip_address,
			mac_address,
			identity,
			description,
			api_port,
			is_active,
			username,
			password
		) VALUES (
			:ip_address,
			:mac_address,
			:identity,
			:description,
			:api_port,
			:is_active,
			:username,
			:password
		)
		RETURNING correlative
		"""
	)

	try:
		result = db.session.execute(
			query,
			{
				'ip_address': ip_address,
				'mac_address': mac_address,
				'identity': identity,
				'description': description,
				'api_port': api_port,
				'is_active': is_active,
				'username': username,
				'password': password,
			},
		).fetchone()
		db.session.commit()
		return result.correlative if result else None
	except SQLAlchemyError as error:
		db.session.rollback()
		if getattr(getattr(error, 'orig', None), 'pgcode', None) == '23505':
			return 'duplicate_data'
		current_app.logger.exception('Error de base de datos al crear router: %s', error)
		return None
	except Exception as error:
		db.session.rollback()
		current_app.logger.exception('Error inesperado al crear router: %s', error)
		return None


def update_route(correlative, ip_address, mac_address, identity, description, api_port, is_active, username, password):
	query = text(
		"""
		UPDATE genius.routes
		SET
			ip_address = :ip_address,
			mac_address = :mac_address,
			identity = :identity,
			description = :description,
			api_port = :api_port,
			is_active = :is_active,
			username = :username,
			password = :password
		WHERE correlative = :correlative
		"""
	)

	try:
		result = db.session.execute(
			query,
			{
				'correlative': correlative,
				'ip_address': ip_address,
				'mac_address': mac_address,
				'identity': identity,
				'description': description,
				'api_port': api_port,
				'is_active': is_active,
				'username': username,
				'password': password,
			},
		)
		db.session.commit()
		return result.rowcount > 0
	except SQLAlchemyError as error:
		db.session.rollback()
		if getattr(getattr(error, 'orig', None), 'pgcode', None) == '23505':
			return 'duplicate_data'
		current_app.logger.exception('Error de base de datos al actualizar router: %s', error)
		return False
	except Exception as error:
		db.session.rollback()
		current_app.logger.exception('Error inesperado al actualizar router: %s', error)
		return False


def delete_route(correlative):
	query = text(
		"""
		DELETE FROM genius.routes
		WHERE correlative = :correlative
		"""
	)

	try:
		result = db.session.execute(query, {'correlative': correlative})
		db.session.commit()
		return result.rowcount > 0
	except SQLAlchemyError as error:
		db.session.rollback()
		current_app.logger.exception('Error de base de datos al eliminar router: %s', error)
		return False
	except Exception as error:
		db.session.rollback()
		current_app.logger.exception('Error inesperado al eliminar router: %s', error)
		return False


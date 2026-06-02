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


def get_area_sales_options():
	return db.session.execute(
		text(
			"""
			SELECT code, description
			FROM area_sales
			ORDER BY description
			"""
		)
	).fetchall()


def get_nodes():
	return db.session.execute(
		text(
			"""
			SELECT
				n.*,
				a.description AS area_sales_description,
				r.identity AS route_identity,
				r.ip_address AS route_ip
			FROM genius.nodo n
			JOIN genius.routes r ON r.correlative = n.route_id
			LEFT JOIN area_sales a ON a.code = n.area_sales_id
			ORDER BY n.correlative DESC
			"""
		)
	).fetchall()


def get_node(correlative: int):
	return db.session.execute(
		text(
			"""
			SELECT
				n.*,
				a.description AS area_sales_description,
				r.identity AS route_identity,
				r.ip_address AS route_ip
			FROM genius.nodo n
			JOIN genius.routes r ON r.correlative = n.route_id
			LEFT JOIN area_sales a ON a.code = n.area_sales_id
			WHERE n.correlative = :correlative
			LIMIT 1
			"""
		),
		{'correlative': correlative},
	).first()


def create_node(description, route_id, area_sales_id):
	query = text(
		"""
		INSERT INTO genius.nodo (
			description,
			route_id,
			area_sales_id
		) VALUES (
			:description,
			:route_id,
			:area_sales_id
		)
		RETURNING correlative
		"""
	)

	try:
		result = db.session.execute(
			query,
			{
				'description': description,
				'route_id': route_id,
				'area_sales_id': area_sales_id,
			},
		).fetchone()
		db.session.commit()
		return result.correlative if result else None
	except SQLAlchemyError as error:
		db.session.rollback()
		if getattr(getattr(error, 'orig', None), 'pgcode', None) == '23505':
			return 'duplicate_data'
		current_app.logger.exception('Error de base de datos al crear nodo: %s', error)
		return None
	except Exception as error:
		db.session.rollback()
		current_app.logger.exception('Error inesperado al crear nodo: %s', error)
		return None


def update_node(correlative, description, route_id, area_sales_id):
	query = text(
		"""
		UPDATE genius.nodo
		SET
			description = :description,
			route_id = :route_id,
			area_sales_id = :area_sales_id
		WHERE correlative = :correlative
		"""
	)

	try:
		result = db.session.execute(
			query,
			{
				'correlative': correlative,
				'description': description,
				'route_id': route_id,
				'area_sales_id': area_sales_id,
			},
		)
		db.session.commit()
		return result.rowcount > 0
	except SQLAlchemyError as error:
		db.session.rollback()
		if getattr(getattr(error, 'orig', None), 'pgcode', None) == '23505':
			return 'duplicate_data'
		current_app.logger.exception('Error de base de datos al actualizar nodo: %s', error)
		return False
	except Exception as error:
		db.session.rollback()
		current_app.logger.exception('Error inesperado al actualizar nodo: %s', error)
		return False


def delete_node(correlative):
	query = text(
		"""
		DELETE FROM genius.nodo
		WHERE correlative = :correlative
		"""
	)

	try:
		result = db.session.execute(query, {'correlative': correlative})
		db.session.commit()
		return result.rowcount > 0
	except SQLAlchemyError as error:
		db.session.rollback()
		current_app.logger.exception('Error de base de datos al eliminar nodo: %s', error)
		return False
	except Exception as error:
		db.session.rollback()
		current_app.logger.exception('Error inesperado al eliminar nodo: %s', error)
		return False


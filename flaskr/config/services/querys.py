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


def get_naps(page: int = 1, per_page: int = 10, search: str = ''):
	offset = (page - 1) * per_page
	search_value = f"%{search.strip()}%" if search else None
	return db.session.execute(
		text(
			"""
			SELECT
				n.correlative,
				n.description,
				n.location,
				n.nodo_id,
				n.created_at,
				nd.description AS nodo_description,
				COUNT(d.correlative) AS port_count
			FROM genius.nap n
			LEFT JOIN genius.nodo nd ON nd.correlative = n.nodo_id
			LEFT JOIN genius.nap_details d ON d.nap_id = n.correlative
			WHERE (
				:search_value IS NULL
				OR n.description ILIKE :search_value
				OR n.location ILIKE :search_value
				OR nd.description ILIKE :search_value
			)
			GROUP BY n.correlative, nd.description
			ORDER BY n.correlative DESC
			LIMIT :limit OFFSET :offset
			"""
		),
		{'limit': per_page, 'offset': offset, 'search_value': search_value},
	).fetchall()


def get_naps_count(search: str = ''):
	search_value = f"%{search.strip()}%" if search else None
	return db.session.execute(
		text(
			"""
			SELECT COUNT(*)
			FROM genius.nap n
			LEFT JOIN genius.nodo nd ON nd.correlative = n.nodo_id
			WHERE (
				:search_value IS NULL
				OR n.description ILIKE :search_value
				OR n.location ILIKE :search_value
				OR nd.description ILIKE :search_value
			)
			"""
		),
		{'search_value': search_value},
	).scalar_one()


def get_nap(correlative: int):
	return db.session.execute(
		text(
			"""
			SELECT
				n.correlative,
				n.description,
				n.location,
				n.nodo_id,
				n.created_at
			FROM genius.nap n
			WHERE n.correlative = :correlative
			LIMIT 1
			"""
		),
		{'correlative': correlative},
	).first()


def get_nap_ports(nap_id: int):
	return db.session.execute(
		text(
			"""
			SELECT
				d.correlative,
				d.nap_id,
				d.port_name,
				d.port_trunk,
				d.next_nap_id,
				d.in_use
			FROM genius.nap_details d
			WHERE d.nap_id = :nap_id
			ORDER BY d.correlative ASC
			"""
		),
		{'nap_id': nap_id},
	).fetchall()


def get_nap_options():
	return db.session.execute(
		text(
			"""
			SELECT correlative, description
			FROM genius.nap
			ORDER BY description
			"""
		)
	).fetchall()


def create_nap_with_ports(description, location, nodo_id, ports):
	insert_nap_query = text(
		"""
		INSERT INTO genius.nap (
			description,
			location,
			nodo_id
		) VALUES (
			:description,
			:location,
			:nodo_id
		)
		RETURNING correlative
		"""
	)

	insert_port_query = text(
		"""
		INSERT INTO genius.nap_details (
			nap_id,
			port_name,
			port_trunk,
			next_nap_id,
			in_use
		) VALUES (
			:nap_id,
			:port_name,
			:port_trunk,
			:next_nap_id,
			:in_use
		)
		"""
	)

	try:
		result = db.session.execute(
			insert_nap_query,
			{
				'description': description,
				'location': location,
				'nodo_id': nodo_id,
			},
		).fetchone()

		nap_id = result.correlative if result else None
		if not nap_id:
			db.session.rollback()
			return None

		for port in ports:
			db.session.execute(
				insert_port_query,
				{
					'nap_id': nap_id,
					'port_name': port['port_name'],
					'port_trunk': port['port_trunk'],
					'next_nap_id': port['next_nap_id'],
					'in_use': bool(port['port_trunk']),
				},
			)

		db.session.commit()
		return nap_id
	except SQLAlchemyError as error:
		db.session.rollback()
		pgcode = getattr(getattr(error, 'orig', None), 'pgcode', None)
		if pgcode == '23505':
			return 'duplicate_data'
		if pgcode == '23503':
			return 'invalid_reference'
		current_app.logger.exception('Error de base de datos al crear NAP: %s', error)
		return None
	except Exception as error:
		db.session.rollback()
		current_app.logger.exception('Error inesperado al crear NAP: %s', error)
		return None


def update_nap(correlative, description, location, nodo_id):
	query = text(
		"""
		UPDATE genius.nap
		SET
			description = :description,
			location = :location,
			nodo_id = :nodo_id
		WHERE correlative = :correlative
		"""
	)

	try:
		result = db.session.execute(
			query,
			{
				'correlative': correlative,
				'description': description,
				'location': location,
				'nodo_id': nodo_id,
			},
		)
		db.session.commit()
		return result.rowcount > 0
	except SQLAlchemyError as error:
		db.session.rollback()
		if getattr(getattr(error, 'orig', None), 'pgcode', None) == '23505':
			return 'duplicate_data'
		current_app.logger.exception('Error de base de datos al actualizar NAP: %s', error)
		return False
	except Exception as error:
		db.session.rollback()
		current_app.logger.exception('Error inesperado al actualizar NAP: %s', error)
		return False


def delete_nap(correlative):
	query = text(
		"""
		DELETE FROM genius.nap
		WHERE correlative = :correlative
		"""
	)

	try:
		result = db.session.execute(query, {'correlative': correlative})
		db.session.commit()
		return result.rowcount > 0
	except SQLAlchemyError as error:
		db.session.rollback()
		current_app.logger.exception('Error de base de datos al eliminar NAP: %s', error)
		return False
	except Exception as error:
		db.session.rollback()
		current_app.logger.exception('Error inesperado al eliminar NAP: %s', error)
		return False


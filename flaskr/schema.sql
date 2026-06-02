DO $$
BEGIN
	IF NOT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 'genius') THEN
		EXECUTE 'CREATE SCHEMA genius';
	END IF;
END
$$;

-- Tabla de planes de servicios
CREATE TABLE IF NOT EXISTS genius.plans (
	correlative BIGSERIAL PRIMARY KEY,
	code VARCHAR(30) NOT NULL,
	description VARCHAR(150) NOT NULL,
	comment TEXT,
	coin VARCHAR(30),
	price NUMERIC(12,2)
);

DO $$
BEGIN
	IF NOT EXISTS (
		SELECT 1
		FROM information_schema.columns
		WHERE table_schema = 'genius'
		  AND table_name = 'plans'
		  AND column_name = 'coin'
	) THEN
		EXECUTE 'ALTER TABLE genius.plans ADD COLUMN coin VARCHAR(30)';
	END IF;
END
$$;

DO $$
BEGIN
	IF NOT EXISTS (
		SELECT 1
		FROM information_schema.columns
		WHERE table_schema = 'genius'
		  AND table_name = 'plans'
		  AND column_name = 'price'
	) THEN
		EXECUTE 'ALTER TABLE genius.plans ADD COLUMN price NUMERIC(12,2)';
	END IF;
END
$$;

DO $$
BEGIN
	IF EXISTS (
		SELECT 1
		FROM information_schema.columns
		WHERE table_schema = 'public'
		  AND table_name = 'coin'
		  AND column_name = 'code'
	)
	AND NOT EXISTS (
		SELECT 1
		FROM pg_constraint con
		JOIN pg_class rel ON rel.oid = con.conrelid
		JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
		WHERE con.conname = 'fk_plans_coin'
		  AND rel.relname = 'plans'
		  AND nsp.nspname = 'genius'
	) THEN
		EXECUTE 'ALTER TABLE genius.plans ADD CONSTRAINT fk_plans_coin FOREIGN KEY (coin) REFERENCES public.coin(code) ON UPDATE CASCADE ON DELETE RESTRICT';
	END IF;
END
$$;

DO $$
BEGIN
	IF NOT EXISTS (
		SELECT 1
		FROM pg_class c
		JOIN pg_namespace n ON n.oid = c.relnamespace
		WHERE c.relkind = 'i'
		  AND c.relname = 'uq_plans_code'
		  AND n.nspname = 'genius'
	) THEN
		EXECUTE 'CREATE UNIQUE INDEX uq_plans_code ON genius.plans(code)';
	END IF;
END
$$;

DO $$
BEGIN
	IF NOT EXISTS (
		SELECT 1
		FROM pg_class c
		JOIN pg_namespace n ON n.oid = c.relnamespace
		WHERE c.relkind = 'i'
		  AND c.relname = 'idx_plans_coin'
		  AND n.nspname = 'genius'
	) THEN
		EXECUTE 'CREATE INDEX idx_plans_coin ON genius.plans(coin)';
	END IF;
END
$$;

-- Tabla de suscripciones de servicios
CREATE TABLE IF NOT EXISTS genius.subscription (
	correlative BIGSERIAL PRIMARY KEY,
	client_code VARCHAR(30) NOT NULL,
	installation BIGINT,
	plan_code VARCHAR(30) NOT NULL,
	status VARCHAR(50) NOT NULL,
	cutoff_day DATE,
	credit_day SMALLINT,
	price_applied NUMERIC(12,2),
	CONSTRAINT fk_subscription_client
		FOREIGN KEY (client_code)
		REFERENCES public.clients(code)
		ON UPDATE CASCADE
		ON DELETE RESTRICT,
	CONSTRAINT fk_subscription_plan
		FOREIGN KEY (plan_code)
		REFERENCES genius.plans(code)
		ON UPDATE CASCADE
		ON DELETE RESTRICT,
	CONSTRAINT chk_subscription_status
		CHECK (status IN ('activo', 'suspendido_por_falta_de_pago', 'suspendido_temporal', 'retirado')),
	CONSTRAINT chk_subscription_credit_day
		CHECK (credit_day IS NULL OR (credit_day BETWEEN 1 AND 31)),
	CONSTRAINT chk_subscription_price_applied
		CHECK (price_applied IS NULL OR price_applied >= 0)
);

DO $$
BEGIN
	IF EXISTS (
		SELECT 1
		FROM pg_constraint con
		JOIN pg_class rel ON rel.oid = con.conrelid
		JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
		WHERE con.conname = 'chk_subscription_cutoff_day'
		  AND rel.relname = 'subscription'
		  AND nsp.nspname = 'genius'
	) THEN
		EXECUTE 'ALTER TABLE genius.subscription DROP CONSTRAINT chk_subscription_cutoff_day';
	END IF;
END
$$;

DO $$
DECLARE
	v_data_type TEXT;
BEGIN
	SELECT c.data_type
	INTO v_data_type
	FROM information_schema.columns c
	WHERE c.table_schema = 'genius'
	  AND c.table_name = 'subscription'
	  AND c.column_name = 'cutoff_day';

	IF v_data_type IS NOT NULL AND v_data_type <> 'date' THEN
		EXECUTE 'ALTER TABLE genius.subscription RENAME COLUMN cutoff_day TO cutoff_day_legacy';
		EXECUTE 'ALTER TABLE genius.subscription ADD COLUMN cutoff_day DATE';
		EXECUTE 'UPDATE genius.subscription SET cutoff_day = to_date(lpad(cutoff_day_legacy::text, 2, ''0'') || ''-'' || to_char(CURRENT_DATE, ''MM-YYYY''), ''DD-MM-YYYY'') WHERE cutoff_day_legacy IS NOT NULL';
		EXECUTE 'ALTER TABLE genius.subscription DROP COLUMN cutoff_day_legacy';
	END IF;
END
$$;

DO $$
BEGIN
	IF NOT EXISTS (
		SELECT 1
		FROM pg_class c
		JOIN pg_namespace n ON n.oid = c.relnamespace
		WHERE c.relkind = 'i'
		  AND c.relname = 'idx_subscription_client_code'
		  AND n.nspname = 'genius'
	) THEN
		EXECUTE 'CREATE INDEX idx_subscription_client_code ON genius.subscription(client_code)';
	END IF;
END
$$;

DO $$
BEGIN
	IF NOT EXISTS (
		SELECT 1
		FROM pg_class c
		JOIN pg_namespace n ON n.oid = c.relnamespace
		WHERE c.relkind = 'i'
		  AND c.relname = 'idx_subscription_installation'
		  AND n.nspname = 'genius'
	) THEN
		EXECUTE 'CREATE INDEX idx_subscription_installation ON genius.subscription(installation)';
	END IF;
END
$$;

DO $$
BEGIN
	IF NOT EXISTS (
		SELECT 1
		FROM pg_class c
		JOIN pg_namespace n ON n.oid = c.relnamespace
		WHERE c.relkind = 'i'
		  AND c.relname = 'idx_subscription_plan_code'
		  AND n.nspname = 'genius'
	) THEN
		EXECUTE 'CREATE INDEX idx_subscription_plan_code ON genius.subscription(plan_code)';
	END IF;
END
$$;

DO $$
BEGIN
	IF NOT EXISTS (
		SELECT 1
		FROM pg_class c
		JOIN pg_namespace n ON n.oid = c.relnamespace
		WHERE c.relkind = 'i'
		  AND c.relname = 'uq_subscription_installation'
		  AND n.nspname = 'genius'
	) THEN
		EXECUTE 'CREATE UNIQUE INDEX uq_subscription_installation ON genius.subscription(installation) WHERE installation IS NOT NULL';
	END IF;
END
$$;

DO $$
BEGIN
	IF NOT EXISTS (
		SELECT 1
		FROM pg_class c
		JOIN pg_namespace n ON n.oid = c.relnamespace
		WHERE c.relkind = 'i'
		  AND c.relname = 'idx_subscription_status'
		  AND n.nspname = 'genius'
	) THEN
		EXECUTE 'CREATE INDEX idx_subscription_status ON genius.subscription(status)';
	END IF;
END
$$;

-- Tabla principal de instalaciones
CREATE TABLE IF NOT EXISTS genius.installations (
	id BIGSERIAL PRIMARY KEY,
	client_code VARCHAR(30) NOT NULL,
	no_installation VARCHAR(40),
	install_date DATE NOT NULL,
	location VARCHAR(255) NOT NULL,
	route_id BIGINT,
	mac_address VARCHAR(50) NOT NULL,
	comment TEXT,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
	CONSTRAINT fk_installations_client
		FOREIGN KEY (client_code)
		REFERENCES public.clients(code)
		ON UPDATE CASCADE
		ON DELETE RESTRICT
);

DO $$
BEGIN
	IF NOT EXISTS (
		SELECT 1
		FROM information_schema.columns
		WHERE table_schema = 'genius'
		  AND table_name = 'installations'
		  AND column_name = 'route_id'
	) THEN
		EXECUTE 'ALTER TABLE genius.installations ADD COLUMN route_id BIGINT';
	END IF;
END
$$;

DO $$
BEGIN
	IF EXISTS (
		SELECT 1
		FROM information_schema.tables
		WHERE table_schema = 'genius'
		  AND table_name = 'routes'
	)
	AND NOT EXISTS (
		SELECT 1
		FROM pg_constraint con
		JOIN pg_class rel ON rel.oid = con.conrelid
		JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
		WHERE con.conname = 'fk_installations_route'
		  AND rel.relname = 'installations'
		  AND nsp.nspname = 'genius'
	) THEN
		EXECUTE 'ALTER TABLE genius.installations ADD CONSTRAINT fk_installations_route FOREIGN KEY (route_id) REFERENCES genius.routes(correlative) ON UPDATE CASCADE ON DELETE SET NULL';
	END IF;
END
$$;

DO $$
BEGIN
	IF NOT EXISTS (
		SELECT 1
		FROM pg_class c
		JOIN pg_namespace n ON n.oid = c.relnamespace
		WHERE c.relkind = 'i'
		  AND c.relname = 'idx_installations_route_id'
		  AND n.nspname = 'genius'
	) THEN
		EXECUTE 'CREATE INDEX idx_installations_route_id ON genius.installations(route_id)';
	END IF;
END
$$;

DO $$
BEGIN
	IF NOT EXISTS (
		SELECT 1
		FROM information_schema.columns
		WHERE table_schema = 'genius'
		  AND table_name = 'installations'
		  AND column_name = 'nap_detail_id'
	) THEN
		EXECUTE 'ALTER TABLE genius.installations ADD COLUMN nap_detail_id BIGINT';
	END IF;
END
$$;

DO $$
BEGIN
	IF EXISTS (
		SELECT 1
		FROM information_schema.tables
		WHERE table_schema = 'genius'
		  AND table_name = 'nap_details'
	)
	AND EXISTS (
		SELECT 1
		FROM information_schema.columns
		WHERE table_schema = 'genius'
		  AND table_name = 'installations'
		  AND column_name = 'nap_detail_id'
	)
	AND NOT EXISTS (
		SELECT 1
		FROM pg_constraint con
		JOIN pg_class rel ON rel.oid = con.conrelid
		JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
		WHERE con.conname = 'fk_installations_nap_detail'
		  AND rel.relname = 'installations'
		  AND nsp.nspname = 'genius'
	) THEN
		EXECUTE 'ALTER TABLE genius.installations ADD CONSTRAINT fk_installations_nap_detail FOREIGN KEY (nap_detail_id) REFERENCES genius.nap_details(correlative) ON UPDATE CASCADE ON DELETE SET NULL';
	END IF;
END
$$;

DO $$
BEGIN
	IF NOT EXISTS (
		SELECT 1
		FROM pg_class c
		JOIN pg_namespace n ON n.oid = c.relnamespace
		WHERE c.relkind = 'i'
		  AND c.relname = 'uq_installations_nap_detail_id'
		  AND n.nspname = 'genius'
	) THEN
		EXECUTE 'CREATE UNIQUE INDEX uq_installations_nap_detail_id ON genius.installations(nap_detail_id) WHERE nap_detail_id IS NOT NULL';
	END IF;
END
$$;

DO $$
BEGIN
	IF NOT EXISTS (
		SELECT 1
		FROM information_schema.columns
		WHERE table_schema = 'genius'
		  AND table_name = 'installations'
		  AND column_name = 'no_installation'
	) THEN
		EXECUTE 'ALTER TABLE genius.installations ADD COLUMN no_installation VARCHAR(40)';
	END IF;
END
$$;

DO $$
BEGIN
	IF EXISTS (
		SELECT 1
		FROM information_schema.columns
		WHERE table_schema = 'genius'
		  AND table_name = 'installations'
		  AND column_name = 'contract_number'
	) THEN
		EXECUTE 'UPDATE genius.installations SET no_installation = ''contrato-'' || contract_number::text WHERE no_installation IS NULL AND contract_number IS NOT NULL';
	END IF;
END
$$;

WITH ordered_installations AS (
	SELECT
		id,
		ROW_NUMBER() OVER (
			PARTITION BY client_code
			ORDER BY install_date, id
		) AS rn
	FROM genius.installations
)
UPDATE genius.installations i
SET no_installation = 'contrato-' || oi.rn::text
FROM ordered_installations oi
WHERE i.id = oi.id
	AND i.no_installation IS NULL;

DO $$
BEGIN
	IF EXISTS (
		SELECT 1
		FROM information_schema.columns
		WHERE table_schema = 'genius'
		  AND table_name = 'installations'
		  AND column_name = 'no_installation'
	)
	AND NOT EXISTS (
		SELECT 1
		FROM genius.installations
		WHERE no_installation IS NULL
	) THEN
		EXECUTE 'ALTER TABLE genius.installations ALTER COLUMN no_installation SET NOT NULL';
	END IF;
END
$$;

DO $$
BEGIN
	IF EXISTS (
		SELECT 1
		FROM pg_class c
		JOIN pg_namespace n ON n.oid = c.relnamespace
		WHERE c.relkind = 'i'
		  AND c.relname = 'uq_installations_client_contract'
		  AND n.nspname = 'genius'
	) THEN
		EXECUTE 'DROP INDEX genius.uq_installations_client_contract';
	END IF;
END
$$;

DO $$
BEGIN
	IF NOT EXISTS (
		SELECT 1
		FROM pg_class c
		JOIN pg_namespace n ON n.oid = c.relnamespace
		WHERE c.relkind = 'i'
		  AND c.relname = 'uq_installations_client_contract'
		  AND n.nspname = 'genius'
	) THEN
		EXECUTE 'CREATE UNIQUE INDEX uq_installations_client_contract ON genius.installations(client_code, no_installation)';
	END IF;
END
$$;

DO $$
BEGIN
	IF NOT EXISTS (
		SELECT 1
		FROM pg_class c
		JOIN pg_namespace n ON n.oid = c.relnamespace
		WHERE c.relkind = 'i'
		  AND c.relname = 'idx_installations_client_code'
		  AND n.nspname = 'genius'
	) THEN
		EXECUTE 'CREATE INDEX idx_installations_client_code ON genius.installations(client_code)';
	END IF;
END
$$;

DO $$
BEGIN
	IF NOT EXISTS (
		SELECT 1
		FROM pg_class c
		JOIN pg_namespace n ON n.oid = c.relnamespace
		WHERE c.relkind = 'i'
		  AND c.relname = 'idx_installations_install_date'
		  AND n.nspname = 'genius'
	) THEN
		EXECUTE 'CREATE INDEX idx_installations_install_date ON genius.installations(install_date)';
	END IF;
END
$$;

DO $$
BEGIN
	IF NOT EXISTS (
		SELECT 1
		FROM pg_class c
		JOIN pg_namespace n ON n.oid = c.relnamespace
		WHERE c.relkind = 'i'
		  AND c.relname = 'idx_installations_mac_address'
		  AND n.nspname = 'genius'
	) THEN
		EXECUTE 'CREATE INDEX idx_installations_mac_address ON genius.installations(mac_address)';
	END IF;
END
$$;

DO $$
BEGIN
	IF EXISTS (
		SELECT 1
		FROM information_schema.tables
		WHERE table_schema = 'genius'
		  AND table_name = 'installations'
	)
	AND EXISTS (
		SELECT 1
		FROM information_schema.tables
		WHERE table_schema = 'genius'
		  AND table_name = 'subscription'
	)
	AND NOT EXISTS (
		SELECT 1
		FROM pg_constraint con
		JOIN pg_class rel ON rel.oid = con.conrelid
		JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
		WHERE con.conname = 'fk_subscription_installation'
		  AND rel.relname = 'subscription'
		  AND nsp.nspname = 'genius'
	) THEN
		EXECUTE 'ALTER TABLE genius.subscription ADD CONSTRAINT fk_subscription_installation FOREIGN KEY (installation) REFERENCES genius.installations(id) ON UPDATE CASCADE ON DELETE SET NULL';
	END IF;
END
$$;

-- Evita que la misma MAC se registre para cualquier cliente.
DO $$
BEGIN
	IF EXISTS (
		SELECT 1
		FROM pg_class c
		JOIN pg_namespace n ON n.oid = c.relnamespace
		WHERE c.relkind = 'i'
		  AND c.relname = 'uq_installations_client_mac_normalized'
		  AND n.nspname = 'genius'
	) THEN
		EXECUTE 'DROP INDEX genius.uq_installations_client_mac_normalized';
	END IF;
END
$$;

DO $$
BEGIN
	IF NOT EXISTS (
		SELECT 1
		FROM pg_class c
		JOIN pg_namespace n ON n.oid = c.relnamespace
		WHERE c.relkind = 'i'
		  AND c.relname = 'uq_installations_mac_normalized'
		  AND n.nspname = 'genius'
	) THEN
		EXECUTE 'CREATE UNIQUE INDEX uq_installations_mac_normalized ON genius.installations (regexp_replace(lower(mac_address), ''[^0-9a-f]'', '''', ''g''))';
	END IF;
END
$$;


-- Tabla para contenido multimedia de cada instalacion
CREATE TABLE IF NOT EXISTS genius.installation_media (
	id BIGSERIAL PRIMARY KEY,
	installation_id BIGINT NOT NULL,
	media_type VARCHAR(40) NOT NULL,
	file_name VARCHAR(255) NOT NULL,
	file_data BYTEA NOT NULL,
	mime_type VARCHAR(120),
	file_size_bytes BIGINT,
	uploaded_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
	CONSTRAINT fk_installation_media_installation
		FOREIGN KEY (installation_id)
		REFERENCES genius.installations(id)
		ON UPDATE CASCADE
		ON DELETE CASCADE,
	CONSTRAINT chk_installation_media_type
		CHECK (media_type IN ('image_label_onu', 'image_installation', 'other'))
);

DO $$
BEGIN
	IF NOT EXISTS (
		SELECT 1
		FROM pg_class c
		JOIN pg_namespace n ON n.oid = c.relnamespace
		WHERE c.relkind = 'i'
		  AND c.relname = 'idx_installation_media_installation_id'
		  AND n.nspname = 'genius'
	) THEN
		EXECUTE 'CREATE INDEX idx_installation_media_installation_id ON genius.installation_media(installation_id)';
	END IF;
END
$$;

DO $$
BEGIN
	IF NOT EXISTS (
		SELECT 1
		FROM pg_class c
		JOIN pg_namespace n ON n.oid = c.relnamespace
		WHERE c.relkind = 'i'
		  AND c.relname = 'idx_installation_media_type'
		  AND n.nspname = 'genius'
	) THEN
		EXECUTE 'CREATE INDEX idx_installation_media_type ON genius.installation_media(media_type)';
	END IF;
END
$$;


-- Funcion y triggers para mantener updated_at automaticamente
CREATE OR REPLACE FUNCTION genius.set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
	NEW.updated_at = NOW();
	RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
BEGIN
	IF EXISTS (
		SELECT 1
		FROM pg_trigger t
		JOIN pg_class c ON c.oid = t.tgrelid
		JOIN pg_namespace n ON n.oid = c.relnamespace
		WHERE t.tgname = 'trg_set_updated_at_installations'
		  AND c.relname = 'installations'
		  AND n.nspname = 'genius'
	) THEN
		EXECUTE 'DROP TRIGGER trg_set_updated_at_installations ON genius.installations';
	END IF;
END
$$;

CREATE TRIGGER trg_set_updated_at_installations
BEFORE UPDATE ON genius.installations
FOR EACH ROW
EXECUTE PROCEDURE genius.set_updated_at();


-- Historial experimental de asignacion y liberacion de puertos NAP
CREATE TABLE IF NOT EXISTS genius.nap_port_history (
	correlative BIGSERIAL PRIMARY KEY,
	nap_detail_id BIGINT NOT NULL,
	installation_id BIGINT,
	event_type VARCHAR(30) NOT NULL,
	previous_in_use BOOLEAN,
	new_in_use BOOLEAN NOT NULL,
	notes TEXT,
	event_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
	CONSTRAINT fk_nap_port_history_installation
		FOREIGN KEY (installation_id)
		REFERENCES genius.installations(id)
		ON UPDATE CASCADE
		ON DELETE SET NULL,
	CONSTRAINT chk_nap_port_history_event_type
		CHECK (event_type IN ('asignacion', 'liberacion', 'reasignacion'))
);

DO $$
BEGIN
	IF NOT EXISTS (
		SELECT 1
		FROM pg_class c
		JOIN pg_namespace n ON n.oid = c.relnamespace
		WHERE c.relkind = 'i'
		  AND c.relname = 'idx_nap_port_history_nap_detail_id'
		  AND n.nspname = 'genius'
	) THEN
		EXECUTE 'CREATE INDEX idx_nap_port_history_nap_detail_id ON genius.nap_port_history(nap_detail_id)';
	END IF;
END
$$;

DO $$
BEGIN
	IF NOT EXISTS (
		SELECT 1
		FROM pg_class c
		JOIN pg_namespace n ON n.oid = c.relnamespace
		WHERE c.relkind = 'i'
		  AND c.relname = 'idx_nap_port_history_installation_id'
		  AND n.nspname = 'genius'
	) THEN
		EXECUTE 'CREATE INDEX idx_nap_port_history_installation_id ON genius.nap_port_history(installation_id)';
	END IF;
END
$$;

DO $$
BEGIN
	IF NOT EXISTS (
		SELECT 1
		FROM pg_class c
		JOIN pg_namespace n ON n.oid = c.relnamespace
		WHERE c.relkind = 'i'
		  AND c.relname = 'idx_nap_port_history_event_at'
		  AND n.nspname = 'genius'
	) THEN
		EXECUTE 'CREATE INDEX idx_nap_port_history_event_at ON genius.nap_port_history(event_at)';
	END IF;
END
$$;

DO $$
BEGIN
	IF EXISTS (
		SELECT 1
		FROM pg_trigger t
		JOIN pg_class c ON c.oid = t.tgrelid
		JOIN pg_namespace n ON n.oid = c.relnamespace
		WHERE t.tgname = 'trg_set_updated_at_installation_media'
		  AND c.relname = 'installation_media'
		  AND n.nspname = 'genius'
	) THEN
		EXECUTE 'DROP TRIGGER trg_set_updated_at_installation_media ON genius.installation_media';
	END IF;
END
$$;

CREATE TRIGGER trg_set_updated_at_installation_media
BEFORE UPDATE ON genius.installation_media
FOR EACH ROW
EXECUTE PROCEDURE genius.set_updated_at();


-- Tabla de routers para gestion de conexiones Mikrotik
CREATE TABLE IF NOT EXISTS genius.routes (
	correlative BIGSERIAL PRIMARY KEY,
	ip_address VARCHAR(64) NOT NULL,
	mac_address VARCHAR(50),
	identity VARCHAR(150),
	description TEXT,
	api_port INTEGER NOT NULL DEFAULT 8728,
	is_active BOOLEAN NOT NULL DEFAULT TRUE,
	username VARCHAR(120) NOT NULL,
	password VARCHAR(255) NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

DO $$
BEGIN
	IF NOT EXISTS (
		SELECT 1
		FROM information_schema.columns
		WHERE table_schema = 'genius'
		  AND table_name = 'routes'
		  AND column_name = 'api_port'
	) THEN
		EXECUTE 'ALTER TABLE genius.routes ADD COLUMN api_port INTEGER';
	END IF;
END
$$;

DO $$
BEGIN
	IF EXISTS (
		SELECT 1
		FROM information_schema.columns
		WHERE table_schema = 'genius'
		  AND table_name = 'routes'
		  AND column_name = 'api_port'
	) THEN
		EXECUTE 'UPDATE genius.routes SET api_port = 8728 WHERE api_port IS NULL';
		EXECUTE 'ALTER TABLE genius.routes ALTER COLUMN api_port SET DEFAULT 8728';
	END IF;
END
$$;

DO $$
BEGIN
	IF EXISTS (
		SELECT 1
		FROM information_schema.columns
		WHERE table_schema = 'genius'
		  AND table_name = 'routes'
		  AND column_name = 'api_port'
	)
	AND NOT EXISTS (
		SELECT 1
		FROM genius.routes
		WHERE api_port IS NULL
	) THEN
		EXECUTE 'ALTER TABLE genius.routes ALTER COLUMN api_port SET NOT NULL';
	END IF;
END
$$;

DO $$
BEGIN
	IF NOT EXISTS (
		SELECT 1
		FROM pg_constraint con
		JOIN pg_class rel ON rel.oid = con.conrelid
		JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
		WHERE con.conname = 'chk_routes_api_port'
		  AND rel.relname = 'routes'
		  AND nsp.nspname = 'genius'
	) THEN
		EXECUTE 'ALTER TABLE genius.routes ADD CONSTRAINT chk_routes_api_port CHECK (api_port BETWEEN 1 AND 65535)';
	END IF;
END
$$;

DO $$
BEGIN
	IF NOT EXISTS (
		SELECT 1
		FROM information_schema.columns
		WHERE table_schema = 'genius'
		  AND table_name = 'routes'
		  AND column_name = 'is_active'
	) THEN
		EXECUTE 'ALTER TABLE genius.routes ADD COLUMN is_active BOOLEAN';
	END IF;
END
$$;

DO $$
BEGIN
	IF EXISTS (
		SELECT 1
		FROM information_schema.columns
		WHERE table_schema = 'genius'
		  AND table_name = 'routes'
		  AND column_name = 'is_active'
	) THEN
		EXECUTE 'UPDATE genius.routes SET is_active = TRUE WHERE is_active IS NULL';
		EXECUTE 'ALTER TABLE genius.routes ALTER COLUMN is_active SET DEFAULT TRUE';
	END IF;
END
$$;

DO $$
BEGIN
	IF EXISTS (
		SELECT 1
		FROM information_schema.columns
		WHERE table_schema = 'genius'
		  AND table_name = 'routes'
		  AND column_name = 'is_active'
	)
	AND NOT EXISTS (
		SELECT 1
		FROM genius.routes
		WHERE is_active IS NULL
	) THEN
		EXECUTE 'ALTER TABLE genius.routes ALTER COLUMN is_active SET NOT NULL';
	END IF;
END
$$;

DO $$
BEGIN
	IF NOT EXISTS (
		SELECT 1
		FROM pg_class c
		JOIN pg_namespace n ON n.oid = c.relnamespace
		WHERE c.relkind = 'i'
		  AND c.relname = 'uq_routes_ip_address'
		  AND n.nspname = 'genius'
	) THEN
		EXECUTE 'CREATE UNIQUE INDEX uq_routes_ip_address ON genius.routes(ip_address)';
	END IF;
END
$$;

DO $$
BEGIN
	IF NOT EXISTS (
		SELECT 1
		FROM pg_class c
		JOIN pg_namespace n ON n.oid = c.relnamespace
		WHERE c.relkind = 'i'
		  AND c.relname = 'uq_routes_mac_normalized'
		  AND n.nspname = 'genius'
	) THEN
		EXECUTE 'CREATE UNIQUE INDEX uq_routes_mac_normalized ON genius.routes (regexp_replace(lower(mac_address), ''[^0-9a-f]'', '''', ''g'')) WHERE mac_address IS NOT NULL';
	END IF;
END
$$;

DO $$
BEGIN
	IF NOT EXISTS (
		SELECT 1
		FROM pg_class c
		JOIN pg_namespace n ON n.oid = c.relnamespace
		WHERE c.relkind = 'i'
		  AND c.relname = 'idx_routes_identity'
		  AND n.nspname = 'genius'
	) THEN
		EXECUTE 'CREATE INDEX idx_routes_identity ON genius.routes(identity)';
	END IF;
END
$$;

DO $$
BEGIN
	IF NOT EXISTS (
		SELECT 1
		FROM pg_class c
		JOIN pg_namespace n ON n.oid = c.relnamespace
		WHERE c.relkind = 'i'
		  AND c.relname = 'idx_routes_is_active'
		  AND n.nspname = 'genius'
	) THEN
		EXECUTE 'CREATE INDEX idx_routes_is_active ON genius.routes(is_active)';
	END IF;
END
$$;

DO $$
BEGIN
	IF EXISTS (
		SELECT 1
		FROM pg_trigger t
		JOIN pg_class c ON c.oid = t.tgrelid
		JOIN pg_namespace n ON n.oid = c.relnamespace
		WHERE t.tgname = 'trg_set_updated_at_routes'
		  AND c.relname = 'routes'
		  AND n.nspname = 'genius'
	) THEN
		EXECUTE 'DROP TRIGGER trg_set_updated_at_routes ON genius.routes';
	END IF;
END
$$;

CREATE TRIGGER trg_set_updated_at_routes
BEFORE UPDATE ON genius.routes
FOR EACH ROW
EXECUTE PROCEDURE genius.set_updated_at();


-- Tabla principal de nodos de red
CREATE TABLE IF NOT EXISTS genius.nodo (
	correlative BIGSERIAL PRIMARY KEY,
	description VARCHAR(150) NOT NULL,
	area_sales_id VARCHAR(30)
);

DO $$
BEGIN
	IF EXISTS (
		SELECT 1
		FROM information_schema.tables
		WHERE table_schema = 'public'
		  AND table_name = 'area_sales'
	)
	AND EXISTS (
		SELECT 1
		FROM information_schema.columns
		WHERE table_schema = 'public'
		  AND table_name = 'area_sales'
		  AND column_name = 'code'
	)
	AND NOT EXISTS (
		SELECT 1
		FROM pg_constraint con
		JOIN pg_class rel ON rel.oid = con.conrelid
		JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
		WHERE con.conname = 'fk_nodo_area_sales'
		  AND rel.relname = 'nodo'
		  AND nsp.nspname = 'genius'
	) THEN
		EXECUTE 'ALTER TABLE genius.nodo ADD CONSTRAINT fk_nodo_area_sales FOREIGN KEY (area_sales_id) REFERENCES public.area_sales(code) ON UPDATE CASCADE ON DELETE SET NULL';
	END IF;
END
$$;

DO $$
BEGIN
	IF NOT EXISTS (
		SELECT 1
		FROM pg_class c
		JOIN pg_namespace n ON n.oid = c.relnamespace
		WHERE c.relkind = 'i'
		  AND c.relname = 'idx_nodo_area_sales_id'
		  AND n.nspname = 'genius'
	) THEN
		EXECUTE 'CREATE INDEX idx_nodo_area_sales_id ON genius.nodo(area_sales_id)';
	END IF;
END
$$;

DO $$
BEGIN
	IF NOT EXISTS (
		SELECT 1
		FROM pg_class c
		JOIN pg_namespace n ON n.oid = c.relnamespace
		WHERE c.relkind = 'i'
		  AND c.relname = 'idx_nodo_description'
		  AND n.nspname = 'genius'
	) THEN
		EXECUTE 'CREATE INDEX idx_nodo_description ON genius.nodo(description)';
	END IF;
END
$$;


-- Tabla principal de cajas NAP
CREATE TABLE IF NOT EXISTS genius.nap (
	correlative BIGSERIAL PRIMARY KEY,
	nodo_id BIGINT,
	description VARCHAR(150) NOT NULL,
	location TEXT NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
	CONSTRAINT fk_nap_nodo
		FOREIGN KEY (nodo_id)
		REFERENCES genius.nodo(correlative)
		ON UPDATE CASCADE
		ON DELETE SET NULL
);

DO $$
BEGIN
	IF NOT EXISTS (
		SELECT 1
		FROM pg_class c
		JOIN pg_namespace n ON n.oid = c.relnamespace
		WHERE c.relkind = 'i'
		  AND c.relname = 'idx_nap_description'
		  AND n.nspname = 'genius'
	) THEN
		EXECUTE 'CREATE INDEX idx_nap_description ON genius.nap(description)';
	END IF;
END
$$;

DO $$
BEGIN
	IF NOT EXISTS (
		SELECT 1
		FROM information_schema.columns
		WHERE table_schema = 'genius'
		  AND table_name = 'nap'
		  AND column_name = 'nodo_id'
	) THEN
		EXECUTE 'ALTER TABLE genius.nap ADD COLUMN nodo_id BIGINT';
	END IF;
END
$$;

DO $$
BEGIN
	IF EXISTS (
		SELECT 1
		FROM information_schema.columns
		WHERE table_schema = 'genius'
		  AND table_name = 'nap'
		  AND column_name = 'nodo_id'
	)
	AND NOT EXISTS (
		SELECT 1
		FROM pg_constraint con
		JOIN pg_class rel ON rel.oid = con.conrelid
		JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
		WHERE con.conname = 'fk_nap_nodo'
		  AND rel.relname = 'nap'
		  AND nsp.nspname = 'genius'
	) THEN
		EXECUTE 'ALTER TABLE genius.nap ADD CONSTRAINT fk_nap_nodo FOREIGN KEY (nodo_id) REFERENCES genius.nodo(correlative) ON UPDATE CASCADE ON DELETE SET NULL';
	END IF;
END
$$;

DO $$
BEGIN
	IF NOT EXISTS (
		SELECT 1
		FROM pg_class c
		JOIN pg_namespace n ON n.oid = c.relnamespace
		WHERE c.relkind = 'i'
		  AND c.relname = 'idx_nap_nodo_id'
		  AND n.nspname = 'genius'
	) THEN
		EXECUTE 'CREATE INDEX idx_nap_nodo_id ON genius.nap(nodo_id)';
	END IF;
END
$$;

DO $$
BEGIN
	IF NOT EXISTS (
		SELECT 1
		FROM information_schema.columns
		WHERE table_schema = 'genius'
		  AND table_name = 'nap'
		  AND column_name = 'created_at'
	) THEN
		EXECUTE 'ALTER TABLE genius.nap ADD COLUMN created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()';
		EXECUTE 'UPDATE genius.nap SET created_at = NOW() WHERE created_at IS NULL';
	END IF;
END
$$;


-- Tabla de puertos y asignaciones de cada NAP
CREATE TABLE IF NOT EXISTS genius.nap_details (
	correlative BIGSERIAL PRIMARY KEY,
	nap_id BIGINT NOT NULL,
	port_name VARCHAR(80) NOT NULL,
	in_use BOOLEAN NOT NULL DEFAULT FALSE,
	port_trunk BOOLEAN NOT NULL DEFAULT FALSE,
	next_nap_id BIGINT,
	CONSTRAINT fk_nap_details_nap
		FOREIGN KEY (nap_id)
		REFERENCES genius.nap(correlative)
		ON UPDATE CASCADE
		ON DELETE CASCADE,
	CONSTRAINT fk_nap_details_next_nap
		FOREIGN KEY (next_nap_id)
		REFERENCES genius.nap(correlative)
		ON UPDATE CASCADE
		ON DELETE SET NULL,
	CONSTRAINT chk_nap_details_trunk_next_nap
		CHECK (NOT port_trunk OR next_nap_id IS NOT NULL)
);

DO $$
BEGIN
	IF NOT EXISTS (
		SELECT 1
		FROM information_schema.columns
		WHERE table_schema = 'genius'
		  AND table_name = 'nap_details'
		  AND column_name = 'in_use'
	) THEN
		EXECUTE 'ALTER TABLE genius.nap_details ADD COLUMN in_use BOOLEAN NOT NULL DEFAULT FALSE';
	END IF;
END
$$;

DO $$
BEGIN
	IF EXISTS (
		SELECT 1
		FROM information_schema.columns
		WHERE table_schema = 'genius'
		  AND table_name = 'nap_details'
		  AND column_name = 'client_id'
	) THEN
		IF EXISTS (
			SELECT 1
			FROM pg_constraint con
			JOIN pg_class rel ON rel.oid = con.conrelid
			JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
			WHERE con.conname = 'fk_nap_details_client'
			  AND rel.relname = 'nap_details'
			  AND nsp.nspname = 'genius'
		) THEN
			EXECUTE 'ALTER TABLE genius.nap_details DROP CONSTRAINT fk_nap_details_client';
		END IF;

		IF EXISTS (
			SELECT 1
			FROM pg_class c
			JOIN pg_namespace n ON n.oid = c.relnamespace
			WHERE c.relkind = 'i'
			  AND c.relname = 'idx_nap_details_client_id'
			  AND n.nspname = 'genius'
		) THEN
			EXECUTE 'DROP INDEX genius.idx_nap_details_client_id';
		END IF;

		EXECUTE 'ALTER TABLE genius.nap_details DROP COLUMN client_id';
	END IF;
END
$$;

DO $$
BEGIN
	IF EXISTS (
		SELECT 1
		FROM pg_constraint con
		JOIN pg_class rel ON rel.oid = con.conrelid
		JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
		WHERE con.conname = 'chk_nap_details_trunk_client'
		  AND rel.relname = 'nap_details'
		  AND nsp.nspname = 'genius'
	) THEN
		EXECUTE 'ALTER TABLE genius.nap_details DROP CONSTRAINT chk_nap_details_trunk_client';
	END IF;
END
$$;

DO $$
BEGIN
	IF EXISTS (
		SELECT 1
		FROM information_schema.columns
		WHERE table_schema = 'genius'
		  AND table_name = 'nap_details'
		  AND column_name = 'in_use'
	) THEN
		EXECUTE 'UPDATE genius.nap_details SET in_use = FALSE WHERE in_use IS NULL';
		EXECUTE 'ALTER TABLE genius.nap_details ALTER COLUMN in_use SET DEFAULT FALSE';
	END IF;
END
$$;

DO $$
BEGIN
	IF NOT EXISTS (
		SELECT 1
		FROM information_schema.columns
		WHERE table_schema = 'genius'
		  AND table_name = 'nap_details'
		  AND column_name = 'next_nap_id'
	) THEN
		EXECUTE 'ALTER TABLE genius.nap_details ADD COLUMN next_nap_id BIGINT';
	END IF;
END
$$;

DO $$
BEGIN
	IF EXISTS (
		SELECT 1
		FROM information_schema.columns
		WHERE table_schema = 'genius'
		  AND table_name = 'nap_details'
		  AND column_name = 'next_nap_id'
	)
	AND NOT EXISTS (
		SELECT 1
		FROM pg_constraint con
		JOIN pg_class rel ON rel.oid = con.conrelid
		JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
		WHERE con.conname = 'fk_nap_details_next_nap'
		  AND rel.relname = 'nap_details'
		  AND nsp.nspname = 'genius'
	) THEN
		EXECUTE 'ALTER TABLE genius.nap_details ADD CONSTRAINT fk_nap_details_next_nap FOREIGN KEY (next_nap_id) REFERENCES genius.nap(correlative) ON UPDATE CASCADE ON DELETE SET NULL';
	END IF;
END
$$;

DO $$
BEGIN
	IF EXISTS (
		SELECT 1
		FROM information_schema.columns
		WHERE table_schema = 'genius'
		  AND table_name = 'nap_details'
		  AND column_name = 'in_use'
	)
	AND NOT EXISTS (
		SELECT 1
		FROM genius.nap_details
		WHERE in_use IS NULL
	) THEN
		EXECUTE 'ALTER TABLE genius.nap_details ALTER COLUMN in_use SET NOT NULL';
	END IF;
END
$$;

DO $$
BEGIN
	IF NOT EXISTS (
		SELECT 1
		FROM pg_class c
		JOIN pg_namespace n ON n.oid = c.relnamespace
		WHERE c.relkind = 'i'
		  AND c.relname = 'uq_nap_details_nap_port_name'
		  AND n.nspname = 'genius'
	) THEN
		EXECUTE 'CREATE UNIQUE INDEX uq_nap_details_nap_port_name ON genius.nap_details(nap_id, port_name)';
	END IF;
END
$$;

DO $$
BEGIN
	IF NOT EXISTS (
		SELECT 1
		FROM pg_class c
		JOIN pg_namespace n ON n.oid = c.relnamespace
		WHERE c.relkind = 'i'
		  AND c.relname = 'idx_nap_details_nap_id'
		  AND n.nspname = 'genius'
	) THEN
		EXECUTE 'CREATE INDEX idx_nap_details_nap_id ON genius.nap_details(nap_id)';
	END IF;
END
$$;

DO $$
BEGIN
	IF NOT EXISTS (
		SELECT 1
		FROM pg_class c
		JOIN pg_namespace n ON n.oid = c.relnamespace
		WHERE c.relkind = 'i'
		  AND c.relname = 'idx_nap_details_in_use'
		  AND n.nspname = 'genius'
	) THEN
		EXECUTE 'CREATE INDEX idx_nap_details_in_use ON genius.nap_details(in_use)';
	END IF;
END
$$;

DO $$
BEGIN
	IF NOT EXISTS (
		SELECT 1
		FROM pg_class c
		JOIN pg_namespace n ON n.oid = c.relnamespace
		WHERE c.relkind = 'i'
		  AND c.relname = 'idx_nap_details_next_nap_id'
		  AND n.nspname = 'genius'
	) THEN
		EXECUTE 'CREATE INDEX idx_nap_details_next_nap_id ON genius.nap_details(next_nap_id)';
	END IF;
END
$$;

DO $$
BEGIN
	IF NOT EXISTS (
		SELECT 1
		FROM pg_class c
		JOIN pg_namespace n ON n.oid = c.relnamespace
		WHERE c.relkind = 'i'
		  AND c.relname = 'idx_nap_details_port_trunk'
		  AND n.nspname = 'genius'
	) THEN
		EXECUTE 'CREATE INDEX idx_nap_details_port_trunk ON genius.nap_details(port_trunk)';
	END IF;
END
$$;

DO $$
BEGIN
	IF EXISTS (
		SELECT 1
		FROM information_schema.tables
		WHERE table_schema = 'genius'
		  AND table_name = 'nap_port_history'
	)
	AND EXISTS (
		SELECT 1
		FROM information_schema.tables
		WHERE table_schema = 'genius'
		  AND table_name = 'nap_details'
	)
	AND NOT EXISTS (
		SELECT 1
		FROM pg_constraint con
		JOIN pg_class rel ON rel.oid = con.conrelid
		JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
		WHERE con.conname = 'fk_nap_port_history_nap_detail'
		  AND rel.relname = 'nap_port_history'
		  AND nsp.nspname = 'genius'
	) THEN
		EXECUTE 'ALTER TABLE genius.nap_port_history ADD CONSTRAINT fk_nap_port_history_nap_detail FOREIGN KEY (nap_detail_id) REFERENCES genius.nap_details(correlative) ON UPDATE CASCADE ON DELETE CASCADE';
	END IF;
END
$$;

DO $$
BEGIN
	IF EXISTS (
		SELECT 1
		FROM pg_constraint con
		JOIN pg_class rel ON rel.oid = con.conrelid
		JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
		WHERE con.conname = 'chk_nap_details_trunk_next_nap'
		  AND rel.relname = 'nap_details'
		  AND nsp.nspname = 'genius'
	) THEN
		EXECUTE 'ALTER TABLE genius.nap_details DROP CONSTRAINT chk_nap_details_trunk_next_nap';
	END IF;
END
$$;

DO $$
BEGIN
	-- Si el puerto no es trunk, no debe apuntar a una NAP siguiente.
	EXECUTE 'UPDATE genius.nap_details SET next_nap_id = NULL WHERE NOT port_trunk';
END
$$;

DO $$
BEGIN
	IF NOT EXISTS (
		SELECT 1
		FROM pg_constraint con
		JOIN pg_class rel ON rel.oid = con.conrelid
		JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
		WHERE con.conname = 'chk_nap_details_trunk_next_nap_exact'
		  AND rel.relname = 'nap_details'
		  AND nsp.nspname = 'genius'
	) THEN
		EXECUTE 'ALTER TABLE genius.nap_details ADD CONSTRAINT chk_nap_details_trunk_next_nap_exact CHECK ((port_trunk AND next_nap_id IS NOT NULL) OR (NOT port_trunk AND next_nap_id IS NULL))';
	END IF;
END
$$;

CREATE OR REPLACE FUNCTION genius.validate_installation_nap_port()
RETURNS TRIGGER AS $$
DECLARE
	v_port_trunk BOOLEAN;
BEGIN
	IF NEW.nap_detail_id IS NULL THEN
		RETURN NEW;
	END IF;

	SELECT nd.port_trunk
	INTO v_port_trunk
	FROM genius.nap_details nd
	WHERE nd.correlative = NEW.nap_detail_id
	FOR UPDATE;

	IF NOT FOUND THEN
		RAISE EXCEPTION 'El puerto NAP % no existe.', NEW.nap_detail_id;
	END IF;

	IF v_port_trunk THEN
		RAISE EXCEPTION 'El puerto NAP % es trunk y no puede asignarse a una instalacion.', NEW.nap_detail_id;
	END IF;

	RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION genius.sync_nap_port_usage_from_installations()
RETURNS TRIGGER AS $$
BEGIN
	IF TG_OP = 'INSERT' THEN
		IF NEW.nap_detail_id IS NOT NULL THEN
			UPDATE genius.nap_details
			SET in_use = TRUE
			WHERE correlative = NEW.nap_detail_id;
		END IF;
		RETURN NEW;
	END IF;

	IF TG_OP = 'UPDATE' THEN
		IF NEW.nap_detail_id IS NOT NULL THEN
			UPDATE genius.nap_details
			SET in_use = TRUE
			WHERE correlative = NEW.nap_detail_id;
		END IF;

		IF OLD.nap_detail_id IS NOT NULL AND (NEW.nap_detail_id IS NULL OR OLD.nap_detail_id <> NEW.nap_detail_id) THEN
			UPDATE genius.nap_details nd
			SET in_use = CASE
				WHEN nd.port_trunk THEN TRUE
				WHEN EXISTS (
					SELECT 1
					FROM genius.installations i
					WHERE i.nap_detail_id = OLD.nap_detail_id
				) THEN TRUE
				ELSE FALSE
			END
			WHERE nd.correlative = OLD.nap_detail_id;
		END IF;

		RETURN NEW;
	END IF;

	IF TG_OP = 'DELETE' THEN
		IF OLD.nap_detail_id IS NOT NULL THEN
			UPDATE genius.nap_details nd
			SET in_use = CASE
				WHEN nd.port_trunk THEN TRUE
				WHEN EXISTS (
					SELECT 1
					FROM genius.installations i
					WHERE i.nap_detail_id = OLD.nap_detail_id
				) THEN TRUE
				ELSE FALSE
			END
			WHERE nd.correlative = OLD.nap_detail_id;
		END IF;
		RETURN OLD;
	END IF;

	RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION genius.enforce_nap_details_state()
RETURNS TRIGGER AS $$
DECLARE
	v_has_installation BOOLEAN;
BEGIN
	IF TG_OP = 'INSERT' THEN
		v_has_installation := FALSE;
	ELSE
		SELECT EXISTS (
			SELECT 1
			FROM genius.installations i
			WHERE i.nap_detail_id = OLD.correlative
		)
		INTO v_has_installation;
	END IF;

	IF NEW.port_trunk AND v_has_installation THEN
		RAISE EXCEPTION 'El puerto NAP % no puede marcarse como trunk porque ya esta asignado a una instalacion.', COALESCE(OLD.correlative, NEW.correlative);
	END IF;

	IF NEW.port_trunk THEN
		NEW.in_use := TRUE;
	ELSE
		IF v_has_installation THEN
			NEW.in_use := TRUE;
		ELSE
			NEW.in_use := FALSE;
		END IF;
	END IF;

	RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
BEGIN
	IF EXISTS (
		SELECT 1
		FROM pg_trigger t
		JOIN pg_class c ON c.oid = t.tgrelid
		JOIN pg_namespace n ON n.oid = c.relnamespace
		WHERE t.tgname = 'trg_validate_installation_nap_port'
		  AND c.relname = 'installations'
		  AND n.nspname = 'genius'
	) THEN
		EXECUTE 'DROP TRIGGER trg_validate_installation_nap_port ON genius.installations';
	END IF;
END
$$;

CREATE TRIGGER trg_validate_installation_nap_port
BEFORE INSERT OR UPDATE OF nap_detail_id ON genius.installations
FOR EACH ROW
EXECUTE PROCEDURE genius.validate_installation_nap_port();

DO $$
BEGIN
	IF EXISTS (
		SELECT 1
		FROM pg_trigger t
		JOIN pg_class c ON c.oid = t.tgrelid
		JOIN pg_namespace n ON n.oid = c.relnamespace
		WHERE t.tgname = 'trg_sync_nap_port_usage_installations'
		  AND c.relname = 'installations'
		  AND n.nspname = 'genius'
	) THEN
		EXECUTE 'DROP TRIGGER trg_sync_nap_port_usage_installations ON genius.installations';
	END IF;
END
$$;

CREATE TRIGGER trg_sync_nap_port_usage_installations
AFTER INSERT OR UPDATE OF nap_detail_id OR DELETE ON genius.installations
FOR EACH ROW
EXECUTE PROCEDURE genius.sync_nap_port_usage_from_installations();

DO $$
BEGIN
	IF EXISTS (
		SELECT 1
		FROM pg_trigger t
		JOIN pg_class c ON c.oid = t.tgrelid
		JOIN pg_namespace n ON n.oid = c.relnamespace
		WHERE t.tgname = 'trg_enforce_nap_details_state'
		  AND c.relname = 'nap_details'
		  AND n.nspname = 'genius'
	) THEN
		EXECUTE 'DROP TRIGGER trg_enforce_nap_details_state ON genius.nap_details';
	END IF;
END
$$;

CREATE TRIGGER trg_enforce_nap_details_state
BEFORE INSERT OR UPDATE OF port_trunk, next_nap_id, in_use ON genius.nap_details
FOR EACH ROW
EXECUTE PROCEDURE genius.enforce_nap_details_state();

DO $$
BEGIN
	UPDATE genius.nap_details nd
	SET in_use = CASE
		WHEN nd.port_trunk THEN TRUE
		WHEN EXISTS (
			SELECT 1
			FROM genius.installations i
			WHERE i.nap_detail_id = nd.correlative
		) THEN TRUE
		ELSE FALSE
	END;
END
$$;

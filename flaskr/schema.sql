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
	contract_number INTEGER,
	install_date DATE NOT NULL,
	location VARCHAR(255) NOT NULL,
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
		  AND column_name = 'contract_number'
	) THEN
		EXECUTE 'ALTER TABLE genius.installations ADD COLUMN contract_number INTEGER';
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
SET contract_number = oi.rn
FROM ordered_installations oi
WHERE i.id = oi.id
	AND i.contract_number IS NULL;

DO $$
BEGIN
	IF EXISTS (
		SELECT 1
		FROM information_schema.columns
		WHERE table_schema = 'genius'
		  AND table_name = 'installations'
		  AND column_name = 'contract_number'
	)
	AND NOT EXISTS (
		SELECT 1
		FROM genius.installations
		WHERE contract_number IS NULL
	) THEN
		EXECUTE 'ALTER TABLE genius.installations ALTER COLUMN contract_number SET NOT NULL';
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
		EXECUTE 'CREATE UNIQUE INDEX uq_installations_client_contract ON genius.installations(client_code, contract_number)';
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

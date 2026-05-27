DO $$
BEGIN
	IF NOT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 'genius') THEN
		EXECUTE 'CREATE SCHEMA genius';
	END IF;
END
$$;

-- Tabla principal de instalaciones
CREATE TABLE IF NOT EXISTS genius.installations (
	id BIGSERIAL PRIMARY KEY,
	client_code VARCHAR(30) NOT NULL,
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

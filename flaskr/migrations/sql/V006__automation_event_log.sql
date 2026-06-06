CREATE TABLE IF NOT EXISTS genius.automation_event_log (
    id BIGSERIAL PRIMARY KEY,
    automation_name VARCHAR(80) NOT NULL,
    action VARCHAR(80) NOT NULL,
    status VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    client_code VARCHAR(30),
    subscription_correlative BIGINT,
    receivable_correlative BIGINT,
    route_id BIGINT,
    mac_address VARCHAR(50),
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relkind = 'i'
          AND c.relname = 'idx_automation_event_log_created_at'
          AND n.nspname = 'genius'
    ) THEN
        EXECUTE 'CREATE INDEX idx_automation_event_log_created_at ON genius.automation_event_log(created_at DESC)';
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
          AND c.relname = 'idx_automation_event_log_subscription'
          AND n.nspname = 'genius'
    ) THEN
        EXECUTE 'CREATE INDEX idx_automation_event_log_subscription ON genius.automation_event_log(subscription_correlative)';
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
          AND c.relname = 'idx_automation_event_log_client'
          AND n.nspname = 'genius'
    ) THEN
        EXECUTE 'CREATE INDEX idx_automation_event_log_client ON genius.automation_event_log(client_code)';
    END IF;
END
$$;

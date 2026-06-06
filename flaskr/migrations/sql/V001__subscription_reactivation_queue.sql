CREATE TABLE IF NOT EXISTS genius.subscription_reactivation_queue (
    id BIGSERIAL PRIMARY KEY,
    receivable_correlative BIGINT NOT NULL,
    subscription_correlative BIGINT NOT NULL,
    client_code VARCHAR(30) NOT NULL,
    queued_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMP WITHOUT TIME ZONE,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    error_message TEXT
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relkind = 'i'
          AND c.relname = 'idx_subscription_reactivation_queue_status'
          AND n.nspname = 'genius'
    ) THEN
        EXECUTE 'CREATE INDEX idx_subscription_reactivation_queue_status ON genius.subscription_reactivation_queue(status, queued_at)';
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
          AND c.relname = 'uq_subscription_reactivation_queue_receivable'
          AND n.nspname = 'genius'
    ) THEN
        EXECUTE 'CREATE UNIQUE INDEX uq_subscription_reactivation_queue_receivable ON genius.subscription_reactivation_queue(receivable_correlative)';
    END IF;
END
$$;

CREATE OR REPLACE FUNCTION genius.fn_enqueue_subscription_reactivation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    v_subscription_text TEXT;
    v_subscription_correlative BIGINT;
BEGIN
    IF NEW.operation_type <> 'RECEIVABLE' THEN
        RETURN NEW;
    END IF;

    IF COALESCE(NEW.payment_applied, 0) <= COALESCE(OLD.payment_applied, 0) THEN
        RETURN NEW;
    END IF;

    v_subscription_text := substring(COALESCE(NEW.description, '') FROM 'suscripcion #([0-9]+)');

    IF v_subscription_text IS NULL OR btrim(v_subscription_text) = '' THEN
        RETURN NEW;
    END IF;

    v_subscription_correlative := v_subscription_text::BIGINT;

    BEGIN
        INSERT INTO genius.subscription_reactivation_queue (
            receivable_correlative,
            subscription_correlative,
            client_code
        )
        VALUES (
            NEW.correlative,
            v_subscription_correlative,
            COALESCE(NEW.client_code, '')
        );
    EXCEPTION
        WHEN unique_violation THEN
            NULL;
    END;

    RETURN NEW;
EXCEPTION
    WHEN others THEN
        RETURN NEW;
END;
$$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name = 'receivable'
    )
    AND EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'receivable'
          AND column_name = 'payment_applied'
    )
    AND NOT EXISTS (
        SELECT 1
        FROM pg_trigger t
        JOIN pg_class c ON c.oid = t.tgrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE t.tgname = 'trg_enqueue_subscription_reactivation'
          AND c.relname = 'receivable'
          AND n.nspname = 'public'
    ) THEN
        EXECUTE '
            CREATE TRIGGER trg_enqueue_subscription_reactivation
            AFTER UPDATE OF payment_applied ON public.receivable
            FOR EACH ROW
            EXECUTE PROCEDURE genius.fn_enqueue_subscription_reactivation()
        ';
    END IF;
END
$$;

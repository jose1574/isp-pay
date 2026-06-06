CREATE TABLE IF NOT EXISTS genius.subscription_receivable_link (
    id BIGSERIAL PRIMARY KEY,
    receivable_correlative BIGINT NOT NULL,
    subscription_correlative BIGINT NOT NULL,
    client_code VARCHAR(30) NOT NULL,
    emission_date DATE NOT NULL,
    amount NUMERIC(12,2) NOT NULL DEFAULT 0,
    payment_status VARCHAR(50) NOT NULL DEFAULT 'pending_payment',
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relkind = 'i'
          AND c.relname = 'uq_subscription_receivable_link_receivable'
          AND n.nspname = 'genius'
    ) THEN
        EXECUTE 'CREATE UNIQUE INDEX uq_subscription_receivable_link_receivable ON genius.subscription_receivable_link(receivable_correlative)';
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
          AND c.relname = 'idx_subscription_receivable_link_subscription'
          AND n.nspname = 'genius'
    ) THEN
        EXECUTE 'CREATE INDEX idx_subscription_receivable_link_subscription ON genius.subscription_receivable_link(subscription_correlative, emission_date)';
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
          AND c.relname = 'idx_subscription_receivable_link_status'
          AND n.nspname = 'genius'
    ) THEN
        EXECUTE 'CREATE INDEX idx_subscription_receivable_link_status ON genius.subscription_receivable_link(payment_status, updated_at)';
    END IF;
END
$$;

CREATE OR REPLACE FUNCTION genius.fn_enqueue_subscription_reactivation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    v_subscription_correlative BIGINT;
    v_client_code VARCHAR(30);
BEGIN
    IF NEW.operation_type <> 'RECEIVABLE' THEN
        RETURN NEW;
    END IF;

    IF COALESCE(NEW.payment_applied, 0) <= COALESCE(OLD.payment_applied, 0) THEN
        RETURN NEW;
    END IF;

    SELECT
        l.subscription_correlative,
        l.client_code
    INTO
        v_subscription_correlative,
        v_client_code
    FROM genius.subscription_receivable_link l
    WHERE l.receivable_correlative = NEW.correlative
    LIMIT 1;

    IF v_subscription_correlative IS NULL THEN
        RETURN NEW;
    END IF;

    IF COALESCE(NEW.balance, COALESCE(NEW.total, 0) - COALESCE(NEW.payment_applied, 0)) > 0 THEN
        UPDATE genius.subscription_receivable_link
        SET payment_status = 'partial_payment', updated_at = NOW()
        WHERE receivable_correlative = NEW.correlative;

        RETURN NEW;
    END IF;

    UPDATE genius.subscription_receivable_link
    SET payment_status = 'paid_pending_activation', updated_at = NOW()
    WHERE receivable_correlative = NEW.correlative;

    BEGIN
        INSERT INTO genius.subscription_reactivation_queue (
            receivable_correlative,
            subscription_correlative,
            client_code
        )
        VALUES (
            NEW.correlative,
            v_subscription_correlative,
            COALESCE(v_client_code, COALESCE(NEW.client_code, ''))
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

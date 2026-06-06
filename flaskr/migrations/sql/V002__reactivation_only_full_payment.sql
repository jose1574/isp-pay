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

    IF COALESCE(NEW.balance, COALESCE(NEW.total, 0) - COALESCE(NEW.payment_applied, 0)) > 0 THEN
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

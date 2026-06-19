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

    IF COALESCE(NEW.balance, COALESCE(NEW.total, 0) - COALESCE(NEW.payment_applied, 0)) > 0.01 THEN
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
            UPDATE genius.subscription_reactivation_queue
            SET status = 'pending', processed_at = NULL, error_message = NULL
            WHERE receivable_correlative = NEW.correlative
              AND status <> 'pending';
    END;

    RETURN NEW;
EXCEPTION
    WHEN others THEN
        RETURN NEW;
END;
$$;

INSERT INTO genius.subscription_receivable_link (
    receivable_correlative,
    subscription_correlative,
    client_code,
    emission_date,
    amount,
    payment_status,
    created_at,
    updated_at
)
SELECT
    r.correlative,
    substring(lower(COALESCE(r.description, '')) FROM 'suscripcion #([0-9]+)')::BIGINT,
    COALESCE(r.client_code, ''),
    r.emission_date,
    COALESCE(r.total, 0),
    CASE
        WHEN COALESCE(r.balance, COALESCE(r.total, 0) - COALESCE(r.payment_applied, 0)) <= 0 THEN 'paid_pending_activation'
        WHEN COALESCE(r.payment_applied, 0) > 0 THEN 'partial_payment'
        ELSE 'pending_payment'
    END,
    NOW(),
    NOW()
FROM receivable r
WHERE r.operation_type = 'RECEIVABLE'
  AND substring(lower(COALESCE(r.description, '')) FROM 'suscripcion #([0-9]+)') IS NOT NULL
  AND NOT EXISTS (
      SELECT 1
      FROM genius.subscription_receivable_link l
      WHERE l.receivable_correlative = r.correlative
  );

CREATE OR REPLACE VIEW genius.v_subscription_receivable_audit AS
SELECT
    l.id AS link_id,
    l.subscription_correlative,
    s.status AS subscription_status,
    l.client_code,
    c.description AS client_name,
    l.receivable_correlative,
    l.emission_date,
    l.amount AS linked_amount,
    COALESCE(r.total, 0) AS receivable_total,
    COALESCE(r.payment_applied, 0) AS receivable_payment_applied,
    COALESCE(r.balance, COALESCE(r.total, 0) - COALESCE(r.payment_applied, 0)) AS receivable_balance,
    CASE
        WHEN COALESCE(r.balance, COALESCE(r.total, 0) - COALESCE(r.payment_applied, 0)) <= 0 THEN 'paid'
        WHEN COALESCE(r.payment_applied, 0) > 0 THEN 'partial'
        ELSE 'pending'
    END AS receivable_payment_state,
    l.payment_status AS link_payment_status,
    i.id AS installation_id,
    i.mac_address,
    i.route_id,
    l.created_at,
    l.updated_at
FROM genius.subscription_receivable_link l
LEFT JOIN genius.subscription s
    ON s.correlative = l.subscription_correlative
LEFT JOIN public.receivable r
    ON r.correlative = l.receivable_correlative
LEFT JOIN public.clients c
    ON c.code = l.client_code
LEFT JOIN genius.installations i
    ON i.id = s.installation;

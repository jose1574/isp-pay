Migraciones SQL manuales

- Crea archivos con formato: VYYYYMMDDHHMM__descripcion.sql
- Ejemplo: V202606020930__agrega_columna_foo.sql
- Las migraciones se aplican en orden alfabetico (versionadas por prefijo V...)
- Cada migracion aplicada se registra en genius.schema_migrations con checksum.
- Si cambias una migracion ya aplicada, la app detiene el arranque para proteger datos.

Recomendaciones

- Escribe migraciones idempotentes cuando sea posible (IF EXISTS / IF NOT EXISTS).
- Evita operaciones destructivas sin respaldo.
- Prueba primero en staging antes de produccion.

Checklist Post-Despliegue (Suscripciones y CxC)

1. Aplicar migraciones en el entorno objetivo:

	flask --app flaskr migrate-db

2. Verificar que existen los objetos nuevos:

	SELECT to_regclass('genius.subscription_receivable_link') AS tabla_link,
			 to_regclass('genius.subscription_reactivation_queue') AS tabla_cola;

	SELECT to_regclass('genius.v_subscription_receivable_audit') AS vista_auditoria;

3. Revisar integridad de relaciones suscripcion-CxC:

	SELECT link_id,
			 subscription_correlative,
			 receivable_correlative,
			 receivable_total,
			 receivable_payment_applied,
			 receivable_balance,
			 receivable_payment_state,
			 link_payment_status,
			 subscription_status
	FROM genius.v_subscription_receivable_audit
	ORDER BY updated_at DESC
	LIMIT 50;

4. Validar regla de pago fraccionado (NO debe activar):

	SELECT COUNT(*) AS pendientes_monto
	FROM genius.v_subscription_receivable_audit
	WHERE receivable_payment_state = 'partial'
	  AND subscription_status <> 'activo';

	Resultado esperado: filas mayores o iguales a 0 segun datos, y sin activacion automatica en parciales.

5. Validar regla de pago completo (SI debe activar):

	SELECT COUNT(*) AS pagadas_pendientes_activacion
	FROM genius.v_subscription_receivable_audit
	WHERE receivable_payment_state = 'paid'
	  AND link_payment_status IN ('paid_pending_activation', 'partial_payment');

	Si el conteo es mayor a 0, ejecutar checker:

	flask --app flaskr check-paid-subscriptions

	Luego revalidar:

	SELECT COUNT(*) AS pagadas_sin_activar
	FROM genius.v_subscription_receivable_audit
	WHERE receivable_payment_state = 'paid'
	  AND subscription_status <> 'activo';

	Resultado esperado: 0 (o solo casos con error de red/router, que quedaran en cola con error).

6. Validar que otras deudas del cliente NO afecten la suscripcion:

	SELECT a.subscription_correlative,
			 a.client_code,
			 a.receivable_correlative,
			 a.receivable_payment_state,
			 a.subscription_status,
			 q.status AS cola_status,
			 q.error_message
	FROM genius.v_subscription_receivable_audit a
	LEFT JOIN genius.subscription_reactivation_queue q
			 ON q.receivable_correlative = a.receivable_correlative
	WHERE a.client_code = :client_code
	ORDER BY a.updated_at DESC;

	Resultado esperado: solo CxC vinculadas en subscription_receivable_link pueden cambiar estado de la suscripcion.

7. Monitoreo operativo recomendado (cada 1-5 minutos):

	flask --app flaskr check-overdue-subscriptions
	flask --app flaskr check-paid-subscriptions

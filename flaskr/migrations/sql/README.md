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

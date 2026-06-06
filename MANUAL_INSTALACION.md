# Manual de Instalacion - ISP PAY

Este documento explica como dejar la aplicacion lista en un equipo nuevo o en un servidor Windows.

## 1. Requisitos previos

- Python 3.10 o superior.
- PostgreSQL en ejecucion.
- Acceso de red a los routers MikroTik.
- Un usuario de PostgreSQL con permisos para crear esquemas, tablas, vistas, funciones y triggers.
- PowerShell o CMD en Windows.

## 2. Revision del archivo requirements.txt

El archivo [requirements.txt](requirements.txt) contiene solo las dependencias necesarias para esta aplicacion:

- Flask
- Flask-SQLAlchemy
- SQLAlchemy
- librouteros
- requests
- urllib3
- psycopg2-binary

No se necesitan paquetes adicionales para ejecutar las migraciones ni el panel de automatizaciones.

## 3. Crear el entorno virtual

Desde la raiz del proyecto:

```bat
py -3 -m venv .venv
```

Si ya existe `.venv`, puedes omitir este paso.

## 4. Instalar dependencias

Activa el entorno virtual e instala los paquetes:

```bat
.venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 5. Configuracion de base de datos

La aplicacion usa PostgreSQL y crea sus objetos dentro del esquema `genius`.

La cadena de conexion por defecto esta definida en el proyecto, pero en instalacion real conviene ajustar `instance/config.py` si necesitas otra base de datos.

Ejemplo de `instance/config.py`:

```python
SECRET_KEY = 'cambia-esta-clave'
SQLALCHEMY_DATABASE_URI = 'postgresql://usuario:clave@localhost:5432/tu_base'
AUTO_INIT_DB = True
```

## 6. Crear tablas en el esquema genius

La aplicacion ya incluye el comando para crear la estructura de base de datos y aplicar migraciones.

Ejecuta:

```bat
flask --app flaskr migrate-db
```

Ese comando hace lo siguiente:

- Ejecuta `flaskr/schema.sql`
- Crea el esquema `genius` si no existe
- Crea tablas base como `genius.plans`, `genius.subscription`, `genius.installations`, etc.
- Aplica las migraciones `V*.sql` pendientes
- Registra cada migracion en `genius.schema_migrations`

## 7. Automatizaciones

La aplicacion ya trae dos procesos de automatizacion:

```bat
flask --app flaskr check-overdue-subscriptions
flask --app flaskr check-paid-subscriptions
```

Uso recomendado:

- `check-overdue-subscriptions`: suspende suscripciones vencidas y crea la cuenta por cobrar.
- `check-paid-subscriptions`: reactiva la suscripcion cuando la cuenta por cobrar vinculada queda totalmente pagada.

## 8. Opcion automatica con un solo comando

Si prefieres automatizar la instalacion, usa el script:

- [bootstrap_install.bat](bootstrap_install.bat)

Ese script instala dependencias, aplica migraciones y deja la base lista.

## 9. Opcion totalmente automatizada con configuracion incluida

Si quieres que el instalador tambien cree `instance/config.py`, usa preferentemente:

- [full_install_isp_pay.ps1](full_install_isp_pay.ps1)

Como alternativa, tambien existe:

- [full_install_isp_pay.bat](full_install_isp_pay.bat)

Este script:

- crea `.venv` si no existe
- instala dependencias
- genera `instance/config.py` con los datos de conexion
- aplica migraciones y crea las tablas del esquema `genius`
- ejecuta las automatizaciones para validar la instalacion

Puedes definir antes de ejecutarlo estas variables de entorno:

- `SECRET_KEY`
- `DB_HOST`
- `DB_PORT`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `AUTO_INIT_DB` (usa `true`, `false`, `1`, `0`, `yes` o `no`; el instalador lo convierte a `True`/`False` para Python)

Ejemplo de ejecucion en PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\full_install_isp_pay.ps1
```

## 10. Verificacion final

Despues de instalar, valida que las tablas y vistas existan:

```sql
SELECT to_regclass('genius.subscription');
SELECT to_regclass('genius.subscription_receivable_link');
SELECT to_regclass('genius.subscription_reactivation_queue');
SELECT to_regclass('genius.automation_event_log');
SELECT to_regclass('genius.v_subscription_receivable_audit');
```

Tambien puedes probar el panel web y el menu de automatizaciones.

## 11. Despliegue en produccion

Para produccion, ejecuta los comandos desde una consola con acceso al entorno virtual y programa las tareas del sistema operativo para llamar:

- `check-overdue-subscriptions`
- `check-paid-subscriptions`


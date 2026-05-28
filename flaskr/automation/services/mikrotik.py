import requests
from requests.auth import HTTPBasicAuth

# Configuración del router
HOST = "192.168.33.1"  # Cambia por la IP de tu MikroTik
USER = "josegomez"
PASSWORD = "jose1574**"

# URL base de la REST API
URL = f"https://{HOST}/rest/system/resource"

# Desactivar alertas de certificados auto-firmados en la consola
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    # Realizamos la consulta GET
    response = requests.get(
        URL, 
        auth=HTTPBasicAuth(USER, PASSWORD), 
        verify=False  # Al poner False ignora si el certificado SSL es local/auto-firmado
    )

    if response.status_code == 200:
        datos = response.json()
        print("¡Conexión exitosa!")
        print(f"Modelo: {datos.get('board-name')}")
        print(f"Versión de RouterOS: {datos.get('version')}")
        print(f"Uptime: {datos.get('uptime')}")
    else:
        print(f"Error del router: {response.status_code} - {response.text}")

except Exception as e:
    print(f"No se pudo conectar al MikroTik: {e}")
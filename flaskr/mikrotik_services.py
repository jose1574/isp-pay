import requests
from requests.auth import HTTPBasicAuth
import urllib3

# Apagamos las alertas del certificado auto-firmado globalmente en este módulo
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class MikroTikClient:
    def __init__(self, host, user, password, use_ssl=False):
        # Manejamos dinámicamente si usas http o https
        protocol = "https" if use_ssl else "http"
        self.base_url = f"{protocol}://{host}/rest"
        self.auth = HTTPBasicAuth(user, password)

    def query(self, endpoint):
        """
        Método genérico para realizar consultas GET a la REST API.
        endpoint: por ejemplo '/system/resource' o '/interface'
        """
        # Aseguramos que el endpoint empiece con barra, pero no duplique la del base_url
        endpoint_limpio = endpoint.lstrip('/')
        url = f"{self.base_url}/{endpoint_limpio}"
        
        try:
            response = requests.get(
                url, 
                auth=self.auth, 
                verify=False,  # Ignora la falta de certificado SSL
                timeout=5      # Evita que tu app Flask se quede colgada si el router no responde
            )
            
            if response.status_code == 200:
                return response.json(), True
            else:
                return f"Error {response.status_code}: {response.text}", False
                
        except requests.exceptions.RequestException as e:
            return f"No se pudo conectar al MikroTik: {str(e)}", False
        


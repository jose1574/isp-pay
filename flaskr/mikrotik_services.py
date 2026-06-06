from librouteros import connect
from librouteros.exceptions import LibRouterosError, TrapError
from ssl import CERT_NONE, create_default_context

class MikroTikClient:
    def __init__(self, host, user, password, use_ssl=False, port=None):
        self.host = str(host).strip()
        self.user = user
        self.password = password
        self.use_ssl = use_ssl
        self.port = int(port) if port else (8729 if use_ssl else 8728)

    def _build_ssl_wrapper(self):
        if not self.use_ssl:
            return None

        context = create_default_context()
        context.check_hostname = False
        context.verify_mode = CERT_NONE
        return lambda sock: context.wrap_socket(sock, server_hostname=self.host)

    def _connect(self):
        return connect(
            host=self.host,
            username=self.user,
            password=self.password,
            port=self.port,
            timeout=10,
            ssl_wrapper=self._build_ssl_wrapper(),
        )

    def query(self, endpoint):
        api = None
        try:
            api = self._connect()
            endpoint_parts = [part for part in endpoint.strip('/').split('/') if part]
            response = list(api.path(*endpoint_parts))
            return response, True
        except (LibRouterosError, TrapError, OSError, ValueError) as error:
            return f"No se pudo conectar al MikroTik: {error}", False
        finally:
            if api is not None:
                api.close()

    def set_dhcp_lease_block_access(self, lease_id, block_access):
        api = None
        try:
            api = self._connect()
            leases = api.path('ip', 'dhcp-server', 'lease')
            leases.update(**{'.id': str(lease_id), 'block-access': block_access})
            return True, None
        except (LibRouterosError, TrapError, OSError, ValueError) as error:
            return False, f'No se pudo actualizar el cliente en el MikroTik: {error}'
        finally:
            if api is not None:
                api.close()



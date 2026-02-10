import requests
from requests.auth import HTTPBasicAuth
import config

class RouterAPI:
    def __init__(self):
        self.base_url = f"https://{config.ROUTER_IP}/rest"
        self.auth = HTTPBasicAuth(config.ROUTER_USER, config.ROUTER_PASS)
        # Matikan verify jika tidak pakai SSL certificate valid
        self.verify = False 

    def get_resource(self, path):
        response = requests.get(f"{self.base_url}/{path}", auth=self.auth, verify=self.verify)
        return response.json()

    def get_interfaces(self):
        return self.get_resource("interface")
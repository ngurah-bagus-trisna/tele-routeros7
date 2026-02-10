import requests
from requests.auth import HTTPBasicAuth
import config
import urllib3

# Menghilangkan pesan warning InsecureRequest di log
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class RouterAPI:
    def __init__(self):
        self.base_url = f"https://{config.ROUTER_IP}/rest"
        self.auth = HTTPBasicAuth(config.ROUTER_USER, config.ROUTER_PASS)
        self.verify = False 

    def get_resource(self, path):
        try:
            # Pastikan path tidak diawali / karena base_url sudah punya /rest
            url = f"{self.base_url}/{path.lstrip('/')}"
            response = requests.get(url, auth=self.auth, verify=self.verify, timeout=10)
            
            # Cek jika status code bukan 200 OK
            if response.status_code != 200:
                print(f"❌ Error API: Status {response.status_code} - {response.text}")
                return None
            
            # Pastikan response adalah JSON
            return response.json()
            
        except requests.exceptions.JSONDecodeError:
            print(f"❌ Error: Respon dari MikroTik bukan JSON. Raw content: {response.text[:100]}")
            return None
        except Exception as e:
            print(f"❌ Connection Error: {e}")
            return None

    def get_interfaces(self):
        return self.get_resource("interface")
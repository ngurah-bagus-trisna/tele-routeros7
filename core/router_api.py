import requests
from requests.auth import HTTPBasicAuth
import config
import urllib3
import logging
import os
import tempfile

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

    def post_resource(self, path, data=None):
        """POST request ke router"""
        try:
            url = f"{self.base_url}/{path.lstrip('/')}"
            response = requests.post(url, auth=self.auth, verify=self.verify, timeout=10, json=data)
            
            if response.status_code not in [200, 201]:
                print(f"❌ Error API POST: Status {response.status_code} - {response.text}")
                return None
            
            return response.json() if response.text else {"status": "ok"}
            
        except Exception as e:
            print(f"❌ Connection Error (POST): {e}")
            return None

    def get_interfaces(self):
        return self.get_resource("interface")

    def get_hotspot_users(self):
        """Ambil daftar user hotspot yang sedang aktif"""
        return self.get_resource("ip/hotspot/user")

    def get_hotspot_sessions(self):
        """Ambil daftar session hotspot yang aktif (login info)"""
        return self.get_resource("ip/hotspot/active")

    def get_dhcp_leases(self):
        """Ambil daftar DHCP lease dari server"""
        return self.get_resource("ip/dhcp-server/lease")

    def get_ppp_secrets(self):
        """Ambil daftar PPP secrets (user/password)"""
        return self.get_resource("ppp/secret")

    def backup_router(self):
        """Trigger backup router configuration"""
        try:
            # Trigger backup save tanpa password
            data = {}
            result = self.post_resource("system/backup/save", data)
            return result
        except Exception as e:
            print(f"❌ Error triggering backup: {e}")
            return None

    def download_backup(self, filename="backup.backup"):
        """Download backup file dari router"""
        try:
            # URL untuk download backup
            url = f"https://{config.ROUTER_IP}/download?file={filename}"
            response = requests.get(url, auth=self.auth, verify=self.verify, timeout=30)
            
            if response.status_code != 200:
                print(f"❌ Error downloading backup: Status {response.status_code}")
                return None
            
            # Simpan file ke temp location
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".backup")
            temp_file.write(response.content)
            temp_file.close()
            
            return temp_file.name
            
        except Exception as e:
            print(f"❌ Error downloading backup file: {e}")
            return None

    def get_backup_files(self):
        """List semua backup files di router"""
        return self.get_resource("file")

    def get_system_identity(self):
        """Ambil identitas system router"""
        result = self.get_resource("system/identity")
        if isinstance(result, list) and len(result) > 0:
            return result[0]
        return result

    def get_interfaces_detail(self):
        """Ambil detail semua interface dengan status, speed, dan error info"""
        try:
            interfaces = self.get_interfaces()
            if not interfaces:
                return None
            
            # Enrichment data dengan statistik error
            for iface in interfaces:
                iface_name = iface.get('name')
                # Coba ambil statistics jika tersedia
                stats = self.get_resource(f"interface/ether/{iface_name}/stats")
                if stats and isinstance(stats, dict):
                    iface['rx-error'] = stats.get('rx-error', 0)
                    iface['tx-error'] = stats.get('tx-error', 0)
                    iface['rx-drop'] = stats.get('rx-drop', 0)
                    iface['tx-drop'] = stats.get('tx-drop', 0)
            
            return interfaces
        except Exception as e:
            print(f"❌ Error getting interface details: {e}")
            return None

    def get_ppp_interfaces(self):
        """Ambil PPP interface (untuk monitoring dial-up/DSL links)"""
        return self.get_resource("interface/ppp")

    def get_ether_interfaces(self):
        """Ambil ethernet interface"""
        return self.get_resource("interface/ether")

    def get_wireless_interfaces(self):
        """Ambil wireless interface"""
        return self.get_resource("interface/wireless")

    def get_bridge_interfaces(self):
        """Ambil bridge interface"""
        return self.get_resource("interface/bridge")

    def get_link_status(self, interface_name):
        """Ambil status link dari interface tertentu"""
        try:
            # Coba ambil dari interface path
            result = self.get_resource(f"interface/{interface_name}")
            if result and isinstance(result, list) and len(result) > 0:
                return result[0]
            return None
        except Exception as e:
            print(f"❌ Error getting link status: {e}")
            return None
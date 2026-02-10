import sqlite3
from datetime import datetime, timedelta

class Database:
    def __init__(self, db_name="traffic.db"):
        self.db_name = db_name
        self.init_db()

    def init_db(self):
        with sqlite3.connect(self.db_name) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS traffic_history (
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    interface TEXT,
                    rx_bytes INTEGER,
                    tx_bytes INTEGER
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS hotspot_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT,
                    mac_address TEXT,
                    ip_address TEXT,
                    login_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                    logout_time DATETIME,
                    status TEXT DEFAULT 'active'
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS dhcp_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mac_address TEXT,
                    ip_address TEXT,
                    hostname TEXT,
                    event_type TEXT,
                    event_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                    lease_time INTEGER,
                    status TEXT DEFAULT 'pending'
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS interface_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    interface_name TEXT,
                    event_type TEXT,
                    status TEXT,
                    speed TEXT,
                    rx_error INTEGER DEFAULT 0,
                    tx_error INTEGER DEFAULT 0,
                    event_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                    details TEXT
                )
            ''')
            
            conn.commit()

    def save_snapshot(self, interface, rx, tx):
        with sqlite3.connect(self.db_name) as conn:
            conn.execute(
                "INSERT INTO traffic_history (interface, rx_bytes, tx_bytes) VALUES (?, ?, ?)",
                (interface, rx, tx)
            )
            conn.commit()

    def get_past_data(self, interface, period):
        # Mapping period ke menit
        offsets = {"1h": 60, "1d": 1440, "1m": 43800, "1y": 525600}
        minutes = offsets.get(period, 60)
        
        target_time = (datetime.now() - timedelta(minutes=minutes)).strftime('%Y-%m-%d %H:%M:%S')
        
        with sqlite3.connect(self.db_name) as conn:
            # Mencari data yang paling mendekati target_time
            cursor = conn.execute('''
                SELECT rx_bytes, tx_bytes FROM traffic_history 
                WHERE interface = ? AND timestamp <= ? 
                ORDER BY timestamp DESC LIMIT 1
            ''', (interface, target_time))
            return cursor.fetchone()

    def save_hotspot_login(self, username, mac_address, ip_address):
        """Simpan hotspot login event"""
        with sqlite3.connect(self.db_name) as conn:
            conn.execute(
                "INSERT INTO hotspot_sessions (username, mac_address, ip_address, status) VALUES (?, ?, ?, ?)",
                (username, mac_address, ip_address, 'active')
            )
            conn.commit()

    def save_hotspot_logout(self, username, mac_address):
        """Update hotspot logout event"""
        with sqlite3.connect(self.db_name) as conn:
            conn.execute(
                "UPDATE hotspot_sessions SET logout_time = CURRENT_TIMESTAMP, status = ? WHERE username = ? AND mac_address = ? AND status = ?",
                ('inactive', username, mac_address, 'active')
            )
            conn.commit()

    def save_dhcp_event(self, mac_address, ip_address, hostname, event_type, lease_time):
        """Simpan DHCP event"""
        with sqlite3.connect(self.db_name) as conn:
            conn.execute(
                "INSERT INTO dhcp_events (mac_address, ip_address, hostname, event_type, lease_time, status) VALUES (?, ?, ?, ?, ?, ?)",
                (mac_address, ip_address, hostname, event_type, lease_time, 'pending')
            )
            conn.commit()

    def get_recent_hotspot_sessions(self, limit=10):
        """Ambil recent hotspot sessions"""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.execute('''
                SELECT username, mac_address, ip_address, login_time, logout_time, status 
                FROM hotspot_sessions 
                ORDER BY login_time DESC LIMIT ?
            ''', (limit,))
            return cursor.fetchall()

    def get_recent_dhcp_events(self, limit=10):
        """Ambil recent DHCP events"""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.execute('''
                SELECT mac_address, ip_address, hostname, event_type, event_time, lease_time 
                FROM dhcp_events 
                ORDER BY event_time DESC LIMIT ?
            ''', (limit,))
            return cursor.fetchall()

    def save_interface_event(self, interface_name, event_type, status, speed=None, rx_error=0, tx_error=0, details=None):
        """Simpan interface event"""
        with sqlite3.connect(self.db_name) as conn:
            conn.execute(
                "INSERT INTO interface_events (interface_name, event_type, status, speed, rx_error, tx_error, details) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (interface_name, event_type, status, speed, rx_error, tx_error, details)
            )
            conn.commit()

    def get_recent_interface_events(self, limit=20):
        """Ambil recent interface events"""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.execute('''
                SELECT interface_name, event_type, status, speed, rx_error, tx_error, event_time, details 
                FROM interface_events 
                ORDER BY event_time DESC LIMIT ?
            ''', (limit,))
            return cursor.fetchall()
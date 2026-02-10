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
            conn.commit()

    def save_snapshot(self, interface, rx, tx):
        with sqlite3.connect(self.db_name) as conn:
            conn.execute(
                "INSERT INTO traffic_history (interface, rx_bytes, tx_bytes) VALUES (?, ?, ?)",
                (interface, rx, tx)
            )

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
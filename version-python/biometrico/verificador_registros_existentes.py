from zk import ZK
import sys

print("Python:", sys.executable)

DEVICE_IP = "192.168.1.203"

zk = ZK(DEVICE_IP, port=4370, timeout=5)

try:
    conn = zk.connect()
    print("✅ Conectado al dispositivo")

    logs = conn.get_attendance()
    print(f"📋 Registros encontrados: {len(logs)}")

    for log in logs:
        print(log.user_id, log.timestamp)

    conn.disconnect()
    print("🔌 Desconectado")

except Exception as e:
    print("❌ Error:", e)

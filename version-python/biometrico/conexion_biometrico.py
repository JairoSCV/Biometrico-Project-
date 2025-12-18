import time
import logging
import os
from zk import ZK
import mysql.connector
from mysql.connector import Error

# ------------------ CONFIGURACIÓN ------------------
DEVICE_IP = "192.168.1.203"
SLEEP_TIME = 30  # segundos entre chequeos
MYSQL_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",  # tu contraseña MySQL
    "database": "pruebas_marcacion"
}

# ------------------ LOGGING UTF-8 ------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE_DIR, "marcaciones.log")

logger = logging.getLogger()
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(file_handler)

console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(console_handler)

# ------------------ FUNCIONES ------------------
def guardar_registro(cursor, dni, fecha, evento):
    sql = "INSERT INTO marcaciones (dni, fecha, evento) VALUES (%s, %s, %s)"
    cursor.execute(sql, (dni, fecha, evento))

def procesar_marcaciones():
    zk = ZK(DEVICE_IP, port=4370, timeout=20)
    try:
        conn = zk.connect()
        logging.info("Conectado al dispositivo")

        try:
            conn.disable_device()

            # Intentar leer registros con get_attendance()
            try:
                logging.info("Intentando get_attendance()")
                logs = conn.get_attendance()
            except Exception as err1:
                logging.warning(f"get_attendance() falló: {err1}. Intentando get_attendance_ext()")
                try:
                    logs = conn.get_attendance_ext()
                    logging.info("get_attendance_ext() exitoso")
                except Exception as err2:
                    logging.error(f"get_attendance_ext() también falló: {err2}")
                    logs = []

            logging.info(f"Registros encontrados: {len(logs)}")

            if logs:
                registros_procesados = 0
                try:
                    with mysql.connector.connect(**MYSQL_CONFIG) as db:
                        with db.cursor() as cursor:
                            for i, log in enumerate(logs):
                                try:
                                    dni = str(log.user_id)
                                    fecha = log.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                                    evento = str(getattr(log, 'punch', 'N/A'))
                                    logging.info(f"[{i}] Guardando: DNI={dni}, Fecha={fecha}, Evento={evento}")
                                    guardar_registro(cursor, dni, fecha, evento)
                                    registros_procesados += 1
                                except Exception as e:
                                    logging.error(f"[{i}] Registro corrupto ignorado: {e}")
                            db.commit()
                except Error as e:
                    logging.error(f"Error en MySQL: {e}")

                if registros_procesados > 0:
                    try:
                        conn.clear_attendance()
                        logging.info("Registros borrados del dispositivo")
                    except Exception as e:
                        logging.error(f"No se pudieron borrar los registros: {e}")
            else:
                logging.info("No hay registros para procesar")

        except Exception as e:
            logging.error(f"Error al leer o procesar dispositivo: {e}")

        finally:
            try:
                conn.enable_device()
            except Exception as e:
                logging.error(f"No se pudo habilitar el dispositivo: {e}")
            try:
                conn.disconnect()
            except Exception as e:
                logging.error(f"No se pudo desconectar del dispositivo: {e}")
            logging.info("Desconectado del dispositivo")

    except Exception as e:
        logging.error(f"No se pudo conectar con el dispositivo: {e}")

# ------------------ BUCLE PRINCIPAL ------------------
if __name__ == "__main__":
    logging.info("🚀 Servicio iniciado")
    try:
        while True:
            try:
                procesar_marcaciones()
            except Exception as e:
                logging.exception(f"Error procesando marcaciones: {e}")
            time.sleep(SLEEP_TIME)
    except Exception as e:
        logging.exception(f"Error crítico en el bucle principal: {e}")
        input("Presiona Enter para cerrar...")

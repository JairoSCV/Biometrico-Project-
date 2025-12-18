<?php
require_once __DIR__ . "/zklib/zklib.php";

/* ================= CONFIG ================= */
$DEVICE_IP = "192.168.1.203";
$PORT      = 4370;
$SLEEP     = 30; // segundos

$DB_HOST = "localhost";
$DB_USER = "root";
$DB_PASS = "";
$DB_NAME = "pruebas_marcacion";

$LOG_FILE = __DIR__ . "/marcaciones.log";
/* ========================================== */

function log_msg($msg) {
    global $LOG_FILE;
    $date = date("Y-m-d H:i:s");
    file_put_contents($LOG_FILE, "[$date] $msg\n", FILE_APPEND);
}

log_msg("Servicio iniciado");

while (true) {
    try {
        $zk = new ZKLib($DEVICE_IP, $PORT);

        // MySQL
        $mysqli = new mysqli($DB_HOST, $DB_USER, $DB_PASS, $DB_NAME);
        if ($mysqli->connect_error) {
            throw new Exception("MySQL: " . $mysqli->connect_error);
        }

        if (!$zk->connect()) {
            throw new Exception("No se pudo conectar al biométrico");
        }

        $zk->disableDevice();
        $logs = $zk->getAttendance();

        if (!empty($logs)) {
            foreach ($logs as $log) {
                $dni    = $log['id'];
                $fecha  = date("Y-m-d H:i:s", strtotime($log['timestamp']));
                $evento = $log['type'];

                $stmt = $mysqli->prepare(
                    "INSERT INTO marcaciones (dni, fecha, evento) VALUES (?, ?, ?)"
                );
                $stmt->bind_param("sss", $dni, $fecha, $evento);
                $stmt->execute();
                $stmt->close();
            }

            $zk->clearAttendance();
            log_msg("Marcaciones procesadas: " . count($logs));
        }

        $zk->enableDevice();
        $zk->disconnect();
        $mysqli->close();

    } catch (Exception $e) {
        log_msg("ERROR: " . $e->getMessage());
    }

    sleep($SLEEP);
}

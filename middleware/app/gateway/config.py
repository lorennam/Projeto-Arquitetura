import os

SERVICES = {
    "scheduling": os.getenv("SCHEDULING_URL", "http://scheduling:8001"),
    "medical-record": os.getenv("MEDICAL_RECORD_URL", "http://medical-record:8002"),
    "notification": os.getenv("NOTIFICATION_URL", "http://notification:8003"),
}

REQUEST_TIMEOUT = float(os.getenv("GATEWAY_TIMEOUT_SECONDS", "5"))
CONNECT_TIMEOUT = float(os.getenv("GATEWAY_CONNECT_TIMEOUT_SECONDS", "2"))

MAX_RETRIES = int(os.getenv("GATEWAY_MAX_RETRIES", "3"))
BACKOFF_BASE_SECONDS = float(os.getenv("GATEWAY_BACKOFF_BASE_SECONDS", "0.5"))

CB_FAILURE_THRESHOLD = int(os.getenv("GATEWAY_CB_FAILURE_THRESHOLD", "3"))
CB_RECOVERY_SECONDS = float(os.getenv("GATEWAY_CB_RECOVERY_SECONDS", "10"))
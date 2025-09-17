from dependencies.lora import SX126x

LORA_CFG = {
    "busId": 0,
    "csId": 0,
    "resetPin": 18,
    "busyPin": 20,
    "irqPin": -1,
    "txenPin": -1,
    "rxenPin": -1,
    "frequency": 915_000_000,   # 915 MHz
    "txPower": 22,              # +22 dBm
    "txPowerVersion": SX126x.TX_POWER_SX1262,
    "sf": 7,                    # Spreading factor
    "bw": 125_000,              # 125 kHz
    "cr": 5,                    # coding rate 4/5
    "headerType": SX126x.HEADER_EXPLICIT,
    "preambleLength": 12,
    "payloadLength": 64,        # allow small batches/strings
    "crcType": True,
    "syncWord": 0x34,
}

# ----------------------------
# App parameters
# ----------------------------
CONF_THRESHOLD = 0.70
BATCH_INTERVAL_SEC = 2.0
DEDUP_DISTANCE_M = 10.0                 # do not send multiple detections of same person within 10m
DATA_MAX_AGE_SEC = 5 * 60              # retain last 5 minutes
DATA_MAX_ROWS = 5000                    # hard cap to avoid runaway memory

RELEVANT_CLASSES = {"person"}
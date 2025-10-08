# OnBoardNode/apps/dependencies/lora/secure_sender.py
# Secure LoRa sender: AES-GCM, header(ver,dev_id,ctr), nonce(12B), persistent CTR
import json, time, secrets, struct, os, pathlib
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

DEV_ID    = int(os.getenv("DEV_ID", "7"))
KEY_HEX   = os.getenv("KEY_HEX", "00112233445566778899aabbccddeeff")   # test key (school)
CTR_FILE  = os.getenv("CTR_FILE", "/tmp/tails_ctr.json")               # where we persist CTR

def load_ctr() -> int:
    p = pathlib.Path(CTR_FILE)
    if p.exists():
        try:
            return int(json.loads(p.read_text()).get(str(DEV_ID), 0))
        except Exception:
            pass
    return 0

def save_ctr(ctr: int) -> None:
    p = pathlib.Path(CTR_FILE)
    state = {}
    if p.exists():
        try:
            state = json.loads(p.read_text())
        except Exception:
            state = {}
    state[str(DEV_ID)] = int(ctr)
    p.write_text(json.dumps(state))

def build_secure_frame(dev_id: int, ctr: int, lat: float, lng: float) -> dict:
    key = bytes.fromhex(KEY_HEX)
    aes = AESGCM(key)
    header = struct.pack(">B I I", 1, dev_id, ctr)                     # VER=1
    nonce  = struct.pack(">I I I", dev_id, ctr, secrets.randbits(32))  # 12 bytes
    payload = {"ts": int(time.time()), "lat": lat, "lng": lng}
    ct = aes.encrypt(nonce, json.dumps(payload).encode("utf-8"), header)
    return {"header": header.hex(), "nonce": nonce.hex(), "ciphertext_tag": ct.hex()}

def send_over_lora(frame_json: str) -> bool:
    """
    Plug your existing SX126x driver here (already in the repo).
    Replace the commented lines with the real init/send used on your Pi.
    """
    try:
        import SX126x as sx  # or 'sx126x' depending on your driver module name
        # radio = sx.SX126x(...)                # TODO: init as you already do
        # radio.send_bytes(frame_json.encode()) # or radio.send_string(...)
        print("[LoRa TX] ", frame_json)          # keep a console trace
        return True
    except Exception as e:
        print("[DRY-RUN] Driver not available here:", e)
        print(frame_json)  # still prints JSON so you can test without hardware
        return False

if __name__ == "__main__":
    last_ctr = load_ctr()
    ctr = last_ctr + 1

    # TODO: replace with GPS read on the Pi if you want real coordinates
    lat, lng = 45.4215, -75.6972

    frame = build_secure_frame(DEV_ID, ctr, lat, lng)
    frame_json = json.dumps(frame)

    if send_over_lora(frame_json):
        save_ctr(ctr)
        print(f"[OK] sent (dev_id={DEV_ID}, ctr={ctr})")
    else:
        print(f"[SIM] printed (dev_id={DEV_ID}, ctr={ctr})")

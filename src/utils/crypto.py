import json, struct, os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

#Charger la cle depuis keys.json
def load_key(dev_id: int) -> bytes:
    here = os.path.dirname(__file__)
    with open(os.path.join(here, "keys.json"), "r", encoding="utf-8") as f:
        keys = json.load(f)
    return bytes.fromhex(keys[str(dev_id)])

#Decoder l'entete 
def parse_header(header_bytes: bytes):
    ver, dev_id, ctr = struct.unpack(">B I I", header_bytes)
    return ver, dev_id, ctr


# Chiffrement d'une trame 
def decrypt_frame(header_hex: str, nonce_hex: str, ct_hex: str) -> dict:
    header = bytes.fromhex(header_hex)
    nonce  = bytes.fromhex(nonce_hex)
    ct     = bytes.fromhex(ct_hex)

    ver, dev_id, ctr = parse_header(header)
    key = load_key(dev_id)

    aes = AESGCM(key)
    plaintext = aes.decrypt(nonce, ct, header)   # vérifie automatiquement le TAG
    data = json.loads(plaintext.decode("utf-8"))
    data.update({"dev_id": dev_id, "ctr": ctr, "ver": ver})
    return data
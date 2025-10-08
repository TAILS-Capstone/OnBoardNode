import json, os
STATE_FILE = os.path.join(os.path.dirname(__file__), "last_ctr.json")

def _load():
    if not os.path.exists(STATE_FILE): return {}
    with open(STATE_FILE, "r", encoding="utf-8") as f: return json.load(f)

def _save(st):
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f: json.dump(st, f)
    os.replace(tmp, STATE_FILE)

def check_and_update(dev_id: int, ctr: int) -> bool:
    st = _load()
    last = st.get(str(dev_id), -1)
    if ctr <= last:  # refuse les CTR non strictement croissants
        return False
    st[str(dev_id)] = ctr
    _save(st)
    return True
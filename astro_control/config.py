"""Simple JSON profile/config persistence."""
import json, os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "astro_config.json")
PROFILE_DIR = os.path.join(os.path.dirname(__file__), "..", "profiles")

os.makedirs(PROFILE_DIR, exist_ok=True)

def load_site():
    if not os.path.exists(CONFIG_PATH):
        return {"lat": 0.0, "lon": 0.0, "profile": "default"}
    try:
        with open(CONFIG_PATH) as f:
            return json.load(f)
    except Exception:
        return {"lat": 0.0, "lon": 0.0, "profile": "default"}

def save_site(data: dict):
    data.setdefault("profile", "default")
    try:
        with open(CONFIG_PATH, "w") as f:
            json.dump(data, f)
    except Exception as e:
        print("[Config] save error:", e)

def save_sequence(name: str, steps: list):
    path = os.path.join(PROFILE_DIR, f"{name}.json")
    try:
        with open(path, "w") as f:
            json.dump({"name": name, "steps": steps}, f)
    except Exception as e:
        print("[Config] seq save error:", e)

def load_sequence(name: str) -> list:
    path = os.path.join(PROFILE_DIR, f"{name}.json")
    if not os.path.exists(path):
        return []
    try:
        with open(path) as f:
            return json.load(f).get("steps", [])
    except Exception:
        return []

def list_profiles():
    try:
        return [f.replace(".json","") for f in os.listdir(PROFILE_DIR) if f.endswith(".json")]
    except Exception:
        return []

import json
from pathlib import Path

_config = None

def load_config(path="config.json"):
    global _config
    if _config is None:
        with open(Path(path), "r", encoding="utf-8") as f:
            _config = json.load(f)
    return _config

def get_config():
    if _config is None:
        raise RuntimeError("Config not loaded. Call load_config() first.")
    return _config

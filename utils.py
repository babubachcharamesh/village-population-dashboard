# utils.py
import json
import hashlib
import os

def hash_password(pwd: str) -> str:
    return hashlib.sha256(pwd.encode()).hexdigest()

def load_json(file_path: str, default=None):
    if default is None:
        default = {}
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return json.load(f)
    return default

def save_json(data, file_path: str):
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)

def log_user_action(username: str, action: str, details=None):
    from datetime import datetime
    from config import LOG_FILE
    
    entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user": username,
        "action": action,
        "details": str(details) if details else ""
    }
    
    # Append-only (NDJSON format)
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")

def delete_log_entries(entries_to_delete: list):
    """
    Delete specific entries from the log file.
    
    :param entries_to_delete: List of dictionary entries to remove.
    """
    from config import LOG_FILE
    
    if not os.path.exists(LOG_FILE):
        return

    # 1. Read all logs
    all_logs = []
    with open(LOG_FILE, "r") as f:
        for line in f:
            if line.strip():
                try:
                    all_logs.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    
    # 2. Filter out deleted logs
    # Using JSON string representation for easy comparison
    del_set = {json.dumps(e, sort_keys=True) for e in entries_to_delete}
    
    new_logs = [e for e in all_logs if json.dumps(e, sort_keys=True) not in del_set]
    
    # 3. Rewrite file
    with open(LOG_FILE, "w") as f:
        for entry in new_logs:
            f.write(json.dumps(entry) + "\n")
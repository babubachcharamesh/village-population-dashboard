# config.py
import os

BASE_EXCEL = "FINAL_POPULATION.xlsx"
BASE_PARQUET = "base_population.parquet"
USER_FILE = "users.json"
HISTORY_FILE = "user_history.json"
LOG_FILE = "logs.json"

MIN_VILLAGES = 28
MAX_VILLAGES = 280

# Ensure required files exist (for base data)
if not os.path.exists(BASE_EXCEL):
    raise FileNotFoundError(f"Required file '{BASE_EXCEL}' not found!")
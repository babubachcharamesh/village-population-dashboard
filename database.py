# database.py
import streamlit as st
import duckdb
import pandas as pd
import uuid
import os
from datetime import datetime

from config import BASE_EXCEL, BASE_PARQUET, HISTORY_FILE
from utils import load_json, save_json, log_user_action
from pop_utils import get_marriage_to_village_id

@st.cache_data(ttl=3600)
def load_base_data():
    """Load the base data, converting to Parquet if needed for speed."""
    if not os.path.exists(BASE_PARQUET):
        if not os.path.exists(BASE_EXCEL):
            raise FileNotFoundError(f"Missing base file: {BASE_EXCEL}")
        
        # One-time conversion
        df = pd.read_excel(BASE_EXCEL, sheet_name="FINAL_POPULATION")
        
        # Pre-calculate birth dates once
        df["BIRTH_DATE_SERIAL"] = df["BIRTH_DATE"].apply(
            lambda x: (pd.to_datetime(x, errors='coerce') - pd.Timestamp("1899-12-30")).days
            if pd.notna(x) else None
        )
        df["Date_of_Birth"] = df["BIRTH_DATE_SERIAL"].apply(
            lambda x: (pd.Timestamp("1899-12-30") + pd.Timedelta(days=int(x))).strftime("%A, %B %d, %Y")
            if pd.notna(x) else None
        )
        
        df.to_parquet(BASE_PARQUET)
    
    return pd.read_parquet(BASE_PARQUET)

def generate_database(num_villages: int):
    """Generate a new DuckDB database for the current user using optimized vector operations."""
    username = st.session_state.username
    db_id = str(uuid.uuid4())[:8]
    db_path = f"villages_{username}_{db_id}.db"

    # Remove old file if exists
    if os.path.exists(db_path):
        os.remove(db_path)

    with st.spinner("Generating population database (optimized)..."):
        # Load optimized base data
        base_df = load_base_data()
        base_count = len(base_df)
        
        # Connect to DuckDB
        con = duckdb.connect(db_path)
        
        # Register the base dataframe
        con.register("base_df", base_df)
        
        # Create UDF for marriage mapping
        con.create_function("get_marriage_id", get_marriage_to_village_id, return_type="BIGINT", parameters=["BIGINT", "BIGINT"])
        
        # Create sequence and table
        con.execute("CREATE SEQUENCE seq START 1")
        con.execute("""
            CREATE TABLE population (
                SERIAL_NO INTEGER DEFAULT nextval('seq') PRIMARY KEY,
                COUNTER INTEGER,
                FAMILY_ID INTEGER,
                PERSON_ID INTEGER,
                BIRTH_DATE INTEGER,
                VILLAGE_ID INTEGER,
                GENDER VARCHAR,
                Date_of_Birth VARCHAR,
                MARRIED_TO_VILLAGE_ID INTEGER
            )
        """)
        
        # Optimized SQL Generation
        # 1. Generate villages sequence
        # 2. Cross join with base data
        # 3. Calculate fields in SQL/UDF
        
        # Logic for GENDER:
        # "MALE" if (i % 2 == 0) == (vid % 2 == 1) else "FEMALE"
        # i is row index within village. In base_df, we can rely on implicit row order or add a row_number.
        # Let's add row_number to base_df via SQL
        
        query = f"""
            INSERT INTO population (
                COUNTER, FAMILY_ID, PERSON_ID, BIRTH_DATE, 
                VILLAGE_ID, GENDER, Date_of_Birth, MARRIED_TO_VILLAGE_ID
            )
            WITH base_with_idx AS (
                SELECT *, row_number() OVER () - 1 as idx FROM base_df
            ),
            villages AS (
                SELECT range as vid FROM range(1, {num_villages} + 1)
            )
            SELECT 
                b.COUNTER, 
                b.FAMILY_ID, 
                b.PERSON_ID, 
                b.BIRTH_DATE_SERIAL as BIRTH_DATE,
                v.vid as VILLAGE_ID,
                CASE 
                    WHEN ((b.idx % 2 = 0) = (v.vid % 2 = 1)) THEN 'MALE' 
                    ELSE 'FEMALE' 
                END as GENDER,
                b.Date_of_Birth,
                get_marriage_id(v.vid, b.COUNTER) as MARRIED_TO_VILLAGE_ID
            FROM villages v, base_with_idx b
            ORDER BY v.vid, b.idx
        """
        
        con.execute(query)
        con.execute("CREATE INDEX idx_village ON population(VILLAGE_ID)")
        
        # Get actual count
        total_records = con.execute("SELECT COUNT(*) FROM population").fetchone()[0]
        con.close()

    # Update session state
    st.session_state.update(
        db_path=db_path,
        db_generated=True,
        db_version=st.session_state.db_version + 1,
        num_villages=num_villages,
        db_id=db_id
    )

    # Save to user history
    history = load_json(HISTORY_FILE)
    history.setdefault(username, []).append({
        "db_id": db_id,
        "db_path": db_path,
        "num_villages": num_villages,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    save_json(history, HISTORY_FILE)
    st.session_state.history = history
    
    # Log Action
    log_user_action(username, "GENERATE_DB", f"Created database with {num_villages} villages, {total_records:,} records")

    # Final success message + download button
    st.success(f"Database created: `{db_path}` – {total_records:,} records")
    st.balloons()
    with open(db_path, "rb") as f:
        st.download_button("Download Database", f.read(), db_path, key="download_new_db")

def load_db_from_history(path: str):
    """Load a previously generated database from file path (called when user selects from history)."""
    if os.path.exists(path):
        st.session_state.db_path = path
        st.session_state.db_generated = True
        st.session_state.db_version += 1  # Trigger cache invalidation for visualizations
        st.sidebar.success(f"Loaded database: {os.path.basename(path)}")
    else:
        st.sidebar.error("Database file not found! Removing from history...")
        username = st.session_state.username
        history = load_json(HISTORY_FILE)
        if username in history:
            history[username] = [e for e in history[username] if e["db_path"] != path]
            save_json(history, HISTORY_FILE)
            st.session_state.history = history
        st.rerun()
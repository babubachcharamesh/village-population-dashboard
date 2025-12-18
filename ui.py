import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import json

from database import generate_database, load_base_data
from config import MIN_VILLAGES, MAX_VILLAGES, HISTORY_FILE, LOG_FILE
from utils import load_json, log_user_action

def render_sidebar():
    """Render the main sidebar with navigation buttons."""
    with st.sidebar:
        st.success(f"Logged in: **{st.session_state.username}**")
        
        if st.button("Change Password"):
            st.session_state.show_change_password = True
            st.rerun()
        
        if st.session_state.username == "admin":
            if st.button("Manage Users"):
                st.session_state.show_user_manager = True
                st.rerun()
        
        if st.button("My Database History"):
            st.session_state.show_history = True
            st.rerun()
            
        if st.button("Activity Logs"):
            st.session_state.show_activity_log = True
            st.rerun()
        
        st.markdown("---")
        if st.button("Logout"):
            log_user_action(st.session_state.username, "LOGOUT", "User logged out")
            # Clear all session state except users and history
            keys_to_keep = ["users", "history"]
            for key in list(st.session_state.keys()):
                if key not in keys_to_keep:
                    del st.session_state[key]
            st.session_state.authenticated = False
            st.session_state.username = None
            st.rerun()

def activity_log_page():
    """Display activity logs with delete option."""
    st.title("Activity Logs")
    
    # Load logs
    logs = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            for line in f:
                if line.strip():
                    try:
                        logs.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    
    if not logs:
        st.info("No activity recorded yet.")
    else:
        # Filter for non-admin users
        if st.session_state.username != "admin":
            logs = [entry for entry in logs if entry["user"] == st.session_state.username]
            if not logs:
                st.info("No activity found for your account.")
                st.stop() # Use stop to prevent empty dataframe error if needed

        # Prepare for Editor
        # Add a unique key or just rely on row props? Better to just wrap in Pandas
        df_logs = pd.DataFrame(logs)
        # Sort by timestamp descending
        df_logs = df_logs.sort_values(by="timestamp", ascending=False)
        
        # Insert 'Select' column for checkbox
        df_logs.insert(0, "Select", False)
        
        # Display Editor
        edited_df = st.data_editor(
            df_logs,
            column_config={
                "Select": st.column_config.CheckboxColumn(
                    "Select",
                    help="Select rows to delete",
                    default=False,
                )
            },
            hide_index=True,
            use_container_width=True,
            num_rows="fixed",
            key="log_editor"
        )
        
        # Detect Selection
        selected_rows = edited_df[edited_df["Select"] == True]
        
        if not selected_rows.empty:
            if st.button(f"Delete ({len(selected_rows)}) Entries", type="primary"):
                # Convert back to dict list for utility
                # Drop 'Select' column
                to_delete = selected_rows.drop(columns=["Select"]).to_dict("records")
                
                from utils import delete_log_entries
                delete_log_entries(to_delete)
                
                st.success(f"Deleted {len(to_delete)} entries.")
                st.rerun()

    if st.button("Back to Dashboard"):
        st.session_state.show_activity_log = False
        st.rerun()

def history_page():
    """Display the user's database history with download options."""
    st.title("My Database History")
    user_hist = st.session_state.history.get(st.session_state.username, [])
    
    if not user_hist:
        st.info("No databases created yet.")
    else:
        # Sort by most recent first
        for entry in sorted(user_hist, key=lambda x: x["created_at"], reverse=True):
            with st.expander(f"{entry['db_id']} • {entry['num_villages']} villages • {entry['created_at']}"):
                st.write(f"**File:** `{entry['db_path']}`")
                if os.path.exists(entry["db_path"]):
                    with open(entry["db_path"], "rb") as f:
                        st.download_button(
                            label="Download Database",
                            data=f.read(),
                            file_name=os.path.basename(entry["db_path"]),
                            mime="application/octet-stream",
                            key=f"hist_dl_{entry['db_id']}"
                        )
                else:
                    st.warning("File not found (may have been deleted externally)")

    if st.button("Back to Dashboard"):
        st.session_state.show_history = False
        st.rerun()

def main_tabs():
    """Main content with three tabs: Generate DB/Select DB, SQL Explorer, Visualizations."""
    df_base = load_base_data()
    st.success(f"Base records loaded: {len(df_base):,} people")

    # Determine tab title based on role
    is_admin = st.session_state.username == "admin"
    tab1_title = "Generate DB" if is_admin else "Select Database"
    
    tab1, tab2, tab3 = st.tabs([tab1_title, "SQL Explorer", "Visualizations"])

    # ======================== TAB 1: Generate DB (Admin) / Select DB (User) ========================
    with tab1:
        if is_admin:
            st.header("Generate New Database")
            num = st.number_input(
                "Number of villages (must be multiple of 28)",
                min_value=MIN_VILLAGES,
                max_value=MAX_VILLAGES,
                value=st.session_state.get("num_villages", MIN_VILLAGES),
                step=28,
                key="num_villages_input"
            )

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Generate Database", type="primary"):
                    if num % 28 != 0:
                        st.error("Number of villages must be a multiple of 28!")
                    else:
                        generate_database(num)
            with col2:
                if st.button("Regenerate (Same Size)"):
                    if num % 28 != 0:
                        st.error("Number of villages must be a multiple of 28!")
                    else:
                        generate_database(num)
        else:
            st.header("Select Database")
            st.info("Select a database generated by the Administrator.")
            
            # Load admin's history
            from config import HISTORY_FILE
            from utils import load_json
            
            history = load_json(HISTORY_FILE)
            admin_dbs = history.get("admin", [])
            
            if not admin_dbs:
                st.warning("No databases found from Admin. Please contact the administrator.")
            else:
                # Create a readable list for the selectbox
                # Format: "ID (Date) - N Villages"
                db_options = {
                    f"{d['db_id']} ({d['created_at']}) - {d['num_villages']} Villages": d 
                    for d in sorted(admin_dbs, key=lambda x: x["created_at"], reverse=True)
                }
                
                selected_label = st.selectbox("Available Databases", list(db_options.keys()))
                
                if st.button("Load Database", type="primary"):
                    selected_db = db_options[selected_label]
                    db_path = selected_db["db_path"]
                    
                    if os.path.exists(db_path):
                        st.session_state.update(
                            db_path=db_path,
                            db_generated=True,
                            db_version=st.session_state.get("db_version", 0) + 1,
                            num_villages=selected_db["num_villages"],
                            db_id=selected_db["db_id"]
                        )
                        log_user_action(st.session_state.username, "LOAD_DB", f"Loaded database: {db_path}")
                        st.success(f"Loaded database: {db_path}")
                        st.rerun()
                    else:
                        st.error("Database file not found on server.")

    # ======================== TAB 2: SQL Explorer ========================
    with tab2:
        st.header("SQL Explorer")
        if not st.session_state.get("db_generated", False):
            st.info("Please generate or load a database first.")
        else:
            # Optional schema upgrade for older databases
            try:
                con = duckdb.connect(st.session_state.db_path)
                cols = [row[1] for row in con.execute("PRAGMA table_info(population)").fetchall()]
                if "MARRIED_TO_VILLAGE_ID" not in cols:
                    con.execute("ALTER TABLE population ADD COLUMN MARRIED_TO_VILLAGE_ID INTEGER")
                    st.info("Added missing column: MARRIED_TO_VILLAGE_ID")
                con.close()
            except Exception as e:
                st.warning("Could not check/upgrade schema (continuing anyway)")

            # Get total record count safely
            try:
                con = duckdb.connect(st.session_state.db_path, read_only=True)
                total_row = con.execute("SELECT COUNT(*) FROM population").fetchone()
                total = total_row[0] if total_row else 0
                con.close()
            except Exception as e:
                st.error("Error reading database")
                st.code(str(e))
                total = 0

            st.write(f"**Total records:** {total:,}")

            # Example queries (you can expand this dict as needed)
            examples = {
                "First 20 people": "SELECT * FROM population LIMIT 20",
                "Total population": "SELECT COUNT(*) AS total FROM population",
                "Villages count": "SELECT COUNT(DISTINCT VILLAGE_ID) AS villages FROM population",
                "People per village": "SELECT VILLAGE_ID, COUNT(*) AS residents FROM population GROUP BY VILLAGE_ID ORDER BY VILLAGE_ID",
                "Gender ratio": "SELECT GENDER, COUNT(*) AS count FROM population GROUP BY GENDER",
                "Born on Monday": "SELECT COUNT(*) FROM population WHERE Date_of_Birth LIKE 'Monday%'",
                "Random 10 people": "SELECT * FROM population USING SAMPLE 10"
                # Add more of your original examples here
            }

            choice = st.selectbox("Quick Examples", ["Custom"] + list(examples.keys()))
            default_sql = examples.get(choice, "") if choice != "Custom" else ""
            sql = st.text_area("Enter SQL Query", value=default_sql, height=200)

            if st.button("Run Query", type="primary") and sql.strip():
                try:
                    con = duckdb.connect(st.session_state.db_path, read_only=True)
                    result_df = con.execute(sql).fetchdf()
                    con.close()
                    
                    # Display limit logic
                    if len(result_df) > 1000:
                        st.warning(f"Query returned {len(result_df):,} rows. Displaying first 1,000 only.")
                        st.dataframe(result_df.head(1000), use_container_width=True)
                    else:
                        st.dataframe(result_df, use_container_width=True)
                    
                    log_user_action(st.session_state.username, "RUN_QUERY", f"SQL: {sql[:50]}...")
                    
                    csv = result_df.to_csv(index=False).encode()
                    st.download_button("Download Full CSV", csv, "query_result.csv", "text/csv")
                except Exception as e:
                    st.error("SQL Error")
                    st.code(str(e))

    # ======================== TAB 3: Visualizations ========================
    with tab3:
        st.header("Visualizations (Optimized)")
        if not st.session_state.get("db_generated", False):
            st.warning("Generate or load a database first.")
        else:
            con = duckdb.connect(st.session_state.db_path, read_only=True)
            
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Population per Village")
                df_vol = con.execute("SELECT VILLAGE_ID, COUNT(*) as Population FROM population GROUP BY VILLAGE_ID ORDER BY VILLAGE_ID").fetchdf()
                fig1 = px.bar(df_vol, x="VILLAGE_ID", y="Population")
                st.plotly_chart(fig1, use_container_width=True)

                st.subheader("Overall Gender Ratio")
                df_gen = con.execute("SELECT GENDER, COUNT(*) as Count FROM population GROUP BY GENDER").fetchdf()
                fig2 = px.pie(df_gen, names="GENDER", values="Count", hole=0.4, color_discrete_sequence=["lightblue", "pink"])
                st.plotly_chart(fig2, use_container_width=True)

            with col2:
                st.subheader("Gender Distribution per Village")
                # SQL Based Pivot-ish query
                df_gen_vil = con.execute("""
                    SELECT VILLAGE_ID, GENDER, COUNT(*) as Count 
                    FROM population 
                    GROUP BY VILLAGE_ID, GENDER 
                    ORDER BY VILLAGE_ID
                """).fetchdf()
                
                # Transform for plotting (simple pivot in pandas is fast for 560 rows)
                gv = df_gen_vil.pivot(index="VILLAGE_ID", columns="GENDER", values="Count").fillna(0)
                
                fig3 = go.Figure()
                fig3.add_trace(go.Bar(name="Male", x=gv.index, y=gv.get("MALE", []), marker_color="lightblue"))
                fig3.add_trace(go.Bar(name="Female", x=gv.index, y=gv.get("FEMALE", []), marker_color="pink"))
                fig3.update_layout(barmode="stack", title="Males & Females per Village")
                st.plotly_chart(fig3, use_container_width=True)

                st.subheader("Births by Day of Week")
                # Using string split to get Day (Format: "Monday, January 1, 2000")
                # str_split returns a list, indexes are 1-based in DuckDB
                df_day = con.execute("""
                    SELECT str_split(Date_of_Birth, ', ')[1] as Day, COUNT(*) as Count 
                    FROM population 
                    GROUP BY 1
                """).fetchdf()
                
                order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                # Use pandas categorical sort for small dataset (7 rows)
                df_day["Day"] = pd.Categorical(df_day["Day"], categories=order, ordered=True)
                df_day = df_day.sort_values("Day")
                
                fig4 = px.bar(df_day, x="Day", y="Count")
                st.plotly_chart(fig4, use_container_width=True)
            
            con.close()

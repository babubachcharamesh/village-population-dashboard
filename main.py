# main.py - Entry point
import streamlit as st
from utils import load_json
from config import USER_FILE, HISTORY_FILE
from auth import login_page, change_password_page, user_management_page
from ui import render_sidebar, history_page, main_tabs, activity_log_page
from database import load_db_from_history

def main():
    st.session_state.users = load_json(USER_FILE)
    st.session_state.history = load_json(HISTORY_FILE)

    if not st.session_state.get("authenticated", False):
        login_page()
        st.stop()

    if st.session_state.get("show_change_password"):
        change_password_page()
        st.stop()

    if st.session_state.get("show_user_manager"):
        user_management_page()
        st.stop()

    if st.session_state.get("show_history"):
        history_page()
        st.stop()

    if st.session_state.get("show_activity_log"):
        activity_log_page()
        st.stop()

    # Main dashboard
    st.set_page_config(page_title="Village Dashboard", layout="wide")
    st.title("Village Population Analytics Dashboard")
    st.caption(f"User: **{st.session_state.username}**")

    render_sidebar()

    # Session defaults
    for k, v in {"num_villages": 28, "db_generated": False, "db_version": 0, "db_id": None, "db_path": None}.items():
        st.session_state.setdefault(k, v)

    # History loader
    user_hist = st.session_state.history.get(st.session_state.username, [])
    if user_hist:
        opts = {f"{e['db_id']} ({e['num_villages']} vil, {e['created_at']})": e["db_path"] for e in user_hist}
        selected = st.sidebar.selectbox("Load Previous", ["New"] + list(opts.keys()))
        if selected != "New":
            load_db_from_history(opts[selected])

    main_tabs()

if __name__ == "__main__":
    main()
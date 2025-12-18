# auth.py
import streamlit as st
from utils import hash_password, load_json, save_json, log_user_action
from config import USER_FILE, HISTORY_FILE
import re

def login_page():
    st.set_page_config(page_title="Login")
    st.title("Village Population Analytics Dashboard")
    st.markdown("### Login Required")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login", type="primary"):
        users = load_json(USER_FILE)
        if username in users and users[username] == hash_password(password):
            st.session_state.authenticated = True
            st.session_state.username = username
            log_user_action(username, "LOGIN", "Login successful")
            st.success("Login successful!")
            st.rerun()
        else:
            log_user_action(username, "LOGIN_FAIL", "Invalid username or password")
            st.error("Invalid username or password")

    with st.expander("First-time setup"):
        st.info("Admin must create the first user via user management after manually creating users.json.")

def change_password_page():
    st.title("Change Password")
    user = st.session_state.username
    users = load_json(USER_FILE)

    with st.form("change_pwd"):
        st.write(f"Updating password for **{user}**")
        old = st.text_input("Current Password", type="password")
        new = st.text_input("New Password", type="password")
        confirm = st.text_input("Confirm New Password", type="password")
        submitted = st.form_submit_button("Update")

        if submitted:
            if hash_password(old) != users[user]:
                st.error("Current password incorrect")
            elif new != confirm:
                st.error("Passwords do not match")
            elif len(new) < 8:
                st.error("Password must be at least 8 characters")
            elif not (re.search(r"[A-Za-z]", new) and re.search(r"[0-9]", new)):
                st.error("Password must contain letters and numbers")
            else:
                users[user] = hash_password(new)
                save_json(users, USER_FILE)
                log_user_action(user, "PASSWORD_CHANGE", "Password updated successfully")
                st.success("Password changed successfully!")
                st.balloons()
                st.session_state.show_change_password = False
                st.rerun()

    if st.button("Cancel"):
        st.session_state.show_change_password = False
        st.rerun()

def user_management_page():
    st.title("User Management (Admin Only)")
    users = load_json(USER_FILE).copy()
    history = load_json(HISTORY_FILE)

    for user in list(users.keys()):
        c1, c2, c3 = st.columns([3, 2, 1])
        c1.write(f"**{user}**")
        if user != "admin":
            if c3.button("Delete", key=f"del_{user}"):
                users.pop(user)
                history.pop(user, None)
                save_json(users, USER_FILE)
                save_json(history, HISTORY_FILE)
                log_user_action(st.session_state.username, "USER_DELETE", f"Deleted user: {user}")
                st.success(f"User `{user}` deleted")
                st.rerun()
        else:
            c2.write("(protected)")

    st.markdown("---")
    st.subheader("Add New User")
    with st.form("add_user"):
        new_u = st.text_input("Username")
        new_p = st.text_input("Password", type="password")
        new_p2 = st.text_input("Confirm Password", type="password")
        if st.form_submit_button("Create"):
            if not new_u or not new_p:
                st.error("All fields required")
            elif new_u in users:
                st.error("Username exists")
            elif new_p != new_p2:
                st.error("Passwords mismatch")
            elif len(new_p) < 8:
                st.error("Password too short")
            elif not (re.search(r"[A-Za-z]", new_p) and re.search(r"[0-9]", new_p)):
                st.error("Needs letters + numbers")
            else:
                users[new_u] = hash_password(new_p)
                save_json(users, USER_FILE)
                log_user_action(st.session_state.username, "USER_CREATE", f"Created user: {new_u}")
                st.success(f"User `{new_u}` created!")
                st.balloons()

    if st.button("Back"):
        st.session_state.show_user_manager = False
        st.rerun()

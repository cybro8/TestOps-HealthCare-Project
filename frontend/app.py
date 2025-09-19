import streamlit as st
import requests
import os

# ---------- Backend API ----------
API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="Auth Frontend", layout="wide")


# ---------- Login Page ----------
def login_page():
    st.title("🔐 Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login", use_container_width=True):
        resp = requests.post(f"{API_URL}/token", data={"username": username, "password": password})
        if resp.status_code == 200:
            token = resp.json()["access_token"]
            st.session_state["token"] = token
            st.session_state["username"] = username

            # Fetch current user
            headers = {"Authorization": f"Bearer {token}"}
            me = requests.get(f"{API_URL}/me", headers=headers)
            if me.status_code == 200:
                st.session_state["role"] = me.json().get("role", "user")
                st.success("✅ Login successful")
                st.rerun()
            else:
                st.error("Failed to fetch user info")
        else:
            st.error("❌ Invalid credentials")


# ---------- Admin Dashboard ----------
def admin_dashboard():
    st.title("🛠️ Admin Dashboard")
    token = st.session_state.get("token")
    headers = {"Authorization": f"Bearer {token}"}

    # Sidebar menu
    menu = st.sidebar.selectbox("📌 Menu", ["Users", "Project Configuration"])

    if menu == "Users":
        st.subheader("👥 Manage Users")

        if st.button("🔄 Refresh users", use_container_width=True):
            r = requests.get(f"{API_URL}/users", headers=headers)
            if r.status_code == 200:
                st.session_state["users"] = r.json()
            else:
                st.error("Failed to fetch users")

        users = st.session_state.get("users", [])
        if not users:
            st.info("No users found. Click refresh to load.")
        else:
            for u in users:
                with st.container():
                    st.markdown(f"**{u['username']}** ({u['role']}) — ID: {u['id']}")
                    cols = st.columns([2, 1, 1])

                    with cols[0]:
                        new_pw = st.text_input(f"New password", key=f"pw_{u['id']}")

                    with cols[1]:
                        if st.button("Update", key=f"upd_{u['id']}"):
                            payload = {"username": u['username'], "password": new_pw or "", "role": u['role']}
                            r = requests.put(f"{API_URL}/users/{u['id']}", json=payload, headers=headers)
                            if r.status_code == 200:
                                st.success("✅ Updated")
                            else:
                                st.error("❌ Failed to update")

                    with cols[2]:
                        if st.button("Delete", key=f"del_{u['id']}"):
                            r = requests.delete(f"{API_URL}/users/{u['id']}", headers=headers)
                            if r.status_code == 200:
                                st.success("🗑️ Deleted")
                                st.rerun()
                            else:
                                st.error("❌ Failed to delete")

        st.markdown("---")
        st.subheader("➕ Create new user")

        new_username = st.text_input("Username", key="create_user_name")
        new_password = st.text_input("Password", type="password", key="create_user_pw")
        new_role = st.selectbox("Role", ["user", "editor", "viewer"], key="create_user_role")

        if st.button("Create user", use_container_width=True):
            payload = {"username": new_username, "password": new_password, "role": new_role}
            r = requests.post(f"{API_URL}/users", json=payload, headers=headers)
            if r.status_code in (200, 201):
                st.success("✅ User created")
                st.rerun()
            else:
                st.error(r.text)

    elif menu == "Project Configuration":
        st.subheader("⚙️ Project Configuration")

        with st.form("project_config_form", clear_on_submit=True):
            project_name = st.text_input("Project Name")
            description = st.text_area("Project Description")
            environment = st.selectbox("Environment", ["Development", "Staging", "Production"])

            submitted = st.form_submit_button("💾 Save Configuration")
            if submitted:
                st.success(f"✅ Configuration saved: {project_name} ({environment})")
                # Later: POST this to backend


# ---------- User Dashboard (Healthcare Test Case Generator) ----------
def user_dashboard():
    import google.generativeai as genai
    import fitz  # PyMuPDF
    import docx  # python-docx
    import pandas as pd
    import re
    from config import GENAI_API_KEY

    # Setup Gemini with API Key
    genai.configure(api_key=GENAI_API_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")

    st.title("🏥 Healthcare Test Case Generator")

    uploaded_file = st.file_uploader("Upload a file", type=["pdf", "docx", "md"])

    def extract_text(file, ftype):
        if ftype == "pdf":
            doc = fitz.open(stream=file.read(), filetype="pdf")
            return "".join([page.get_text("text") for page in doc])
        elif ftype == "docx":
            doc = docx.Document(file)
            return "\n".join([p.text for p in doc.paragraphs])
        elif ftype == "md":
            return file.read().decode("utf-8")
        return ""

    if uploaded_file:
        ftype = uploaded_file.name.split(".")[-1].lower()
        st.session_state["doc_content"] = extract_text(uploaded_file, ftype)
        st.success(f"✅ {uploaded_file.name} uploaded and processed!")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    def parse_test_cases(response_text):
        pattern = r"Test Case ID:(.*?)\nDescription:(.*?)\nSteps:(.*?)\nExpected Result:(.*?)\nPriority:(.*?)\n"
        matches = re.findall(pattern, response_text, re.DOTALL | re.IGNORECASE)
        if not matches:
            return None
        return pd.DataFrame([{
            "Test Case ID": m[0].strip(),
            "Description": m[1].strip(),
            "Steps": m[2].strip(),
            "Expected Result": m[3].strip(),
            "Priority": m[4].strip()
        } for m in matches])

    if prompt := st.chat_input("Ask me something..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        normalized_prompt = prompt.lower().strip()
        greetings = ["hi", "hello", "hey", "what are you", "who are you", "what do you do"]

        if normalized_prompt in greetings:
            intro_message = (
                "👋 Hi! I am a **Test Case Generator for Healthcare Applications**. "
                "Upload requirements (PDF, DOCX, or Markdown), and I’ll generate structured test cases."
            )
            with st.chat_message("assistant"):
                st.markdown(intro_message)
            st.session_state.messages.append({"role": "assistant", "content": intro_message})

        elif "test case" not in normalized_prompt and "healthcare" not in normalized_prompt:
            restricted_reply = (
                "⚠️ I am a **Test Case Generator for Healthcare Applications**. "
                "I cannot answer questions outside this domain."
            )
            with st.chat_message("assistant"):
                st.markdown(restricted_reply)
            st.session_state.messages.append({"role": "assistant", "content": restricted_reply})

        else:
            if "doc_content" in st.session_state:
                full_prompt = f"""
                You are an AI specialized in generating **structured test cases for Healthcare Applications**.
                Generate test cases in the following format exactly:

                Test Case ID:
                Description:
                Steps:
                Expected Result:
                Priority:

                Use the following document content to create test cases:

                {st.session_state['doc_content'][:20000]}

                User Query: {prompt}
                """
            else:
                full_prompt = f"""
                You are an AI specialized in generating **structured test cases for Healthcare Applications**.
                Generate test cases in the following format exactly:

                Test Case ID:
                Description:
                Steps:
                Expected Result:
                Priority:

                User Query: {prompt}
                """

            with st.chat_message("assistant"):
                with st.spinner("🤖 Generating structured test cases..."):
                    response = model.generate_content(full_prompt)

                df = parse_test_cases(response.text)
                if df is not None and not df.empty:
                    st.table(df)
                else:
                    st.markdown(response.text)

            st.session_state.messages.append({"role": "assistant", "content": response.text})


# ---------- Main Router ----------
def main():
    if "token" not in st.session_state:
        login_page()
    else:
        role = st.session_state.get("role", "user")
        if role == "admin":
            admin_dashboard()
        else:
            user_dashboard()

        # Single Logout Button
        if st.sidebar.button("🚪 Logout"):
            st.session_state.clear()
            st.rerun()


if __name__ == "__main__":
    main()

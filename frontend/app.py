import streamlit as st
import requests
import os ,json

# ---------- Backend API ----------
API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="Auth Frontend", layout="wide")

# --- Global Button CSS (Teal buttons) ---
# (This will apply to all buttons in the app)
st.markdown("""
<style>
    div[data-testid="stButton"] > button {
        background-color: #008B9B; /* Your requested color */
        color: #FFFFFF; /* White text for better contrast */
        border: 1px solid #008B9B;
    }
    div[data-testid="stButton"] > button:hover {
        background-color: #009DAC; /* Lighter shade for hover */
        color: #FFFFFF;
        border: 1px solid #009DAC;
    }
    div[data-testid="stButton"] > button:active {
        background-color: #007B8A; /* Darker shade for active */
        color: #FFFFFF;
    }
    /* --- Sidebar styles --- */
    [data-testid="stSidebar"] > div:first-child {
        background-color: #333333; /* Dark Grey */
    }
    [data-testid="stSidebar"] .stMarkdown p, 
    [data-testid="stSidebar"] .stSelectbox > label,
    [data-testid="stSidebar"] .stButton > button p {
        color: #FFFFFF; /* White text */
    }
</style>
""", unsafe_allow_html=True)
# --- END CSS ---


# ---------- Login Page (MODIFIED) ----------
def login_page():
    
    # --- MODIFIED: Use columns to create a centered, narrower layout ---
    # This provides some structure without the box
    _ , col_center, _ = st.columns([1, 1.2, 1])

    with col_center:
        st.title("Login")
        
        username = st.text_input("Username:", placeholder="Enter username", label_visibility="visible") 
        password = st.text_input("Password:", placeholder="Enter password", type="password", label_visibility="visible")
        
        st.markdown("<br>", unsafe_allow_html=True) # Add some space
        
        if st.button("SIGN IN", use_container_width=True):
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
    # --- END MODIFICATION ---


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
                with st.expander(f"**{u['username']}** ({u['role']}) — ID: {u['id']}"):
                    
                    col1, col2 = st.columns([2, 1]) 

                    with col1:
                        st.subheader("Update Password")
                        with st.form(key=f"update_form_{u['id']}"):
                            new_pw = st.text_input(f"New password for {u['username']}", type="password", key=f"pw_{u['id']}")
                            submitted = st.form_submit_button("Update")
                            
                            if submitted:
                                if not new_pw:
                                    st.error("Password cannot be empty.")
                                else:
                                    payload = {"username": u['username'], "password": new_pw, "role": u['role']}
                                    r = requests.put(f"{API_URL}/users/{u['id']}", json=payload, headers=headers)
                                    if r.status_code == 200:
                                        st.success(f"✅ Password for {u['username']} updated")
                                    else:
                                        st.error(f"❌ Failed to update: {r.text}")
                    
                    with col2:
                        st.subheader("Delete User")
                        st.warning("This action is permanent.")
                        if st.button("🗑️ Delete this user", key=f"del_{u['id']}", use_container_width=True, type="primary"):
                            if u['username'] == st.session_state.get("username"):
                                st.error("You cannot delete your own account.")
                            else:
                                r = requests.delete(f"{API_URL}/users/{u['id']}", headers=headers)
                                if r.status_code == 200:
                                    st.success(f"🗑️ User {u['username']} deleted")
                                    st.rerun()
                                else:
                                    st.error(f"❌ Failed to delete: {r.text}")

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

        with st.expander("➕ Add New Project", expanded=True):
            with st.form("project_config_form", clear_on_submit=True):

                project_name = st.text_input("Project Name")
                description = st.text_area("Project Description")
                
                tool = st.selectbox("Tool", ["Azure DevOps", "Jira"])
                
                azure_org = st.text_input("Azure Org Name")
                azure_project = st.text_input("Azure Project Name")
                azure_pat = st.text_input("Azure PAT", type="password")

                try:
                    _users_resp = requests.get(f"{API_URL}/users", headers=headers)
                    all_users = _users_resp.json() if _users_resp.status_code == 200 else []
                except Exception:
                    all_users = []

                user_options = {u['username']: u['id'] for u in all_users}
                assigned_usernames = st.multiselect("Assign Users (optional)", list(user_options.keys()))

                submitted = st.form_submit_button("💾 Save Project")

                if submitted:
                    payload = {
                        "name": project_name,
                        "description": description,
                        "organization": azure_org,
                        "pat": azure_pat,
                        "iteration_path": "",
                        "area_path": "",
                        "api_version": "7.0",
                        "chat_history": []
                    }

                    r = requests.post(f"{API_URL}/projects", json=payload, headers=headers)

                    if r.status_code in (200, 201):
                        st.success(f"✅ Project '{project_name}' saved")
                        if assigned_usernames:
                            user_ids = [user_options[n] for n in assigned_usernames]
                            assign_payload = {"user_ids": user_ids}
                            ar = requests.post(f"{API_URL}/projects/{r.json().get('id')}/users/assign",
                                               json=assign_payload, headers=headers)
                            if ar.status_code == 200:
                                st.success("✅ Users assigned to project")
                            else:
                                st.error(f"❌ Failed to assign users: {ar.text}")
                        st.rerun()
                    else:
                        st.error(f"❌ Failed to save project: {r.text}")

    st.markdown("### 📋 Existing Projects")
    r = requests.get(f"{API_URL}/projects/", headers=headers)
    if r.status_code == 200:
        projects = r.json()
    else:
        projects = []
        st.error("❌ Failed to fetch projects")

    if not projects:
        st.info("No projects found. Add one above.")
    else:
        users_resp = requests.get(f"{API_URL}/users", headers=headers)
        all_users = users_resp.json() if users_resp.status_code == 200 else []

        for p in projects:
            with st.expander(f"📂 {p['name']} — Org: {p.get('organization', '')}", expanded=False):
                st.caption(p.get("description", ""))
                st.markdown("📑 **Compliance Files**")

                if f"uploaded_file_{p['id']}" not in st.session_state:
                    st.session_state[f"uploaded_file_{p['id']}"] = None

                uploaded_file = st.file_uploader(
                    f"Upload file for {p['name']}",
                    type=["pdf", "docx", "md", "txt"],
                    key=f"file_uploader_{p['id']}"
                )

                if uploaded_file:
                    st.session_state[f"uploaded_file_{p['id']}"] = uploaded_file

                if st.session_state[f"uploaded_file_{p['id']}"] is not None:
                    if st.button("⬆️ Upload", key=f"upload_btn_{p['id']}"):
                        files = {"file": (
                            st.session_state[f"uploaded_file_{p['id']}"].name,
                            st.session_state[f"uploaded_file_{p['id']}"],
                            st.session_state[f"uploaded_file_{p['id']}"].type
                        )}
                        r = requests.post(
                            f"{API_URL}/projects/{p['id']}/upload_file",
                            files=files,
                            headers={"Authorization": f"Bearer {token}"}
                        )
                        if r.status_code == 200:
                            uploaded_file = st.session_state[f"uploaded_file_{p['id']}"]
                            st.success(f"✅ {uploaded_file.name} uploaded")
                            st.session_state[f"uploaded_file_{p['id']}"] = None
                            st.rerun()
                        else:
                            st.error(f"❌ Upload failed: {r.text}")

                fr = requests.get(f"{API_URL}/projects/{p['id']}", headers={"Authorization": f"Bearer {token}"})
                if fr.status_code == 200:
                    project_details = fr.json()
                    files = project_details.get("files", [])
                    if files:
                        st.markdown("### Uploaded Files")
                        for f in files:
                            col1, col2, col3 = st.columns([6, 1, 1])
                            col1.markdown(f"📄 {f['filename']} (uploaded at {f['uploaded_at']})")

                            with col2:
                                if st.button("🗑️", key=f"del_file_{f['id']}"):
                                    r_del = requests.delete(
                                        f"{API_URL}/projects/files/{f['id']}",
                                        headers={"Authorization": f"Bearer {token}"}
                                    )
                                    if r_del.status_code == 200:
                                        st.success("File deleted")
                                        st.rerun()
                                    else:
                                        st.error("❌ Failed to delete file")

                            with col3:
                                r_dl = requests.get(
                                    f"{API_URL}/projects/files/{f['id']}/download",
                                    headers={"Authorization": f"Bearer {token}"}
                                )
                                if r_dl.status_code == 200:
                                    col3.download_button(
                                        label="⬇️",
                                        data=r_dl.content,
                                        file_name=f['filename']
                                    )
                else:
                    st.info("No files uploaded yet.")

                assigned_users = []
                try:
                    ar = requests.get(f"{API_URL}/projects/{p['id']}/users", headers=headers)
                    if ar.status_code == 200:
                        assigned_users = ar.json()
                except Exception:
                    pass

                if assigned_users:
                    st.markdown(
                        "👥 **Assigned Users:** " +
                        ", ".join([
                            next((usr["username"] for usr in all_users if usr["id"] == u["user_id"]), str(u["user_id"]))
                            for u in assigned_users
                        ])
                    )
                else:
                    st.info("No users assigned yet.")

                cols = st.columns([3, 1])

                with cols[0]:
                    selected_users = st.multiselect(
                        "Assign Users",
                        options=[u["id"] for u in all_users],
                        format_func=lambda uid: next(
                            (u["username"] for u in all_users if u["id"] == uid), str(uid)
                        ),
                        default=[u["user_id"] for u in assigned_users],
                        key=f"user_select_{p['id']}"
                    )

                with cols[1]:
                    if st.button("🗑️ Delete Project", key=f"del_proj_{p['id']}"):
                        dr = requests.delete(f"{API_URL}/projects/{p['id']}", headers=headers)
                        if dr.status_code == 200:
                            st.success(f"🗑️ Project '{p['name']}' deleted")
                            st.rerun()
                        else:
                            st.error("❌ Failed to delete project")

                if st.button("Update Assignments", key=f"assign_btn_{p['id']}"):
                    payload = {"user_ids": [int(uid) for uid in selected_users]}
                    st.write("DEBUG payload →", payload)  # Debug output
                    r = requests.post(
                        f"{API_URL}/projects/{p['id']}/users/assign",
                        json=payload,
                        headers=headers,
                    )
                    if r.status_code == 200:
                        st.success("✅ Assignments updated")
                        st.rerun()
                    else:
                        st.error(f"❌ Failed to update assignments: {r.text}")


# --- NEW FUNCTION: Save Chat History ---
def save_chat_history(project_id, history, headers):
    """
    Saves the current chat history to the backend.
    """
    payload = {"history": history}
    try:
        requests.put(
            f"{API_URL}/projects/{project_id}/chat_history",
            json=payload,
            headers=headers,
            timeout=5 # Use a timeout to avoid hanging the app
        )
    except Exception as e:
        print(f"Warning: Could not save chat history. Error: {e}")


# ---------- User Dashboard (Healthcare Test Case Generator) ----------
def user_dashboard():
    import google.generativeai as genai
    import fitz  # PyMuPDF
    import docx  # python-docx
    import pandas as pd
    import re
    from config import GENAI_API_KEY

    genai.configure(api_key=GENAI_API_KEY)
    model = genai.GenerativeModel("gemini-2.5-pro")

    st.title("🏥 Healthcare Test Case Generator")
    headers = {"Authorization": f"Bearer {st.session_state['token']}"}

    if "testcases" not in st.session_state:
        st.session_state.testcases = []
    
    if "doc_content" not in st.session_state:
        st.session_state.doc_content = None

    r = requests.get(f"{API_URL}/users/me/projects", headers=headers)
    if r.status_code != 200:
        st.markdown("❌ Failed to fetch project info")
        return

    projects = r.json()
    if not projects:
        st.markdown("⚠️ No project assigned")
        return

    if len(projects) == 1:
        selected_project = projects[0]
        st.markdown(f"### 🟢 Assigned Project: **{selected_project['name']}**")
    else:
        selected_name = st.selectbox("🟢 Select Assigned Project", [p["name"] for p in projects])
        selected_project = next(p for p in projects if p["name"] == selected_name)
        st.markdown(f"### Currently Viewing: **{selected_project['name']}**")

    session_key = f"messages_for_project_{selected_project['id']}"
    if session_key not in st.session_state:
        history_from_db = selected_project.get("chat_history")
        if history_from_db and isinstance(history_from_db, list):
            st.session_state[session_key] = history_from_db
        else:
            st.session_state[session_key] = [] 
    
    st.session_state.messages = st.session_state[session_key]

    safety_settings = {
        'HARM_CATEGORY_HARASSMENT': 'BLOCK_NONE',
        'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_NONE',
        'HARM_CATEGORY_SEXUALLY_EXPLICIT': 'BLOCK_NONE',
        'HARM_CATEGORY_DANGEROUS_CONTENT': 'BLOCK_NONE',
    }
    
    def parse_test_cases(response_text):
        pattern = r"\**Test Case ID\**:\s*(.*?)\s*\**Description\**:\s*(.*?)\s*\**Steps\**:\s*(.*?)\s*\**Expected Result\**:\s*(.*?)\s*\**Priority\**:\s*(.*?)(?=\n\n|\Z)"
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
        st.session_state.doc_content = extract_text(uploaded_file, ftype)
        st.success(f"✅ {uploaded_file.name} uploaded and ready. Ask me to 'generate test cases' in the chat.")

    r2 = requests.get(f"{API_URL}/projects/{selected_project['id']}/testcases", headers=headers)
    if r2.status_code == 200:
        fetched = r2.json()
        st.session_state.testcases = []
        for tc in fetched:
            tc_data = tc.get("test_case", {}) 
            if tc_data:
                tc_data["id"] = tc.get("id")
                st.session_state.testcases.append(tc_data)
    else:
        st.session_state.testcases = [] 

    col1, col2 = st.columns([0.6, 0.4])

    with col1:
        st.markdown("### 📋 Existing Test Cases")
        st.info("You can edit, add, or delete test cases directly in the table. Click 'Save Changes' to update the database.")
        
        original_df = pd.DataFrame(st.session_state.testcases)
        
        display_columns = ["Test Case ID", "Description", "Steps", "Expected Result", "Priority", "id"]
        
        for col in display_columns:
            if col not in original_df:
                original_df[col] = None

        original_df = original_df[display_columns]

        edited_df = st.data_editor(
            original_df,
            height=600,
            num_rows="dynamic",
            column_config={
                "id": None 
            },
            key="data_editor"
        )
        
        btn_col1, btn_col2 = st.columns(2)

        with btn_col1:
            if st.button("Save Changes to Test Cases", use_container_width=True):
                with st.spinner("Saving changes..."):
                    original_ids = set(original_df['id'].dropna().astype(int))
                    edited_ids = set(edited_df['id'].dropna().astype(int))
                    
                    deleted_ids = original_ids - edited_ids
                    for db_id in deleted_ids:
                        resp = requests.delete(
                            f"{API_URL}/projects/{selected_project['id']}/testcases/{db_id}",
                            headers=headers
                        )
                    
                    new_rows = edited_df[edited_df['id'].isna()]
                    for _, row in new_rows.iterrows():
                        payload = row.to_dict()
                        del payload['id'] 
                        resp = requests.post(
                            f"{API_URL}/projects/{selected_project['id']}/testcases",
                            json=payload,
                            headers=headers
                        )

                    original_map = {row['id']: row.to_dict() for _, row in original_df.iterrows() if pd.notna(row['id'])}
                    edited_map = {row['id']: row.to_dict() for _, row in edited_df.iterrows() if pd.notna(row['id'])}
                    
                    for db_id in original_ids.intersection(edited_ids):
                        if original_map[db_id] != edited_map[db_id]:
                            payload = edited_map[db_id]
                            del payload['id'] 
                            resp = requests.put(
                                f"{API_URL}/projects/{selected_project['id']}/testcases/{db_id}",
                                json=payload, 
                                headers=headers
                            )
                    
                    st.success("All changes saved successfully!")
                    st.rerun()

        with btn_col2:
            if st.button("Assign Test Cases", use_container_width=True): 
                st.session_state.deploy_triggered = True
        
        if "deploy_triggered" not in st.session_state:
            st.session_state.deploy_triggered = False

        if st.session_state.deploy_triggered:
            st.session_state.deploy_triggered = False 
            payload = {
                "project_id": selected_project['id'],
                "organization": selected_project.get("organization"),
                "project_name": selected_project.get("name"),
                "pat": selected_project.get("pat"),
                "area_path": selected_project.get("name"),
                "iteration_path": f"{selected_project.get('name')}\\Sprint 1"
            }
            
            with st.spinner(f"Assigning test cases to {selected_project.get('name')}..."):
                try:
                    deploy_resp = requests.post(
                        f"{API_URL}/deploy_testcases",
                        headers={**headers, "Content-Type": "application/json"},
                        json=payload
                    )
                    if deploy_resp.status_code == 200:
                        results = deploy_resp.json().get("results", [])
                        if results:
                            df_results = pd.DataFrame(results)
                            st.success(f"🚀 Test cases assigned successfully!")
                            st.markdown("### Assignment Results")
                            st.dataframe(df_results)
                        else:
                            st.info("✅ Assignment completed, but no results returned.")
                    else:
                        st.error(f"❌ Assignment failed: {deploy_resp.text}")

                except Exception as e:
                    st.error(f"❌ Assignment error: {str(e)}")
            
    with col2:
        st.markdown("### 🤖 AI Chat")
        
        chat_container = st.container(height=600)
        with chat_container:
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

        if prompt := st.chat_input("Ask me something..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            save_chat_history(selected_project['id'], st.session_state.messages, headers)
            st.rerun()

    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        prompt = st.session_state.messages[-1]["content"]
        
        normalized_prompt = prompt.lower().strip()
        greetings = ["hi", "hello", "hey", "what are you", "who are you", "what do you do"]

        if normalized_prompt in greetings:
            intro_message = (
                "👋 Hi! I am a **Test Case Generator**. "
                "You can **upload a requirements file** to automatically generate test cases. "
                "You can also ask me to `delete <ID>` or `modify <ID> <field> to ...`."
            )
            st.session_state.messages.append({"role": "assistant", "content": intro_message})
            save_chat_history(selected_project['id'], st.session_state.messages, headers)
            st.rerun()
        
        elif any(x in normalized_prompt for x in ["generate", "create"]):
            
            if st.session_state.doc_content:
                with col2:
                    with chat_container:
                        with st.chat_message("assistant"):
                            with st.spinner("🤖 Generating test cases from your file..."):
                                
                                full_prompt = f"""
                                You are an AI specialized in generating structured test cases.
                                You MUST generate test cases in the following format. Do NOT add any
                                introductory text or markdown formatting.
                                
                                Test Case ID: <ID>
                                Description: <Description>
                                Steps: <Steps>
                                Expected Result: <Result>
                                Priority: <Priority>
                                
                                (Leave a blank line between test cases)

                                Document Content: {st.session_state.doc_content[:20000]}
                                User Query: "{prompt}"
                                """
                                
                                gen_response = model.generate_content(full_prompt, safety_settings=safety_settings)
                                gen_response_text = ""
                                try:
                                    gen_response_text = gen_response.text
                                except ValueError:
                                    gen_response_text = "Sorry, I was unable to generate a response for that."

                                df = parse_test_cases(gen_response_text)
                                chat_message = ""
                                if df is not None and not df.empty:
                                    for _, row in df.iterrows():
                                        testcase_json = row.to_dict()
                                        resp = requests.post(
                                            f"{API_URL}/projects/{selected_project['id']}/testcases",
                                            json=testcase_json,
                                            headers=headers
                                        )
                                        if resp.status_code != 200:
                                            st.error(f"❌ Failed to save test case: {resp.text}")
                                    
                                    chat_message = f"I've generated and saved {len(df)} test cases from the file."
                                else:
                                    chat_message = "I'm sorry, I couldn't find any test cases in that document. The AI response may not have been in the correct format."

                                st.session_state.messages.append({"role": "assistant", "content": chat_message})
                                save_chat_history(selected_project['id'], st.session_state.messages, headers)
                                
                                st.rerun()

            else:
                chat_message = "Please upload a requirements file (PDF, DOCX, etc.) first, and then I can generate test cases."
                st.session_state.messages.append({"role": "assistant", "content": chat_message})
                save_chat_history(selected_project['id'], st.session_state.messages, headers)
                st.rerun()

        else:
            tc_data_for_prompt = []
            for tc in st.session_state.testcases:
                tc_data_for_prompt.append({
                    "id": tc.get("id"),
                    "Test Case ID": tc.get("Test Case ID"),
                    "Description": tc.get("Description")
                })

            instructions_prompt = f"""
            You are an AI assistant. The user has the following test cases:
            {tc_data_for_prompt}
            
            When the user asks to delete or modify, use the "id" field (the database ID),
            not the "Test Case ID" field.
            
            User Instruction: "{prompt}"
            
            Respond ONLY with structured commands in the format:
            DELETE:<id>
            MODIFY:<id>|<field>|<new_value>
            
            If it is NOT a command, just respond as a helpful assistant.
            """
            
            response = model.generate_content(instructions_prompt, safety_settings=safety_settings)

            response_text = ""
            try:
                response_text = response.text
            except ValueError:
                fallback_message = (
                    "I'm sorry, I couldn't process that last request (it may have been blocked by safety filters). "
                    "As a reminder, I am your test case assistant. "
                    "You can **upload a requirements file** (PDF, DOCX, etc.) to generate test cases. "
                    "You can also ask me to `delete <ID>` or `modify <ID> <field> to ...`."
                )
                st.session_state.messages.append({"role": "assistant", "content": fallback_message})
                save_chat_history(selected_project['id'], st.session_state.messages, headers)
                st.rerun()
                return 

            processed_command = False
            for instr in response_text.splitlines():
                instr = instr.strip()
                if instr.startswith("DELETE:"):
                    processed_command = True
                    tcid = instr.replace("DELETE:", "").strip()
                    resp = requests.delete(
                        f"{API_URL}/projects/{selected_project['id']}/testcases/{tcid}",
                        headers=headers
                    )
                    if resp.status_code == 200:
                        chat_message = f"I have successfully deleted test case {tcid}."
                        st.session_state.messages.append({"role": "assistant", "content": chat_message})
                        save_chat_history(selected_project['id'], st.session_state.messages, headers)
                    else:
                        st.error(f"❌ Failed to delete {tcid}: {resp.text}")

                elif instr.startswith("MODIFY:"):
                    processed_command = True
                    parts = instr.replace("MODIFY:", "").split("|")
                    if len(parts) == 3:
                        tcid, field, new_value = parts
                        tcid = tcid.strip()
                        field = field.strip()
                        new_value = new_value.strip()

                        original_tc = None
                        for tc in st.session_state.testcases:
                            if str(tc.get('id')) == str(tcid):
                                original_tc = tc.copy() 
                                break
                        
                        if not original_tc:
                            st.error(f"❌ Cannot find test case with ID {tcid} to modify")
                            continue

                        original_tc[field] = new_value
                        payload = original_tc 
                        
                        resp = requests.put(
                            f"{API_URL}/projects/{selected_project['id']}/testcases/{tcid}",
                            json=payload, 
                            headers=headers
                        )
                        if resp.status_code == 200:
                            chat_message = f"I've updated the '{field}' for test case {tcid}."
                            st.session_state.messages.append({"role": "assistant", "content": chat_message})
                            save_chat_history(selected_project['id'], st.session_state.messages, headers)
                        else:
                            st.error(f"❌ Failed to update {tcid}: {resp.text}")

            if processed_command:
                st.rerun() 
            
            else: # Not a command, just a chat
                st.session_state.messages.append({"role": "assistant", "content": response_text})
                save_chat_history(selected_project['id'], st.session_state.messages, headers)
                st.rerun()


# ---------- Main Router ----------
def main():
    if "token" not in st.session_state:
        # --- This will run the login page ---
        login_page()
    else:
        # --- Once logged in, reset the background to white ---
        # (This is handled by Streamlit's default theme)
            
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
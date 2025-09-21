import streamlit as st
import requests
import os ,json

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

        # --- Create New Project ---

        with st.expander("➕ Add New Project", expanded=True):
            with st.form("project_config_form", clear_on_submit=True):

                project_name = st.text_input("Project Name")
                description = st.text_area("Project Description")
                environment = st.selectbox("Environment", ["Development", "Staging", "Production"])
                azure_org = st.text_input("Azure Org Name")
                azure_project = st.text_input("Azure Project Name")
                azure_pat = st.text_input("Azure PAT", type="password")

                # Fetch users for possible assignment
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
                    }

                    r = requests.post(f"{API_URL}/projects", json=payload, headers=headers)

                    if r.status_code in (200, 201):
                        st.success(f"✅ Project '{project_name}' saved")
                        # If admin selected users, assign them
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

    # --- List Existing Projects ---
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
        # Always fetch all users for assignment controls
        users_resp = requests.get(f"{API_URL}/users", headers=headers)
        all_users = users_resp.json() if users_resp.status_code == 200 else []

        for p in projects:
            with st.expander(f"📂 {p['name']} — Org: {p.get('organization', '')}", expanded=False):
                st.caption(p.get("description", ""))
                # --- File Upload Section ---
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

                # List existing files
                fr = requests.get(f"{API_URL}/projects/{p['id']}", headers={"Authorization": f"Bearer {token}"})
                if fr.status_code == 200:
                    project_details = fr.json()
                    files = project_details.get("files", [])
                    if files:
                        st.markdown("### Uploaded Files")
                        for f in files:
                            col1, col2, col3 = st.columns([6, 1, 1])
                            col1.markdown(f"📄 {f['filename']} (uploaded at {f['uploaded_at']})")

                            # Delete file
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

                            # Download file
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
                # -----------------------------------------------------------------

                # --- Show currently assigned users ---
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

                # --- Two-column layout for Assign + Delete ---
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

                # --- Update Assignments ---
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


# ---------- User Dashboard (Healthcare Test Case Generator) ----------
def user_dashboard():
    import google.generativeai as genai
    import fitz  # PyMuPDF
    import docx  # python-docx
    import pandas as pd
    import re
    from config import GENAI_API_KEY

    genai.configure(api_key=GENAI_API_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")

    st.title("🏥 Healthcare Test Case Generator")
    headers = {"Authorization": f"Bearer {st.session_state['token']}"}

    # ---------- Initialize session state ----------
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "testcases" not in st.session_state:
        st.session_state.testcases = []

    if "doc_content" not in st.session_state:
        st.session_state.doc_content = None

    # ---------- Fetch Assigned Project ----------
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

    # ---------- File Upload ----------
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
        st.success(f"✅ {uploaded_file.name} uploaded and processed!")

    # ---------- Load Existing Test Cases ----------
    r2 = requests.get(f"{API_URL}/projects/{selected_project['id']}/testcases", headers=headers)
    if r2.status_code == 200:
        fetched = r2.json()
        st.session_state.testcases = []
        for tc in fetched:
            tc_data = tc.get("test_case", {})
            if tc_data:
                tc_data["id"] = tc.get("id")  # DB ID
                st.session_state.testcases.append(tc_data)
    else:
        st.session_state.testcases = []

    # Display existing test cases
    if st.session_state.testcases:
        st.markdown("### 📋 Existing Test Cases")
        df = pd.DataFrame(st.session_state.testcases)
        display_df = df[["Test Case ID", "Description", "Steps", "Expected Result", "Priority", "id"]].rename(columns={
            "Test Case ID": "test_case_id",
            "Description": "description",
            "Steps": "steps",
            "Expected Result": "expected_result",
            "Priority": "priority"
        })
        st.dataframe(display_df)
    else:
        st.markdown("⚠️ No test cases found for this project")

    # ---------- Display Chat Messages ----------
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # ---------- AI Chat Input ----------
    if prompt := st.chat_input("Ask me something..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        normalized_prompt = prompt.lower().strip()
        greetings = ["hi", "hello", "hey", "what are you", "who are you", "what do you do"]

        if normalized_prompt in greetings:
            intro_message = (
                "👋 Hi! I am a **Test Case Generator for Healthcare Applications**. "
                "Upload requirements (PDF, DOCX, or Markdown), and I’ll generate structured test cases. "
                "You can also type commands like 'delete TC001' or 'modify TC002 description to ...'."
            )
            with st.chat_message("assistant"):
                st.markdown(intro_message)
            st.session_state.messages.append({"role": "assistant", "content": intro_message})
            return

        # ---------- Handle AI Operations ----------
        instructions_prompt = f"""
        You are an AI assistant. The user has the following test cases:
        {pd.DataFrame(st.session_state.testcases).to_dict(orient='records')}
        User Instruction: "{prompt}"
        Respond ONLY with structured commands in the format:
        DELETE:<id>
        MODIFY:<id>|<field>|<new_value>
        """

        response = model.generate_content(instructions_prompt)

        for instr in response.text.splitlines():
            instr = instr.strip()
            if instr.startswith("DELETE:"):
                tcid = instr.replace("DELETE:", "").strip()
                resp = requests.delete(
                    f"{API_URL}/projects/{selected_project['id']}/testcases/{tcid}",
                    headers=headers
                )
                if resp.status_code == 200:
                    st.success(f"✅ Test case {tcid} deleted")
                    # Update session state
                    st.session_state.testcases = [t for t in st.session_state.testcases if str(t['id']) != str(tcid)]
                else:
                    st.error(f"❌ Failed to delete {tcid}: {resp.text}")

            elif instr.startswith("MODIFY:"):
                parts = instr.replace("MODIFY:", "").split("|")
                if len(parts) == 3:
                    tcid, field, new_value = parts
                    resp = requests.put(
                        f"{API_URL}/projects/{selected_project['id']}/testcases/{tcid.strip()}",
                        json={field.strip(): new_value.strip()},
                        headers=headers
                    )
                    if resp.status_code == 200:
                        st.success(f"✅ Test case {tcid} updated")
                        # Update session state
                        for t in st.session_state.testcases:
                            if str(t["id"]) == str(tcid.strip()):
                                t[field.strip()] = new_value.strip()
                    else:
                        st.error(f"❌ Failed to update {tcid}: {resp.text}")
            st.markdown("### 🚀 Deploy Project Test Cases")

            if "deploy_triggered" not in st.session_state:
                st.session_state.deploy_triggered = False

            if st.button(f"Deploy '{selected_project['name']}' Test Cases"):
                st.session_state.deploy_triggered = True

            if st.session_state.deploy_triggered:
                st.session_state.deploy_triggered = False  # reset
                payload = {
                    "project_id": selected_project['id'],
                    "organization": selected_project.get("organization"),
                    "project_name": selected_project.get("name"),
                    "pat": selected_project.get("pat"),
                    "area_path": selected_project.get("name"),
                    "iteration_path": f"{selected_project.get('name')}\\Sprint 1"
                }

                try:
                    deploy_resp = requests.post(
                        f"{API_URL}/deploy_testcases",
                        headers={**headers, "Content-Type": "application/json"},
                        json=payload
                    )

                    st.write("DEBUG status code:", deploy_resp.status_code)  # debug

                    if deploy_resp.status_code == 200:
                        results = deploy_resp.json().get("results", [])
                        if results:
                            import pandas as pd
                            df = pd.DataFrame(results)
                            st.success(f"🚀 Project '{selected_project['name']}' deployed successfully!")
                            st.markdown("### Deployment Results")
                            st.dataframe(df)
                        else:
                            st.info("✅ Deployment completed, but no results returned.")
                    else:
                        st.error(f"❌ Deployment failed: {deploy_resp.text}")

                except Exception as e:
                    st.error(f"❌ Deployment error: {str(e)}")

        # ---------- Show updated test cases after operations ----------
        if st.session_state.testcases:
            st.markdown("### 📋 Updated Test Cases")
            df = pd.DataFrame(st.session_state.testcases)
            display_df = df[["Test Case ID", "Description", "Steps", "Expected Result", "Priority", "id"]].rename(
                columns={
                    "Test Case ID": "test_case_id",
                    "Description": "description",
                    "Steps": "steps",
                    "Expected Result": "expected_result",
                    "Priority": "priority"
                })
            st.dataframe(display_df)
        else:
            st.markdown("⚠️ No test cases remaining after this operation")

        # ---------- Generate Test Cases from Uploaded File ----------
        if "doc_content" in st.session_state and any(x in normalized_prompt for x in ["generate", "create"]):
            full_prompt = f"""
            You are an AI specialized in generating structured test cases for Healthcare Applications.
            Generate test cases in the format:
            Test Case ID:
            Description:
            Steps:
            Expected Result:
            Priority:

            Document Content: {st.session_state['doc_content'][:20000]}
            User Query: {prompt}
            """
            with st.chat_message("assistant"):
                with st.spinner("🤖 Generating structured test cases..."):
                    gen_response = model.generate_content(full_prompt)

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

                df = parse_test_cases(gen_response.text)
                if df is not None and not df.empty:
                    st.table(df)
                    for _, row in df.iterrows():
                        testcase_json = row.to_dict()
                        resp = requests.post(
                            f"{API_URL}/projects/{selected_project['id']}/testcases",
                            json=testcase_json,
                            headers=headers
                        )
                        if resp.status_code == 200:
                            st.success(f"✅ Test case '{testcase_json.get('Test Case ID')}' saved to DB")
                        else:
                            st.error(f"❌ Failed to save test case: {resp.text}")

            st.session_state.messages.append({"role": "assistant", "content": gen_response.text})
            with st.chat_message("assistant"):
                st.markdown(gen_response.text)

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

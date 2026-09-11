"""
frontend/app.py
----------------
Streamlit frontend for NoteMind AI (Intelligent PDF Study Assistant).
Connects to FastAPI backend for Authentication, PDF RAG QA, Notes Generation,
and Interactive Quizzes.
"""

import time
from datetime import datetime, timedelta
import streamlit as st
import streamlit.components.v1 as components
import requests

# Backend API Base URL
API_URL = "https://notemind-backend-7vl9.onrender.com"

# ---------------------------------------------------------------------
# 1. Page Configuration & Session State Initialization
# ---------------------------------------------------------------------

st.set_page_config(
    page_title="NoteMind AI - Study Assistant",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS: Header hide kare bina sidebar toggle button ko hamesha visible aur clickable rakhna
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display:none;}
    [data-testid="stStatusWidget"] {visibility: hidden;}
    .viewerBadge_container__1QSob {display: none !important;}
    .viewerBadge_link__1SuGQ {display: none !important;}
    div[class*="viewerBadge"] {display: none !important;}
    div[class*="profile"] {display: none !important;}
    #manage-app-button {display: none !important;}

    /* Sidebar toggle button (>>) hamesha visible aur clickable rahega */
    [data-testid="collapsedControl"] {
        display: flex !important;
        visibility: visible !important;
        z-index: 999999 !important;
        top: 0.75rem !important;
        left: 0.75rem !important;
        background-color: #1e293b !important;
        border-radius: 8px !important;
        border: 1px solid #334155 !important;
        color: #38bdf8 !important;
    }
    [data-testid="collapsedControl"] svg {
        fill: #38bdf8 !important;
        stroke: #38bdf8 !important;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize persistent session state variables
if "token" not in st.session_state:
    st.session_state.token = None
if "user_email" not in st.session_state:
    st.session_state.user_email = None
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "uploaded_filename" not in st.session_state:
    st.session_state.uploaded_filename = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "quiz_data" not in st.session_state:
    st.session_state.quiz_data = []
if "quiz_submitted" not in st.session_state:
    st.session_state.quiz_submitted = False

# Step A: Restore from URL query parameters
params = st.query_params
if not st.session_state.token and "token" in params:
    tok = params.get("token")
    if tok and str(tok).strip() and tok != "None":
        st.session_state.token = str(tok).strip()
        st.session_state.user_email = params.get("email", "")
        if "sid" in params:
            st.session_state.session_id = params.get("sid")
        if "fn" in params:
            st.session_state.uploaded_filename = params.get("fn")

# Step B: Agar session_state khali hai toh browser ke localStorage se restore karein
if not st.session_state.token:
    components.html("""
        <script>
        const token = localStorage.getItem("notemind_token");
        const email = localStorage.getItem("notemind_email");
        const sid = localStorage.getItem("notemind_sid");
        const fn = localStorage.getItem("notemind_fn");
        
        if (token && token !== "null" && token !== "") {
            const url = new URL(window.parent.location.href);
            if (!url.searchParams.get("token")) {
                url.searchParams.set("token", token);
                if (email) url.searchParams.set("email", email);
                if (sid) url.searchParams.set("sid", sid);
                if (fn) url.searchParams.set("fn", fn);
                window.parent.location.href = url.href;
            }
        }
        </script>
    """, height=0, width=0)


def get_auth_headers():
    """Return authorization headers with Bearer token."""
    if st.session_state.token:
        return {"Authorization": f"Bearer {st.session_state.token}"}
    return {}


# ---------------------------------------------------------------------
# 2. Sidebar: Authentication & Navigation
# ---------------------------------------------------------------------

with st.sidebar:
    st.title("🧠 NoteMind AI")
    st.caption("Your Intelligent PDF Study Assistant")
    st.markdown("---")

    if not st.session_state.token:
        auth_mode = st.radio("Account Access", ["Login", "Register"], horizontal=True)

        if auth_mode == "Login":
            st.subheader("Login")
            with st.form("login_form"):
                email = st.text_input("Email", placeholder="student@example.com")
                password = st.text_input("Password", type="password")
                login_btn = st.form_submit_button("Sign In", use_container_width=True)

                if login_btn:
                    if email and password:
                        try:
                            clean_url = API_URL.rstrip("/")
                            res = requests.post(
                                f"{clean_url}/api/login",
                                json={"email": email, "password": password},
                                headers={"Content-Type": "application/json"},
                            )
                            if res.status_code == 200:
                                data = res.json()
                                access_token = data["access_token"]
                                st.session_state.token = access_token
                                st.session_state.user_email = email

                                # URL parameters update
                                st.query_params["token"] = access_token
                                st.query_params["email"] = email

                                # Browser permanent storage mein save karein
                                components.html(f"""
                                    <script>
                                    localStorage.setItem("notemind_token", "{access_token}");
                                    localStorage.setItem("notemind_email", "{email}");
                                    </script>
                                """, height=0, width=0)

                                st.success("Logged in successfully!")
                                time.sleep(0.3)
                                st.rerun()
                            else:
                                try:
                                    err_detail = res.json().get("detail", res.text)
                                except Exception:
                                    err_detail = res.text
                                st.error(f"Login failed ({res.status_code}): {err_detail}")
                        except Exception as e:
                            st.error(f"Cannot connect to backend: {e}")
                    else:
                        st.warning("Please fill in both email and password.")

        else:
            st.subheader("Register")
            with st.form("register_form"):
                reg_email = st.text_input("Email", placeholder="student@example.com")
                reg_password = st.text_input("Password", type="password")
                reg_btn = st.form_submit_button("Create Account", use_container_width=True)

                if reg_btn:
                    if reg_email and reg_password:
                        try:
                            clean_url = API_URL.rstrip("/")
                            res = requests.post(
                                f"{clean_url}/api/register",
                                json={"email": reg_email, "password": reg_password},
                                headers={"Content-Type": "application/json"},
                            )
                            if res.status_code in [200, 201]:
                                st.success("Account created! Please switch to Login tab to sign in.")
                            else:
                                try:
                                    err_detail = res.json().get("detail", res.text)
                                except Exception:
                                    err_detail = res.text
                                st.error(f"Backend returned ({res.status_code}): {err_detail}")
                        except Exception as e:
                            st.error(f"Network error connecting to backend: {e}")
                    else:
                        st.warning("Please fill in all fields.")

    else:
        st.success(f"👤 Logged in as:\n**{st.session_state.user_email}**")

        if st.button("🚪 Logout", use_container_width=True):
            # Storage aur session completely clear karein
            components.html("""
                <script>
                localStorage.removeItem("notemind_token");
                localStorage.removeItem("notemind_email");
                localStorage.removeItem("notemind_sid");
                localStorage.removeItem("notemind_fn");
                const url = new URL(window.parent.location.href);
                url.search = "";
                window.parent.location.href = url.href;
                </script>
            """, height=0, width=0)

            st.query_params.clear()
            st.session_state.clear()
            time.sleep(0.3)
            st.rerun()

        st.markdown("---")
        st.subheader("Navigation")
        navigation = st.radio(
            "Go to",
            ["📖 Study Room", "📂 My Saved Notes"],
            label_visibility="collapsed",
        )


# ---------------------------------------------------------------------
# 3. Main Area: Require Login Check
# ---------------------------------------------------------------------

if not st.session_state.token:
    st.info("👋 Welcome to NoteMind AI! Please **Log in** or **Register** from the sidebar to begin.")
    st.stop()


# ---------------------------------------------------------------------
# 4. View: 📖 Study Room
# ---------------------------------------------------------------------

if navigation == "📖 Study Room":
    st.header("📖 Study Room")
    st.write("Upload course slides, textbooks, or research papers to unlock AI study tools.")

    col_upload, col_status = st.columns([2, 1])

    with col_upload:
        uploaded_pdf = st.file_uploader(
            "Upload your PDF document",
            type=["pdf"],
            help="Select a PDF to extract and analyze.",
        )

    with col_status:
        st.write("")
        st.write("")
        if uploaded_pdf and st.button("⚡ Process PDF", use_container_width=True):
            with st.spinner("Processing PDF..."):
                try:
                    files = {"file": (uploaded_pdf.name, uploaded_pdf.getvalue(), "application/pdf")}
                    res = requests.post(
                        f"{API_URL.rstrip('/')}/api/upload-pdf",
                        headers=get_auth_headers(),
                        files=files,
                    )
                    if res.status_code == 200:
                        data = res.json()
                        st.session_state.session_id = data["session_id"]
                        st.session_state.uploaded_filename = data["filename"]
                        st.session_state.chat_history = []
                        st.session_state.quiz_data = []
                        st.session_state.quiz_submitted = False

                        # Active document ko session aur browser storage mein retain karein
                        st.query_params["sid"] = str(data["session_id"])
                        st.query_params["fn"] = data["filename"]
                        components.html(f"""
                            <script>
                            localStorage.setItem("notemind_sid", "{data['session_id']}");
                            localStorage.setItem("notemind_fn", "{data['filename']}");
                            </script>
                        """, height=0, width=0)

                        st.success(f"✅ **{data['filename']}** processed successfully!")
                    else:
                        st.error(res.json().get("detail", "Failed to process PDF."))
                except Exception as e:
                    st.error(f"Error uploading PDF: {e}")

    if st.session_state.session_id:
        st.info(f"📄 Active Document: **{st.session_state.uploaded_filename}**")

        tab_notes, tab_chat, tab_quiz = st.tabs(
            ["📝 Notes & Summary", "💬 Chat with PDF", "🎯 Practice Quiz"]
        )

        # ----------------- Sub-Tab 1: Notes & Summary -----------------
        with tab_notes:
            st.subheader("Automated Study Notes & Summary")
            col_b1, col_b2 = st.columns(2)

            with col_b1:
                if st.button("✨ Generate Comprehensive Notes", use_container_width=True):
                    with st.spinner("Generating structured study notes..."):
                        try:
                            res = requests.post(
                                f"{API_URL.rstrip('/')}/api/generate-notes",
                                headers=get_auth_headers(),
                                json={"session_id": st.session_state.session_id},
                            )
                            if res.status_code == 200:
                                st.session_state["notes_view_mode"] = "comprehensive"
                                st.session_state["last_comprehensive_notes"] = res.json()
                                st.success("Comprehensive notes generated and saved to your library!")
                            else:
                                st.error(res.json().get("detail", "Error generating notes."))
                        except Exception as e:
                            st.error(f"Request failed: {e}")

            with col_b2:
                if st.button("📌 Quick Summary & Takeaways", use_container_width=True):
                    with st.spinner("Generating quick summary..."):
                        try:
                            res = requests.post(
                                f"{API_URL.rstrip('/')}/api/summary",
                                headers=get_auth_headers(),
                                json={"session_id": st.session_state.session_id},
                            )
                            if res.status_code == 200:
                                st.session_state["notes_view_mode"] = "summary"
                                st.session_state["last_quick_summary"] = res.json()
                            else:
                                st.error(res.json().get("detail", "Error generating summary."))
                        except Exception as e:
                            st.error(f"Request failed: {e}")

            view_mode = st.session_state.get("notes_view_mode")

            if view_mode == "comprehensive" and "last_comprehensive_notes" in st.session_state:
                data = st.session_state["last_comprehensive_notes"]
                st.markdown("---")
                st.info("💡 Viewing: **Comprehensive Study Notes**")

                st.markdown("### 📋 Executive Summary")
                st.write(data.get("summary", "No summary available."))

                st.markdown("### 🔑 Key Takeaways")
                for pt in data.get("key_points", []):
                    st.markdown(f"- {pt}")

                st.markdown("### 📚 Full Study Notes")
                st.markdown(data.get("notes", "No notes available."))

            elif view_mode == "summary" and "last_quick_summary" in st.session_state:
                sum_data = st.session_state["last_quick_summary"]
                st.markdown("---")
                st.info("💡 Viewing: **Quick Summary & Takeaways Only**")

                st.markdown("### 📋 Quick Summary")
                st.write(sum_data.get("summary", "No summary available."))

                st.markdown("### 🔑 Key Takeaways")
                for pt in sum_data.get("key_points", []):
                    st.markdown(f"- {pt}")

        # ----------------- Sub-Tab 2: Chat with PDF -----------------
        with tab_chat:
            st.subheader("Ask Questions About Your Document")

            for message in st.session_state.chat_history:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

            user_query = st.chat_input("Ask a question about this document...")
            if user_query:
                st.session_state.chat_history.append({"role": "user", "content": user_query})
                with st.chat_message("user"):
                    st.markdown(user_query)

                with st.chat_message("assistant"):
                    with st.spinner("Searching document & generating answer..."):
                        try:
                            res = requests.post(
                                f"{API_URL.rstrip('/')}/api/chat",
                                headers=get_auth_headers(),
                                json={
                                    "question": user_query,
                                    "session_id": st.session_state.session_id,
                                },
                            )
                            if res.status_code == 200:
                                resp_data = res.json()
                                answer = resp_data.get("answer", "")
                                st.markdown(answer)
                                st.session_state.chat_history.append({"role": "assistant", "content": answer})
                            else:
                                st.error(f"Error: {res.status_code} - {res.text}")
                        except Exception as e:
                            st.error(f"Request failed: {e}")

        # ----------------- Sub-Tab 3: Practice Quiz -----------------
        with tab_quiz:
            st.subheader("🎯 Practice Quiz")
            if st.button("Generate Quiz from Document", use_container_width=True):
                with st.spinner("Generating quiz questions..."):
                    try:
                        res = requests.post(
                            f"{API_URL.rstrip('/')}/api/quiz",
                            headers=get_auth_headers(),
                            json={"session_id": st.session_state.session_id},
                        )
                        if res.status_code == 200:
                            st.session_state.quiz_data = res.json().get("quiz", [])
                            st.session_state.quiz_submitted = False
                            st.rerun()
                        else:
                            st.error(f"Failed to generate quiz: {res.text}")
                    except Exception as e:
                        st.error(f"Error: {e}")

            if st.session_state.quiz_data:
                for idx, q in enumerate(st.session_state.quiz_data, 1):
                    st.markdown(f"**Q{idx}. {q.get('question')}**")
                    options = q.get("options", [])
                    st.radio("Options", options, key=f"q_{idx}", label_visibility="collapsed")

                    if st.session_state.quiz_submitted:
                        user_ans = st.session_state.get(f"q_{idx}")
                        correct_ans = q.get("answer") or q.get("correct_answer") or q.get("correctAnswer")
                        
                        if user_ans and correct_ans and user_ans.strip() == correct_ans.strip():
                            st.success(f"✅ Correct! Answer: {correct_ans}")
                        else:
                            st.error(f"❌ Incorrect! Correct Answer: {correct_ans}")
                    st.write("")

                if st.button("Submit Quiz", use_container_width=True):
                    st.session_state.quiz_submitted = True
                    score = 0
                    for idx, q in enumerate(st.session_state.quiz_data, 1):
                        selected = st.session_state.get(f"q_{idx}")
                        correct = q.get("answer") or q.get("correct_answer") or q.get("correctAnswer")
                        if selected and correct and selected.strip() == correct.strip():
                            score += 1
                    st.success(f"🎉 Final Score: {score}/{len(st.session_state.quiz_data)}")
                    st.rerun()

# ---------------------------------------------------------------------
# 5. View: 📂 My Saved Notes
# ---------------------------------------------------------------------

elif navigation == "📂 My Saved Notes":
    st.header("📂 My Saved Notes")
    st.write("Browse your saved study notes and summaries.")

    try:
        res = requests.get(f"{API_URL.rstrip('/')}/api/notes", headers=get_auth_headers())
        if res.status_code == 200:
            saved_notes = res.json()
            if not saved_notes:
                st.info("No saved notes found yet. Go to the Study Room to generate notes!")
            else:
                for note in saved_notes:
                    note_id = note.get("id")
                    with st.expander(f"📄 {note.get('title', 'Untitled')} - {note.get('created_at', '')[:10]}"):
                        st.markdown("### Executive Summary")
                        st.write(note.get("summary", "No summary available."))
                        st.markdown("### Full Notes")
                        st.markdown(note.get("notes", "No notes content."))
                        
                        st.markdown("---")
                        if st.button("🗑️ Delete Note", key=f"del_note_{note_id}"):
                            del_res = requests.delete(f"{API_URL.rstrip('/')}/api/notes/{note_id}", headers=get_auth_headers())
                            if del_res.status_code == 200:
                                st.success("Note deleted!")
                                st.rerun()
                            else:
                                st.error("Failed to delete note.")
        else:
            st.error("Failed to fetch saved notes.")
    except Exception as e:
        st.error(f"Error loading notes: {e}")
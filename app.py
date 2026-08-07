import streamlit as st
import os
import time
from google import genai
from google.genai import types

# 1. የገጽ ማስተካከያ (Page Configuration)
st.set_page_config(page_title="EduAI - Software Engineering Tutor", page_icon="💻", layout="wide")

# እጅግ ዘመናዊ፣ ጸጥ ያለ እና ማራኪ የቴክኖሎጂ ገጽታ ዲዛይን (Sleek Tech Dark Theme)
st.markdown("""
    <style>
    .stApp {
        background-color: #0f172a !important; /* Deep Slate dark background */
        color: #f8fafc !important; /* Off-white text */
        font-family: 'Inter', sans-serif;
    }
    section[data-testid="stSidebar"] {
        background-color: #1e293b !important;
        border-right: 1px solid #334155;
    }
    div[data-testid="stChatMessage"] {
        background-color: #1e293b !important;
        border: 1px solid #334155;
        border-radius: 12px;
    }
    h1, h2, h3 {
        color: #38bdf8 !important; /* Bright blue headers */
    }
    .stButton>button {
        background-color: #0284c7 !important;
        color: white !important;
        width: 100%;
        border-radius: 8px;
        border: none;
    }
    </style>
""", unsafe_allow_html=True)

# 2. የውይይትና የተጠቃሚ ማህደረ ትውስታ (Initialize Session States)
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "role" not in st.session_state:
    st.session_state.role = ""  # 'admin' ወይም 'student'
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "file_ref" not in st.session_state:
    st.session_state.file_ref = None
if "file_name" not in st.session_state:
    st.session_state.file_name = ""

# 3. 🔐 የተጠቃሚዎች መግቢያ በር (LOGIN SYSTEM)
if not st.session_state.logged_in:
    st.title("💻 EduAI - Software Engineering Learning Portal")
    st.write("Welcome! Please sign in with your credentials to access your courses.")
    
    username_input = st.text_input("Username (የተጠቃሚ ስም)፦")
    password_input = st.text_input("Password (የይለፍ ቃል)፦", type="password")
    
    if st.button("Sign In"):
        # አድሚን (ባለቤቱ/ሚኪያስ) መጽሐፍት የሚጭንበት አካውንት
        if username_input.lower() == "admin" and password_input == "admin123":
            st.session_state.logged_in = True
            st.session_state.role = "admin"
            st.success("Welcome back, Admin Mikias! Redirecting to Management Panel...")
            time.sleep(1)
            st.rerun()
        # ተማሪዎች ገብተው ብቻ የሚማሩበት አካውንት
        elif username_input.lower() == "student" and password_input == "student123":
            st.session_state.logged_in = True
            st.session_state.role = "student"
            st.success("Login successful! Welcome to your Software Engineering course...")
            time.sleep(1)
            st.rerun()
        else:
            st.error("⚠️ Invalid credentials. Try 'admin'/'admin123' or 'student'/'student123'.")
    st.stop()

# --- 💻 ዋናው መድረክ (የሚታየው ሎግ-ኢን ሲገባ ብቻ ነው) ---

st.sidebar.title(f"👤 {st.session_state.role.capitalize()} Portal")
if st.sidebar.button("Logout (ውጣ)"):
    st.session_state.logged_in = False
    st.session_state.role = ""
    st.session_state.chat_history = []
    st.session_state.file_ref = None
    st.session_state.file_name = ""
    st.rerun()

api_key = os.environ.get("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY") if "GEMINI_API_KEY" in st.secrets else None

if not api_key:
    api_key = st.sidebar.text_input("Enter Gemini API Key:", type="password")
else:
    st.sidebar.success("🔑 AI Engine Active!")

# 🅰️ አድሚን ክፍል (መጻሕፍት መጫኛ)
if st.session_state.role == "admin":
    st.title("⚙️ Admin Management Panel (ባለቤት/ሚኪያስ)")
    st.write("እዚህ ላይ መጽሐፍትን በመጫን ለተማሪዎችህ ኮርሶችን ማዘጋጀት ትችላለህ።")
    uploaded_file = st.file_uploader("የማስተማሪያ መጽሐፍ ይጫኑ (PDF/TXT):", type=["pdf", "txt"])
    
    if uploaded_file is not None and uploaded_file.name != st.session_state.file_name:
        st.session_state.file_ref = None
        st.session_state.file_name = uploaded_file.name
        st.session_state.chat_history = []
        if not uploaded_file:
        st.info("👈 እባክህ ለተማሪዎች የሚሆን መጽሐፍ በመጫን ኮርሱን አዘጋጅ።")
        st.stop()
        
    if not api_key:
        st.warning("⚠️ እባክህ ፋይሉን ሰርቨር ላይ ለመጫን የ Gemini API Key አስገባ።")
        st.stop()

    if st.session_state.file_ref is None:
        with st.spinner("መጽሐፉን በማንበብ እና በማዘጋጀት ላይ ነው..."):
            try:
                file_extension = os.path.splitext(uploaded_file.name)[1]
                temp_filename = f"temp_upload{file_extension}"
                with open(temp_filename, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                client = genai.Client(api_key=api_key)
                uploaded_file_ref = client.files.upload(file=temp_filename)
                st.session_state.file_ref = uploaded_file_ref
                
                if os.path.exists(temp_filename):
                    os.remove(temp_filename)
                st.success(f"📚 ኮርሱ በተሳካ ሁኔታ ተዘጋጅቷል! መጽሐፍ፦ {st.session_state.file_name}")
            except Exception as e:
                st.error(f"Error reading textbook: {e}")
                st.stop()

# 🅱️ ተማሪዎች ገጽ
else:
    st.title("🎓 Students E-Learning Dashboard")
    st.write("እንኳን በደህና መጣህ! እዚህ ገጽ ላይ መምህርህ ያዘጋጀልህን ኮርስ መማር ትችላለህ።")
    
    if st.session_state.file_ref is None:
        st.warning("⏳ መምህሩ እስካሁን ምንም አይነት የማስተማሪያ መጽሐፍ አልጫነም። እባክህ መምህሩ ኮርሱን እስኪያዘጋጅ ጠብቅ።")
        st.stop()
        
    st.success(f"📖 Active Course: {st.session_state.file_name}")

    st.markdown("### 🎓 Quick Study Options")
    col1, col2, col3 = st.columns(3)
    clicked_query = None

    with col1:
        if st.button("📝 Generate Course Syllabus"):
            clicked_query = "Based on this textbook, generate a structured week-by-week Software Engineering study syllabus."
    with col2:
        if st.button("❓ Create a Practice Quiz"):
            clicked_query = "Create 3 multiple-choice questions from the book to test my understanding of Software Engineering."
    with col3:
        if st.button("🔑 Explain Core Concepts"):
            clicked_query = "Summarize the top 5 most important Software Engineering concepts explained in this book."

    for role, message in st.session_state.chat_history:
        with st.chat_message(role):
            st.write(message)

    user_query = st.chat_input("የማይገባዎትን የሶፍትዌር ኢንጂነሪንግ ጥያቄ እዚህ ይጠይቁ...")
    if clicked_query:
        user_query = clicked_query

    if not user_query:
        st.stop()

    if not clicked_query:
        with st.chat_message("user"):
            st.write(user_query)
    st.session_state.chat_history.append(("user", user_query))

    with st.spinner("Tutor is thinking..."):
        try:
            client = genai.Client(api_key=api_key)
            system_prompt = """
            You are a world-class Professor of Software Engineering. 
            Your goal is to teach the user software engineering principles based strictly on the uploaded book.
            """
            config = types.GenerateContentConfig(system_instruction=system_prompt, temperature=0.3)
            response = client.models.generate_content(
                model='gemini-3.5-flash',
                contents=[st.session_state.file_ref, user_query],
                config=config
            )
            with st.chat_message("assistant"):
                st.write(response.text)
            st.session_state.chat_history.append(("assistant", response.text))
        except Exception as e:
            st.error(f"AI Error: {e}")
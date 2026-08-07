import streamlit as st
import os
import json
import time
import textwrap
import pypdf
from google import genai
from google.genai import types
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont
from moviepy import ImageClip, AudioFileClip

# 1. የገጽ ማስተካከያ (Page Configuration)
st.set_page_config(page_title="EduAI - SE Platform", page_icon="💻", layout="wide")

# የቴክኖሎጂ ገጽታ ዲዛይን (Sleek Tech Dark Theme)
st.markdown("""
    <style>
    .stApp {
        background-color: #0f172a !important; 
        color: #f8fafc !important; 
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
        color: #38bdf8 !important; 
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

# ============================================================
# 🔗 SHARED COURSE STORAGE (fixes admin <-> student disconnect)
#
# st.session_state is PRIVATE to each browser session — the
# Admin's session and a Student's session never share it.
# So we persist the processed course material to a small JSON
# file on disk. Every session (admin or student) reads from
# this file if its own in-memory copy is empty.
# ============================================================
COURSE_DATA_FILE = "course_data.json"
LECTURE_VIDEO_FILE = "lecture.mp4"


def save_course_data(file_name: str, book_text: str):
    """Persist the active course material so every session can see it."""
    with open(COURSE_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({"file_name": file_name, "book_text": book_text}, f)


def load_course_data():
    """Read the shared course material from disk, if it exists."""
    if os.path.exists(COURSE_DATA_FILE):
        try:
            with open(COURSE_DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("file_name", ""), data.get("book_text", "")
        except Exception:
            return "", ""
    return "", ""


def clear_course_data():
    if os.path.exists(COURSE_DATA_FILE):
        os.remove(COURSE_DATA_FILE)
    if os.path.exists(LECTURE_VIDEO_FILE):
        os.remove(LECTURE_VIDEO_FILE)


# 2. የውይይትና የተጠቃሚ ማህደረ ትውስታ (Initialize Session States)
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "role" not in st.session_state:
    st.session_state.role = ""  # 'admin' ወይም 'student'
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "book_text" not in st.session_state:
    st.session_state.book_text = ""
if "file_name" not in st.session_state:
    st.session_state.file_name = ""

# Every time the app reruns, pull in whatever course is currently
# published on disk if this session doesn't already have it loaded.
# This is what lets a Student session see what the Admin uploaded.
if not st.session_state.book_text:
    shared_file_name, shared_book_text = load_course_data()
    if shared_book_text:
        st.session_state.file_name = shared_file_name
        st.session_state.book_text = shared_book_text

# 3. 🔐 የተጠቃሚዎች መግቢያ በር (LOGIN SYSTEM)
if not st.session_state.logged_in:
    st.title("💻 EduAI - Software Engineering Learning Portal")
    st.write("Welcome! Please sign in with your credentials to access your courses.")

    username_input = st.text_input("Username (የተጠቃሚ ስም)፦")
    password_input = st.text_input("Password (የይለፍ ቃል)፦", type="password")

    if st.button("Sign In"):
        if username_input.lower() == "admin" and password_input == "admin123":
            st.session_state.logged_in = True
            st.session_state.role = "admin"
            st.success("Welcome back, Admin Mikias! Redirecting...")
            time.sleep(1)
            st.rerun()
        elif username_input.lower() == "student" and password_input == "student123":
            st.session_state.logged_in = True
            st.session_state.role = "student"
            st.success("Login successful! Welcome to your Software Engineering course...")
            time.sleep(1)
            st.rerun()
        else:
            st.error("⚠️ Invalid credentials. Try 'admin'/'admin123' or 'student'/'student123'.")
    st.stop()

# --- 💻 ዋናው መድረክ ---

st.sidebar.title(f"👤 {st.session_state.role.capitalize()} Portal")
if st.sidebar.button("Logout (ውጣ)"):
    st.session_state.logged_in = False
    st.session_state.role = ""
    st.session_state.chat_history = []
    # NOTE: we intentionally do NOT clear book_text/file_name here —
    # that's the shared course material, not this user's private data.
    st.rerun()

# ------------------------------------------------------------
# 🔑 API KEY RETRIEVAL — fixed operator-precedence bug.
# The original line:
#   os.environ.get(...) or st.secrets.get(...) if "X" in st.secrets else None
# parses as (env or secrets) IF key-in-secrets ELSE None — meaning it
# returned None whenever secrets.toml had no GEMINI_API_KEY entry,
# even if the environment variable was set. Also st.secrets can raise
# if no secrets file exists at all.
# ------------------------------------------------------------
api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
    except Exception:
        api_key = None

if not api_key:
    api_key = st.sidebar.text_input("Enter Gemini API Key:", type="password")
else:
    st.sidebar.success("🔑 AI Engine Active!")


# 🎥 ባለከፍተኛ ጥራት (1080p) ማራኪ ስላይድ የመሳያ እና ቪዲዮ ማዘጋጃ ፈንክሽን
def generate_ai_video(script_text, slide_title, output_filename=LECTURE_VIDEO_FILE):
    # ሀ. የድምፅ ፋይል በ gTTS ማዘጋጀት
    tts = gTTS(text=script_text, lang='en')
    audio_filename = "temp_lecture.mp3"
    tts.save(audio_filename)

    # ለ. ባለከፍተኛ ጥራት (Full HD 1920x1080) ስላይድ በ Pillow መሳል
    img = Image.new('RGB', (1920, 1080), color='#0b0f19')
    draw = ImageDraw.Draw(img)

    try:
        title_font = ImageFont.truetype("arial.ttf", 55)
        body_font = ImageFont.truetype("arial.ttf", 38)
        badge_font = ImageFont.truetype("arial.ttf", 28)
    except Exception:
        title_font = ImageFont.load_default()
        body_font = ImageFont.load_default()
        badge_font = ImageFont.load_default()

    draw.rectangle([(25, 25), (1895, 1055)], outline="#38bdf8", width=5)
    draw.text((80, 80), "💻 EDUAI PREMIER SOFTWARE ENGINEERING", fill="#38bdf8", font=badge_font)
    draw.text((80, 150), slide_title[:50].upper(), fill="#ffffff", font=title_font)
    draw.line([(80, 240), (1840, 240)], fill="#1e293b", width=3)

    wrapped_lines = textwrap.wrap(script_text, width=65)
    y_offset = 310
    for line in wrapped_lines:
        draw.text((80, y_offset), line, fill="#94a3b8", font=body_font)
        y_offset += 60

    draw.text((80, 970), "Course Curated by Mikias  |  Taught by AI Professor", fill="#475569", font=badge_font)

    image_filename = "temp_slide.png"
    img.save(image_filename)

    audio_clip = AudioFileClip(audio_filename)
    duration = audio_clip.duration

    video_clip = ImageClip(image_filename).with_duration(duration)
    video_clip = video_clip.with_audio(audio_clip)

    video_clip.write_videofile(output_filename, fps=24, codec="libx264")

    audio_clip.close()
    video_clip.close()

    if os.path.exists(audio_filename):
        os.remove(audio_filename)
    if os.path.exists(image_filename):
        os.remove(image_filename)


# 🅰️ አድሚን ክፍል (መጻሕፍት መጫኛ እና ቪዲዮ ማዘጋጃ)
if st.session_state.role == "admin":
    st.title("⚙️ Admin Management Panel (ባለቤት/ሚኪያስ)")
    st.write("እዚህ ላይ መጽሐፍትን በመጫን እና የ AI ቪዲዮ ትምህርቶችን ማመንጨት ትችላለህ።")

    if st.session_state.book_text:
        st.info(f"📚 Currently published course: **{st.session_state.file_name}**")
        if st.button("🗑️ Clear published course (remove for all students)"):
            clear_course_data()
            st.session_state.book_text = ""
            st.session_state.file_name = ""
            st.session_state.chat_history = []
            st.rerun()

    uploaded_file = st.file_uploader("የማስተማሪያ መጽሐፍ ይጫኑ (PDF/TXT):", type=["pdf", "txt"])

    if uploaded_file is not None and uploaded_file.name != st.session_state.file_name:
        st.session_state.book_text = ""
        st.session_state.file_name = uploaded_file.name
        st.session_state.chat_history = []

    if not uploaded_file:
        st.info("👈 እባክህ ለተማሪዎች የሚሆን መጽሐፍ በመጫን ኮርሱን አዘጋጅ።")
        st.stop()

    if not api_key:
        st.warning("⚠️ እባክህ ፋይሉን ሰርቨር ላይ ለመጫን የ Gemini API Key አስገባ።")
        st.stop()

    if st.session_state.book_text == "":
        with st.spinner("መጽሐፉን በማንበብ እና ጽሑፉን በማዘጋጀት ላይ ነው..."):
            try:
                if uploaded_file.name.endswith(".pdf"):
                    pdf_reader = pypdf.PdfReader(uploaded_file)
                    extracted_text = ""
                    for page in pdf_reader.pages[:100]:
                        extracted_text += page.extract_text() or ""
                    st.session_state.book_text = extracted_text
                else:
                    st.session_state.book_text = uploaded_file.read().decode("utf-8")

                # Publish to shared storage so student sessions can see it.
                save_course_data(st.session_state.file_name, st.session_state.book_text)

                st.success("ኮርሱ በተሳካ ሁኔታ ተዘጋጅቷል! (Published for all students)")
                st.rerun()
            except Exception as e:
                st.error(f"Error reading textbook: {e}")
                st.stop()

    st.success(f"📚 Active Course Material: {st.session_state.file_name}")

    st.markdown("### 🎥 AI Video Lecture Studio")
    if st.button("🎬 Generate AI Video Lecture (የቪዲዮ ማስተማሪያ በ AI አዘጋጅ)"):
        with st.spinner("AIው ጽሑፉን እያነበበ ቪዲዮ እያዘጋጀ ነው..."):
            try:
                client = genai.Client(api_key=api_key)
                script_prompt = f"""
                Write a concise, engaging, and professional 35-word educational lecture explaining the core concept of this book.
                Book Content:
                {st.session_state.book_text[:3000]}
                """
                response = client.models.generate_content(
                    model='gemini-3.5-flash',
                    contents=script_prompt
                )

                generate_ai_video(response.text, st.session_state.file_name)
                st.success("🎉 የቪዲዮ ማስተማሪያው በራስ-ሰር ተዘጋጅቷል! (Visible to all students)")
                st.rerun()
            except Exception as e:
                st.error(f"Error generating video: {e}")

    if os.path.exists(LECTURE_VIDEO_FILE):
        st.video(LECTURE_VIDEO_FILE)

# 🅱️ ተማሪዎች ገጽ
else:
    st.title("🎓 Students E-Learning Dashboard")
    st.write("እንኳን በደህና መጣህ! እዚህ ገጽ ላይ መምህርህ ያዘጋጀልህን ኮርስ መማር ትችላለህ።")

    if st.session_state.book_text == "":
        st.warning("⏳ መምህሩ እስካሁን ምንም አይነት የማስተማሪያ መጽሐፍ አልጫነም። እባክህ መምህሩ ኮርሱን እስኪያዘጋጅ ጠብቅ።")
        if st.button("🔄 Check again"):
            st.rerun()
        st.stop()

    st.success(f"📖 Active Course: {st.session_state.file_name}")

    if os.path.exists(LECTURE_VIDEO_FILE):
        st.markdown("### 🎬 Instructor's Video Lecture")
        st.video(LECTURE_VIDEO_FILE)

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

    if not api_key:
        st.error("⚠️ No Gemini API Key configured. Ask the admin to set GEMINI_API_KEY.")
        st.stop()

    with st.spinner("Tutor is thinking..."):
        try:
            client = genai.Client(api_key=api_key)
            system_prompt = """
            You are a world-class Professor of Software Engineering. 
            Your goal is to teach the user software engineering principles based strictly on the uploaded book.
            """
            config = types.GenerateContentConfig(system_instruction=system_prompt, temperature=0.3)

            prompt = f"""
            Answer the user's question based strictly on this document context. 
            Context:
            {st.session_state.book_text[:200000]}

            Question: {user_query}
            """

            response = client.models.generate_content(
                model='gemini-3.5-flash',
                contents=prompt,
                config=config
            )
            with st.chat_message("assistant"):
                st.write(response.text)
            st.session_state.chat_history.append(("assistant", response.text))
        except Exception as e:
            st.error(f"AI Error: {e}")
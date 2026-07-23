import streamlit as st
import os
import time
from google import genai
from google.genai import types

# 1. የገጽ ማስተካከያ (Page Configuration)
st.set_page_config(page_title="Ancient Wisdom AI Assistant", page_icon="📜", layout="wide")

# የጥንታዊ ብራና እና የአቡሻህር ገጽታ ውበት (Parchment & Ancient Theme UI)
st.markdown("""
    <style>
    /* የዋናው ገጽ የበስተጀርባ የብራና ቀለም */
    .stApp {
        background-color: #f6eedb !important; 
        color: #2e1a05 !important;
        font-family: 'Georgia', serif;
    }
    /* የጎን ማውጫ (Sidebar) ውበትና ቀለም */
    section[data-testid="stSidebar"] {
        background-color: #e6d5b3 !important;
        border-right: 2px solid #8c6239;
    }
    /* የውይይት ሳጥኖች (Chat Messages) ውበት */
    div[data-testid="stChatMessage"] {
        background-color: #fbf7ed !important;
        border: 1px solid #d4c3a3;
        border-radius: 12px;
        box-shadow: 1px 1px 5px rgba(0,0,0,0.05);
    }
    /* ርዕሶች እና ጽሑፎች */
    h1, h2, h3 {
        color: #5c3a21 !important;
        font-family: 'Georgia', serif;
    }
    /* በጎን በኩል ያሉ አዝራሮች (Quick Buttons) ውበት */
    .stButton>button {
        background-color: #8c6239 !important;
        color: white !important;
        border-radius: 8px !important;
        border: 1px solid #5c3a21 !important;
        width: 100%;
        text-align: left;
    }
    </style>
""", unsafe_allow_html=True)

# 2. የጎን ማስተካከያ ሳጥን (Sidebar Settings)
st.sidebar.title("📜 የጥንታዊ ብራና መቆጣጠሪያ")
st.sidebar.write("እዚህ ጋር ማስተካከያዎችን ያድርጉ።")

# አዲሱ ብልህ ኮድ (Smart API Key Loader) - በመጀመሪያ በሰርቨሩ ውስጥ የተደበቀ ቁልፍ ካለ ይፈትሻል
api_key = os.environ.get("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY") if "GEMINI_API_KEY" in st.secrets else None

# የተደበቀ ቁልፍ ከሌለ (ለምሳሌ በኮምፒውተርህ ላይ ስትሞክረው) ተጠቃሚው እንዲያስገባ ይጠይቃል
if not api_key:
    api_key = st.sidebar.text_input("Enter Gemini API Key:", type="password")
else:
    st.sidebar.success("🔑 AI Engine Active!")

uploaded_file = st.sidebar.file_uploader("የጥንታዊ መጻሕፍት/ብራናዎችን ይጫኑ (PDF/TXT):", type=["pdf", "txt"])

# የባለቤትነት ክሬዲት (Developer Credit)
st.sidebar.markdown("""
---
💻 Developed by Mikias  
*የጥንታውያን አባቶች እውቀት በዘመናዊ ቴክኖሎጂ*
""")

# 3. የውይይት ማህደረ ትውስታ (Initialize Session Memory)
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "file_ref" not in st.session_state:
    st.session_state.file_ref = None
if "file_name" not in st.session_state:
    st.session_state.file_name = ""

# አዲስ ፋይል ከተጫነ የድሮውን ማህደረ ትውስታ ማጽዳት
if uploaded_file is not None and uploaded_file.name != st.session_state.file_name:
    st.session_state.file_ref = None
    st.session_state.file_name = uploaded_file.name
    st.session_state.chat_history = []

# 4. ዋናው ገጽታ (Main Panel)
st.title("📜 የጥንታውያን አባቶች እውቀትና መንፈሳዊ ረዳት")
st.subheader("Ancient Wisdom & Spiritual AI Assistant (by Mikias)")
st.write("የተጫኑ ጥንታዊ የብራና መጻሕፍትን፣ የአቡሻህር የዘመን አቆጣጠርንና የግዕዝ ጥቅሶችን ለመተንተን ከታች ይጠይቁ።")

# መጽሐፍ ካልተጫነ እዚህ ጋር ይቆማል (Guard Clause 1)
if not uploaded_file:
    st.info("👈 እባክህ መጀመሪያ በጎን በኩል (Settings Panel) PDF ወይም TXT መጽሐፍ በመጫን ጀምር።")
    st.stop()

# API Key ካልገባ ማስጠንቀቂያ መስጠት (Guard Clause 2)
if not api_key:
    st.warning("⚠️ እባክህ መጽሐፉን ሰርቨር ላይ ለመጫን በጎን በኩል (Settings Panel) የ Gemini API Key አስገባ።")
    st.stop()

# 5. መጽሐፉን ወደ ጉግል ሰርቨር መጫን (በአንድ ፋይል አንድ ጊዜ ብቻ - የስም ስህተትን ለመከላከል የተስተካከለ)
if st.session_state.file_ref is None:
    with st.spinner("መጽሐፉን ወደ Google AI Cloud በመጫን ላይ ነው..."):
        try:
            # የፋይሉን መድረሻ (.pdf ወይም .txt) መለየት
            file_extension = os.path.splitext(uploaded_file.name)[1]
            
            # ዊንዶውስ የአማርኛ ስሞችን ሲያነብ እንዳይሳሳት ስሙን ወደ እንግሊዝኛ 'temp_upload' መቀየር
            temp_filename = f"temp_upload{file_extension}"
            
            # ፋይሉን በጊዜያዊነት መጻፍ
            with open(temp_filename, "wb") as f:
                f.write(uploaded_file.getbuffer())# የጉግል AI ደንበኛን መፍጠር እና ፋይሉን መጫን
            client = genai.Client(api_key=api_key)
            uploaded_file_ref = client.files.upload(file=temp_filename)
            
            st.session_state.file_ref = uploaded_file_ref
            
            # ጊዜያዊ ፋይሉን ማጥፋት
            if os.path.exists(temp_filename):
                os.remove(temp_filename)
                
            st.sidebar.success(f"በተሳካ ሁኔታ ተጭኗል: {st.session_state.file_name}")
        except Exception as e:
            st.error(f"Error uploading book to Gemini: {e}")
            st.stop()

st.success(f"📜 Manuscript '{st.session_state.file_name}' is loaded! ከታች ጥያቄ መጠየቅ ወይም የጎን አማራጮችን መጠቀም ትችላለህ።")

# 6. በአንድ ጠቅታ የሚሰሩ የጥንታዊ ጥያቄዎች አማራጭ (Quick Spiritual Buttons)
st.markdown("### ✨ ፈጣን የውይይት መጀመሪያዎች (Quick Queries)")
col1, col2, col3 = st.columns(3)

clicked_query = None

with col1:
    if st.button("📜 የግዕዝ ጽሑፍ ትንታኔና ትርጉም"):
        clicked_query = "በዚህ መጽሐፍ ውስጥ የሚገኙትን ዋና ዋና የግዕዝ ጥቅሶች ትርጉም፣ ሰዋሰዋዊ ትንታኔና አመጣጥ በዝርዝር አብራራልኝ።"
with col2:
    if st.button("🕊️ የጽሑፉ መንፈሳዊ ምስጢርና ትርጓሜ"):
        clicked_query = "የዚህን መጽሐፍ/ጽሑፍ ጥልቅ መንፈሳዊ ምስጢር፣ ምሳሌያዊ አነጋገሮችና የቀደሙ አባቶች ትርጓሜ በሰፊው አብራራልኝ።"
with col3:
    if st.button("🌌 ጥንታዊ ጥበብ (አቡሻህር) እና ዘመናዊ ሳይንስ"):
        clicked_query = "በዚህ መጽሐፍ ውስጥ የሚገኘውን ጥንታዊ እውቀት (ለምሳሌ እንደ አቡሻህር ያሉ የዘመንና የስነ-ኮከብ ስሌቶች) ከዘመናዊው ሳይንስና ቴክኖሎጂ ጋር በማነጻጸር አብራራልኝ።"

# ያለፉ የውይይት መልዕክቶችን ማሳየት
for role, message in st.session_state.chat_history:
    with st.chat_message(role):
        st.write(message)

# የጥያቄ መጻፊያ ሳጥን (Chat Input Box)
user_query = st.chat_input("Ask a question about the book...")

# ፈጣን አዝራር ከተጫነ እሱን እንደ መደበኛ ጥያቄ መውሰድ
if clicked_query:
    user_query = clicked_query

# ተጠቃሚው ጥያቄ ካልጻፈ እዚህ ጋር ይቆማል (Guard Clause 3)
if not user_query:
    st.stop()

# የተጠቃሚውን ጥያቄ በስክሪኑ ላይ ማሳየት እና ማዳን
if not clicked_query:  # ለአዝራሮች ደግመን እንዳናሳይ
    with st.chat_message("user"):
        st.write(user_query)
st.session_state.chat_history.append(("user", user_query))

# 7. የ AI ረዳቱን ምላሽ ማግኘት (በአውቶማቲክ የ 503 ስህተት መከላከያ)
with st.spinner("በመተንተን ላይ ነው..."):
    max_retries = 3
    
    # ጀሚኒ እራሱን በሚኪያስ ረዳትነት እንዲያስተዋውቅና በጥልቅ መንፈሳዊ እውቀት እንዲመልስ የተደረገ ትዕዛዝ (System Prompt)
    system_prompt = """
    You are 'Mikias's Ancient Wisdom AI Assistant', an exceptionally wise and respectful scholar in 
    ancient Ethiopian manuscripts, Orthodox Christian theology, Ge'ez language (ግዕዝ), and classical 
    computus/astronomy (አቡሻህር - Abushahar). 
    
    Your goal is to help the user translate, analyze, and deeply understand the uploaded manuscripts or books.
    Always connect this ancient, timeless wisdom with modern life, science, and technology in an insightful, positive way.
    Always write with deep respect, humility, and high academic/spiritual accuracy. 
    You are fully capable of reading and translating Ge'ez scripts into modern Amharic or English.
    """
    
    for attempt in range(max_retries):
        try:
            client = genai.Client(api_key=api_key)
            
            config = types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.3
            )
            
            prompt = f"Using the provided manuscript context, answer this question: {user_query}"
            
            response = client.models.generate_content(
                model='gemini-3.5-flash',
                contents=[st.session_state.file_ref, prompt],
                config=config
            )
            
            with st.chat_message("assistant"):
                st.write(response.text)
            st.session_state.chat_history.append(("assistant", response.text))
            break
            
        except Exception as e:
            if ("503" in str(e) or "overloaded" in str(e).lower()) and (attempt < max_retries - 1):
                st.warning(f"⚠️ ሰርቨሩ ስራ በዝቶበታል። በ3 ሰከንድ ውስጥ በድጋሚ ይሞከራል... (ሙከራ {attempt + 1}/{max_retries})")
                time.sleep(3)
            else:
                st.error(f"AI Error: {e}")
                break
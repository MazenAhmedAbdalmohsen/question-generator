import streamlit as st
import PyPDF2
import json
from io import BytesIO
import google.generativeai as genai

# Initialize session state
if 'questions' not in st.session_state:
    st.session_state.questions = []
if 'current_question' not in st.session_state:
    st.session_state.current_question = 0
if 'score' not in st.session_state:
    st.session_state.score = 0

# --- Google API Setup ---
def configure_google_api():
    # Check environment variables first (for deployment)
    if "GOOGLE_API_KEY" in os.environ:
        genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    # Check Streamlit secrets (for local testing)
    elif "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    else:
        st.error("Google API key not configured")
        return False
    return True

# Initialize the model
if configure_google_api():
    model = genai.GenerativeModel('gemini-pro')

# --- Helper Functions ---
def extract_text_from_pdf(uploaded_file):
    pdf_reader = PyPDF2.PdfReader(BytesIO(uploaded_file.read()))
    return "\n".join([page.extract_text() for page in pdf_reader.pages])

def generate_questions(text, total_questions, easy_pct, mid_pct, hard_pct):
    num_easy = int(total_questions * (easy_pct/100))
    num_mid = int(total_questions * (mid_pct/100))
    num_hard = total_questions - num_easy - num_mid
    
    prompt = f"""Generate {total_questions} multiple choice questions as a JSON array from this text:
{text[:3000]}

Format each question like this:
{{
    "question": "...",
    "options": ["A", "B", "C", "D"],
    "correct": "A",
    "difficulty": "easy|mid|hard",
    "explanation": "..."
}}

Requirements:
- {num_easy} easy questions (basic recall)
- {num_mid} medium questions (application)
- {num_hard} hard questions (analysis)
- Only return the JSON array, nothing else"""

    try:
        response = model.generate_content(prompt)
        # Extract JSON from response
        json_str = response.text.strip().replace('```json\n', '').replace('\n```', '')
        return json.loads(json_str)
    except Exception as e:
        st.error(f"Failed to generate questions: {str(e)}")
        return []

# --- UI Layout --- (Same as before, just updating the sidebar note)
st.set_page_config(page_title="Free Quiz Generator", layout="wide")
st.title("🔗 Public AI Question Generator")
st.caption("Powered by Google Gemini API")

with st.sidebar:
    st.markdown("### ⚙️ Quiz Settings")
    total_questions = st.slider("Total questions", 5, 20, 10)
    easy_pct = st.slider("% Easy", 0, 100, 30)
    mid_pct = st.slider("% Medium", 0, 100, 50)
    hard_pct = 100 - easy_pct - mid_pct
    st.metric("Hard questions", f"{hard_pct}%")

    st.markdown("""
    ### 🔒 Security Note
    Your Google API key is securely stored and never exposed to users.
    """)

# [Rest of the UI code remains exactly the same as previous version]
# [Keep all the input tabs, quiz display, and reset functionality]

# Footer
st.markdown("---")
st.caption("Note: Uses Google's Gemini API for question generation")

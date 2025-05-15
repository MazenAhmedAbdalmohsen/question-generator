import streamlit as st
import PyPDF2
import json
import requests
from io import BytesIO

# Initialize session state
if 'questions' not in st.session_state:
    st.session_state.questions = []
if 'current_question' not in st.session_state:
    st.session_state.current_question = 0
if 'score' not in st.session_state:
    st.session_state.score = 0

# --- Free LLM Setup ---
OLLAMA_WEBUI_URL = "https://ollama-webui-community.vercel.app"  # Public instance

def query_llm(prompt):
    try:
        response = requests.post(
            f"{OLLAMA_WEBUI_URL}/api/generate",
            json={
                "model": "llama2",  # Free model
                "prompt": prompt,
                "stream": False
            },
            timeout=30
        )
        return response.json().get("response", "")
    except Exception as e:
        st.error(f"LLM service busy. Try again later or use local Ollama.")
        return None

# --- Helper Functions ---
def extract_text_from_pdf(uploaded_file):
    pdf_reader = PyPDF2.PdfReader(BytesIO(uploaded_file.read()))
    return "\n".join([page.extract_text() for page in pdf_reader.pages])

def generate_questions(text, total_questions, easy_pct, mid_pct, hard_pct):
    prompt = f"""Generate {total_questions} MCQs as JSON list. Format:
[
  {{
    "question": "...",
    "options": ["A", "B", "C", "D"],
    "correct": "A",
    "difficulty": "easy|mid|hard",
    "explanation": "..."
  }}
]"""
    
    llm_response = query_llm(prompt)
    if llm_response:
        try:
            # Extract JSON from response
            json_str = llm_response[llm_response.find('['):llm_response.rfind(']')+1]
            return json.loads(json_str)
        except:
            return []

# --- UI Layout ---
st.set_page_config(page_title="Free Quiz Generator", layout="wide")
st.title("🔗 Public Quiz Generator")
st.caption("100% free - No API keys - Share this URL anywhere")

with st.sidebar:
    st.markdown("""
    **How it works:**
    - Uses community-hosted Ollama WebUI
    - No personal tokens needed
    - Works directly in browser
    """)

# ... [Rest of the code remains identical to previous version] ...

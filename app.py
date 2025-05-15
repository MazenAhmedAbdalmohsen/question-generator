import streamlit as st
import PyPDF2
import json
import requests
from io import BytesIO
import os

# Initialize session state
if 'questions' not in st.session_state:
    st.session_state.questions = []
if 'current_question' not in st.session_state:
    st.session_state.current_question = 0
if 'score' not in st.session_state:
    st.session_state.score = 0

# --- Secure Token Handling ---
def get_hf_token():
    # Check environment variables first (for deployment)
    if "HF_TOKEN" in os.environ:
        return os.environ["HF_TOKEN"]
    # Check Streamlit secrets (for local testing)
    elif "HF_TOKEN" in st.secrets:
        return st.secrets["HF_TOKEN"]
    else:
        st.error("API token not configured")
        return None

# --- Free Cloud LLM Setup ---
HF_API_URL = "https://api-inference.huggingface.co/models/google/flan-t5-xxl"  # Free tier model

def query_llm(prompt):
    token = get_hf_token()
    if not token:
        return None
        
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 1000,
            "temperature": 0.7,
            "do_sample": True
        }
    }
    
    try:
        response = requests.post(HF_API_URL, headers=headers, json=payload)
        
        # Handle API response
        if response.status_code == 200:
            return response.json()[0]['generated_text']
        elif response.status_code == 404:
            st.error("Model not found. Trying alternative...")
            return try_alternative_model(prompt)
        else:
            st.error(f"API Error {response.status_code}: {response.text[:200]}")
            return None
            
    except Exception as e:
        st.error(f"Connection failed: {str(e)}")
        return None

def try_alternative_model(prompt):
    """Fallback to another free model"""
    alt_url = "https://api-inference.huggingface.co/models/google/gemma-7b"
    try:
        response = requests.post(
            alt_url,
            headers={"Authorization": f"Bearer {get_hf_token()}"},
            json={"inputs": prompt}
        )
        return response.json()[0]['generated_text']
    except:
        st.error("All models unavailable. Try again later.")
        return None

# --- Helper Functions ---
def extract_text_from_pdf(uploaded_file):
    pdf_reader = PyPDF2.PdfReader(BytesIO(uploaded_file.read()))
    return "\n".join([page.extract_text() for page in pdf_reader.pages])

def generate_questions(text, total_questions, easy_pct, mid_pct, hard_pct):
    num_easy = int(total_questions * (easy_pct/100))
    num_mid = int(total_questions * (mid_pct/100))
    num_hard = total_questions - num_easy - num_mid
    
    prompt = f"""Generate {total_questions} MCQs as JSON list:
[
  {{
    "question": "...",
    "options": ["A", "B", "C", "D"],
    "correct": "A",
    "difficulty": "easy|mid|hard",
    "explanation": "..."
  }}
]
Requirements:
- {num_easy} easy (basic recall)
- {num_mid} medium (application)
- {num_hard} hard (analysis)
From this text:
{text[:3000]}"""
    
    llm_response = query_llm(prompt)
    if llm_response:
        try:
            # Extract JSON part from response
            json_str = llm_response.split('[', 1)[1].rsplit(']', 1)[0]
            return json.loads(f"[{json_str}]")
        except:
            st.error("Failed to parse questions. Trying again...")
            return []

# --- UI Layout ---
st.set_page_config(page_title="Free Quiz Generator", layout="wide")
st.title("🔗 Public AI Question Generator")
st.caption("Anyone with this URL can use it - No installations needed")

with st.sidebar:
    st.markdown("### ⚙️ Quiz Settings")
    total_questions = st.slider("Total questions", 5, 20, 10)
    easy_pct = st.slider("% Easy", 0, 100, 30)
    mid_pct = st.slider("% Medium", 0, 100, 50)
    hard_pct = 100 - easy_pct - mid_pct
    st.metric("Hard questions", f"{hard_pct}%")

    st.markdown("""
    ### 🔒 Security Note
    Your API token is securely stored and never exposed to users.
    """)

# Input Options
tab1, tab2 = st.tabs(["📁 Upload File", "✍️ Paste Text"])
input_text = ""

with tab1:
    uploaded_file = st.file_uploader("PDF or Text", type=["pdf","txt"])
    if uploaded_file:
        input_text = extract_text_from_pdf(uploaded_file) if uploaded_file.type == "application/pdf" else uploaded_file.getvalue().decode()

with tab2:
    input_text = st.text_area("Content", height=200, placeholder="Paste any text here...")

if st.button("Generate Quiz", disabled=not input_text.strip()):
    with st.spinner(f"Creating {total_questions} questions..."):
        questions = generate_questions(input_text, total_questions, easy_pct, mid_pct, hard_pct)
        if questions:
            st.session_state.questions = questions
            st.session_state.current_question = 0
            st.session_state.score = 0
            st.success(f"Generated {len(questions)} questions!")

# Quiz Display
if st.session_state.questions:
    st.divider()
    col1, col2 = st.columns([3,1])
    
    with col1:
        q = st.session_state.questions[st.session_state.current_question]
        
        st.markdown(f"#### Question {st.session_state.current_question+1}")
        st.markdown(f"**{q['question']}**")
        st.caption(f"Difficulty: {q['difficulty'].upper()}")
        
        selected = st.radio("Options:", q['options'], key=f"q{st.session_state.current_question}")
        
        if st.button("Submit Answer"):
            if selected == q['correct']:
                st.session_state.score += 1
                st.success("✅ Correct!")
            else:
                st.error(f"❌ Incorrect (Answer: {q['correct']})")
            
            st.markdown(f"**Explanation:** {q.get('explanation','')}")
            
            if st.session_state.current_question < len(st.session_state.questions)-1:
                st.session_state.current_question += 1
                st.rerun()
            else:
                st.balloons()
                st.success(f"🎉 Final Score: {st.session_state.score}/{len(st.session_state.questions)}")

    with col2:
        st.metric("Score", f"{st.session_state.score}/{len(st.session_state.questions)}")
        st.progress((st.session_state.current_question+1)/len(st.session_state.questions))
        
        with st.expander("📊 Stats"):
            diff_counts = {
                "Easy": sum(1 for q in st.session_state.questions if q['difficulty'] == 'easy'),
                "Medium": sum(1 for q in st.session_state.questions if q['difficulty'] == 'mid'),
                "Hard": sum(1 for q in st.session_state.questions if q['difficulty'] == 'hard')
            }
            st.bar_chart(diff_counts)

# Reset Button
if st.session_state.questions:
    if st.button("🔄 Start New Quiz"):
        st.session_state.questions = []
        st.rerun()

# Footer
st.markdown("---")
st.caption("Note: Uses free-tier Hugging Face models. May have rate limits during peak times.")

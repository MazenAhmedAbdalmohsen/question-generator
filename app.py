import streamlit as st
import PyPDF2
import json
from io import BytesIO
import google.generativeai as genai
import os

if 'questions' not in st.session_state:
    st.session_state.questions = []
if 'current_question' not in st.session_state:
    st.session_state.current_question = 0
if 'score' not in st.session_state:
    st.session_state.score = 0

def configure_google_api():
    if "GOOGLE_API_KEY" in os.environ:
        genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    elif "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    else:
        st.error("Google API key not configured")
        return False
    return True

if configure_google_api():
    model = genai.GenerativeModel('gemini-pro')

def extract_text_from_file(uploaded_file):
    if uploaded_file.type == "application/pdf":
        pdf_reader = PyPDF2.PdfReader(BytesIO(uploaded_file.read()))
        return "\n".join([page.extract_text() for page in pdf_reader.pages])
    elif uploaded_file.type == "text/plain":
        return uploaded_file.read().decode("utf-8")
    else:
        st.error("Unsupported file type. Please upload a PDF or text file.")
        return ""

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
        json_str = response.text.strip().replace('```json\n', '').replace('\n```', '')
        return json.loads(json_str)
    except Exception as e:
        st.error(f"Failed to generate questions: {str(e)}")
        return []

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
    st.markdown("### 🔒 Security Note\nYour Google API key is securely stored and never exposed to users.")

input_method = st.radio("Choose input method:", ("Upload PDF or Text File", "Enter Text"))

if input_method == "Upload PDF or Text File":
    uploaded_file = st.file_uploader("Upload a PDF or Text file", type=["pdf", "txt"])
    if uploaded_file:
        text = extract_text_from_file(uploaded_file)
        if text and st.button("Generate Q&A"):
            st.session_state.questions = generate_questions(text, total_questions, easy_pct, mid_pct, hard_pct)
else:
    user_text = st.text_area("Enter your text here:", height=200)
    if user_text and st.button("Generate Q&A"):
        st.session_state.questions = generate_questions(user_text, total_questions, easy_pct, mid_pct, hard_pct)

if st.session_state.questions:
    q = st.session_state.questions[st.session_state.current_question]
    st.write(f"**Question {st.session_state.current_question + 1} ({q['difficulty']}):** {q['question']}")
    for opt in q['options']:
        if st.button(opt, key=f"opt_{opt}"):
            if opt == q['correct']:
                st.success("Correct!")
                st.session_state.score += 1
            else:
                st.error(f"Incorrect. {q['explanation']}")
            st.session_state.current_question += 1
            if st.session_state.current_question >= len(st.session_state.questions):
                st.write(f"Quiz complete! Your score: {st.session_state.score}/{len(st.session_state.questions)}")
                st.session_state.current_question = 0
                st.session_state.questions = []
                st.session_state.score = 0
            st.rerun()

if st.button("Reset Quiz"):
    st.session_state.questions = []
    st.session_state.current_question = 0
    st.session_state.score = 0
    st.rerun()

st.markdown("---")
st.caption("Note: Uses Google's Gemini API for question generation")

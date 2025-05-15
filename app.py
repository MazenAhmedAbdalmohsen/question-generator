import streamlit as st
import PyPDF2
import json
import requests

# Initialize session state
if 'questions' not in st.session_state:
    st.session_state.questions = []
if 'current_question' not in st.session_state:
    st.session_state.current_question = 0
if 'score' not in st.session_state:
    st.session_state.score = 0

# --- Helper Functions ---
def extract_text_from_pdf(uploaded_file):
    pdf_reader = PyPDF2.PdfReader(uploaded_file)
    return "\n".join([page.extract_text() for page in pdf_reader.pages])

def generate_with_ollama(text, total_questions, easy_pct, mid_pct, hard_pct):
    num_easy = int(total_questions * (easy_pct/100))
    num_mid = int(total_questions * (mid_pct/100))
    num_hard = total_questions - num_easy - num_mid
    
    prompt = f"""Generate {total_questions} MCQs from this text:
{text[:3000]}

Format as JSON with:
- {num_easy} easy (recall)
- {num_mid} medium (application) 
- {num_hard} hard (analysis)
Each with: question, options[A-D], correct, difficulty, explanation"""

    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama2",
                "prompt": prompt,
                "format": "json",
                "stream": False
            }
        )
        return json.loads(response.json()["response"])
    except Exception as e:
        st.error(f"Error: {str(e)}. Make sure Ollama is running locally!")
        return []

# --- UI Layout ---
st.title("📚 Free AI Question Generator")
st.caption("No API keys needed - Uses local Ollama LLM")

with st.sidebar:
    st.markdown("### ⚙️ Quiz Settings")
    total_questions = st.slider("Total questions", 5, 20, 10)
    easy_pct = st.slider("% Easy", 0, 100, 30)
    mid_pct = st.slider("% Medium", 0, 100, 50)
    hard_pct = 100 - easy_pct - mid_pct
    st.metric("Hard questions", f"{hard_pct}%")

    st.markdown("""
    **First time setup:**
    1. Install [Ollama](https://ollama.ai/)
    2. Run in terminal:
    ```bash
    ollama pull llama2
    ollama serve
    ```
    """)

# Input Options
tab1, tab2 = st.tabs(["📁 Upload File", "✍️ Paste Text"])
input_text = ""

with tab1:
    uploaded_file = st.file_uploader("PDF or Text", type=["pdf","txt"])
    if uploaded_file:
        input_text = extract_text_from_pdf(uploaded_file) if uploaded_file.type == "application/pdf" else uploaded_file.getvalue().decode()

with tab2:
    input_text = st.text_area("Content", height=200)

if st.button("Generate Quiz") and input_text.strip():
    with st.spinner(f"Creating {total_questions} questions..."):
        questions = generate_with_ollama(input_text, total_questions, easy_pct, mid_pct, hard_pct)
        if questions:
            st.session_state.questions = questions
            st.session_state.current_question = 0
            st.session_state.score = 0
            st.success("Done!")

# Quiz Display
if st.session_state.questions:
    st.divider()
    q = st.session_state.questions[st.session_state.current_question]
    
    st.subheader(f"Q{st.session_state.current_question+1} ({q['difficulty'].upper()})")
    st.write(q['question'])
    
    selected = st.radio("Options:", q['options'], key=f"q{st.session_state.current_question}")
    
    if st.button("Submit"):
        if selected == q['correct']:
            st.session_state.score += 1
            st.success("Correct!")
        else:
            st.error(f"Wrong! Correct: {q['correct']}")
        st.info(f"💡 {q.get('explanation','')}")
        
        if st.session_state.current_question < len(st.session_state.questions)-1:
            st.session_state.current_question += 1
            st.rerun()
        else:
            st.balloons()
            st.success(f"Final Score: {st.session_state.score}/{len(st.session_state.questions)}")

    st.progress((st.session_state.current_question+1)/len(st.session_state.questions))

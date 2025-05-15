import streamlit as st
import openai
import json
import PyPDF2
from io import StringIO

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
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

def generate_questions(text, total_questions, easy_pct, mid_pct, hard_pct):
    num_easy = int(total_questions * (easy_pct/100))
    num_mid = int(total_questions * (mid_pct/100))
    num_hard = total_questions - num_easy - num_mid
    
    prompt = f"""
    Generate {total_questions} questions from this text:
    {text[:5000]}  # Limiting context window

    Requirements:
    - {num_easy} easy questions
    - {num_mid} medium difficulty (MID) questions
    - {num_hard} hard questions
    - Format as JSON list
    - Each question format:
    {{
        "question": "text",
        "options": ["A", "B", "C", "D"],
        "correct": "A",
        "difficulty": "easy|mid|hard",
        "explanation": "Brief explanation of answer"
    }}
    """
    
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    
    try:
        return json.loads(response.choices[0].message.content)
    except:
        st.error("Failed to generate questions. Please try again.")
        return []

# --- UI Layout ---
st.title("📚 AI Question Generator")
st.caption("Upload a PDF/text file and get customized quizzes")

with st.sidebar:
    st.subheader("🔑 API Configuration")
    openai_api_key = st.text_input("OpenAI API Key", type="password")
    openai.api_key = openai_api_key
    
    st.subheader("⚙️ Quiz Settings")
    total_questions = st.slider("Total questions", 5, 50, 20)
    easy_pct = st.slider("% Easy questions", 0, 100, 30)
    mid_pct = st.slider("% Medium questions", 0, 100, 50)
    hard_pct = 100 - easy_pct - mid_pct
    st.metric("Hard questions", f"{hard_pct}%")

# File Upload Section
uploaded_file = st.file_uploader("Upload PDF or text file", type=["pdf", "txt"])

if uploaded_file and openai_api_key:
    if st.button("✨ Generate Questions"):
        with st.spinner("Processing your document..."):
            if uploaded_file.type == "application/pdf":
                text = extract_text_from_pdf(uploaded_file)
            else:
                text = uploaded_file.getvalue().decode("utf-8")
            
            questions = generate_questions(
                text, 
                total_questions, 
                easy_pct, 
                mid_pct, 
                hard_pct
            )
            
            if questions:
                st.session_state.questions = questions
                st.session_state.current_question = 0
                st.session_state.score = 0
                st.success(f"Generated {len(questions)} questions!")

# Quiz Display Logic
if st.session_state.questions:
    st.divider()
    col1, col2 = st.columns([4,1])
    
    with col1:
        q = st.session_state.questions[st.session_state.current_question]
        st.subheader(f"Question {st.session_state.current_question + 1} ({q['difficulty'].upper()})")
        st.markdown(f"**{q['question']}**")
        
        selected = st.radio("Select answer:", q['options'], key=f"q{st.session_state.current_question}")
        
        if st.button("Submit Answer"):
            if selected == q['correct']:
                st.session_state.score += 1
                st.success("Correct!")
            else:
                st.error(f"Incorrect. The right answer is {q['correct']}")
            
            st.info(f"Explanation: {q.get('explanation', 'No explanation provided')}")
            
            if st.session_state.current_question < len(st.session_state.questions) - 1:
                st.session_state.current_question += 1
                st.experimental_rerun()
            else:
                st.balloons()
                st.success(f"🎯 Quiz Complete! Score: {st.session_state.score}/{len(st.session_state.questions)}")
    
    with col2:
        st.metric("Score", f"{st.session_state.score}/{len(st.session_state.questions)}")
        progress = st.session_state.current_question / len(st.session_state.questions)
        st.progress(progress)
        
        difficulty_counts = {
            "easy": sum(1 for q in st.session_state.questions if q['difficulty'] == 'easy'),
            "medium": sum(1 for q in st.session_state.questions if q['difficulty'] == 'mid'),
            "hard": sum(1 for q in st.session_state.questions if q['difficulty'] == 'hard')
        }
        
        st.caption("Difficulty distribution:")
        st.json(difficulty_counts)

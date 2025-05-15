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
if 'input_method' not in st.session_state:
    st.session_state.input_method = "file"

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
    Generate {total_questions} multiple-choice questions from this content:
    {text[:5000]}

    Requirements:
    - {num_easy} easy questions (basic recall)
    - {num_mid} medium questions (application)
    - {num_hard} hard questions (analysis)
    - Format as JSON list
    - Each question format:
    {{
        "question": "text",
        "options": ["A", "B", "C", "D"],
        "correct": "A",
        "difficulty": "easy|mid|hard",
        "explanation": "Brief explanation"
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
        st.error("Failed to generate questions. Please try with different content.")
        return []

# --- UI Layout ---
st.title("📚 AI Question Generator Pro")
st.caption("Generate quizzes from files OR direct text input")

with st.sidebar:
    st.subheader("🔑 API Configuration")
    openai_api_key = st.text_input("OpenAI API Key", type="password")
    openai.api_key = openai_api_key
    
    st.subheader("⚙️ Quiz Settings")
    total_questions = st.slider("Total questions", 5, 50, 15)
    easy_pct = st.slider("% Easy questions", 0, 100, 30)
    mid_pct = st.slider("% Medium questions", 0, 100, 50)
    hard_pct = 100 - easy_pct - mid_pct
    st.metric("Hard questions", f"{hard_pct}%")

# --- Input Selection Tabs ---
tab1, tab2 = st.tabs(["📁 File Upload", "✍️ Text Input"])

with tab1:
    uploaded_file = st.file_uploader("Upload PDF or text file", 
                                   type=["pdf", "txt"],
                                   help="Supports PDFs and text files")
    input_text = None
    if uploaded_file:
        if uploaded_file.type == "application/pdf":
            input_text = extract_text_from_pdf(uploaded_file)
        else:
            input_text = uploaded_file.getvalue().decode("utf-8")

with tab2:
    input_text = st.text_area("Or paste your text here", 
                            height=200,
                            placeholder="Paste any text content here...",
                            help="Minimum 100 characters recommended")

# --- Generation Logic ---
if st.button("✨ Generate Questions", 
            disabled=not (input_text and openai_api_key),
            help="Requires both content and API key"):
    
    with st.spinner(f"Generating {total_questions} questions..."):
        questions = generate_questions(
            input_text, 
            total_questions, 
            easy_pct, 
            mid_pct, 
            hard_pct
        )
        
        if questions:
            st.session_state.questions = questions
            st.session_state.current_question = 0
            st.session_state.score = 0
            st.success(f"Success! Generated {len(questions)} questions")

# --- Quiz Display ---
if st.session_state.questions:
    st.divider()
    col1, col2 = st.columns([4,1])
    
    with col1:
        q = st.session_state.questions[st.session_state.current_question]
        
        # Difficulty color coding
        diff_color = {
            "easy": "green",
            "mid": "orange",
            "hard": "red"
        }.get(q['difficulty'], "blue")
        
        st.subheader(f"Question {st.session_state.current_question + 1}")
        st.markdown(f"**Difficulty:** :{diff_color}[{q['difficulty'].upper()}]")
        st.markdown(f"**{q['question']}**")
        
        selected = st.radio("Options:", 
                          q['options'], 
                          key=f"q{st.session_state.current_question}")
        
        if st.button("Submit Answer"):
            if selected == q['correct']:
                st.session_state.score += 1
                st.success("✅ Correct!")
            else:
                st.error(f"❌ Incorrect (Correct: {q['correct']})")
            
            st.markdown(f"💡 **Explanation:** {q.get('explanation', 'Not available')}")
            
            if st.session_state.current_question < len(st.session_state.questions) - 1:
                st.session_state.current_question += 1
                st.experimental_rerun()
            else:
                st.balloons()
                st.success(f"""🎯 Quiz Complete! 
                          Score: **{st.session_state.score}/{len(st.session_state.questions)}**
                          ({round(st.session_state.score/len(st.session_state.questions)*100)}%)""")

    with col2:
        st.metric("Score", f"{st.session_state.score}/{len(st.session_state.questions)}")
        st.progress(st.session_state.current_question / len(st.session_state.questions))
        
        with st.expander("📊 Stats"):
            st.write(f"**Remaining:** {len(st.session_state.questions) - st.session_state.current_question}")
            st.write(f"**Correct:** {st.session_state.score}")
            
            diff_counts = {
                "Easy": sum(1 for q in st.session_state.questions if q['difficulty'] == 'easy'),
                "Medium": sum(1 for q in st.session_state.questions if q['difficulty'] == 'mid'),
                "Hard": sum(1 for q in st.session_state.questions if q['difficulty'] == 'hard')
            }
            st.bar_chart(diff_counts)

# --- Reset Button ---
if st.session_state.questions:
    if st.button("🔄 Start New Quiz"):
        st.session_state.questions = []
        st.session_state.current_question = 0
        st.session_state.score = 0
        st.rerun()

import streamlit as st
import json
import os
from text_processor import extract_text_from_pdf
from question_generator import generate_questions

# Initialize session state
if 'questions' not in st.session_state:
    st.session_state.questions = []
if 'current_question' not in st.session_state:
    st.session_state.current_question = 0
if 'score' not in st.session_state:
    st.session_state.score = 0

# Get Hugging Face API key from Streamlit secrets
hf_api_key = os.getenv("HF_API_KEY")

# UI Layout
st.title("📚 Free AI Question Generator")
st.caption("Generate MCQs from PDF or text - no API key needed!")

# Sidebar for settings
with st.sidebar:
    st.markdown("### ⚙️ Quiz Settings")
    num_easy = st.slider("Number of Easy Questions", 0, 10, 7)
    num_mid = st.slider("Number of Medium Questions", 0, 10, 7)
    st.markdown("**Instructions**: Upload a PDF or paste text to generate questions.")

# Input tabs
tab1, tab2 = st.tabs(["📁 Upload File", "✍️ Paste Text"])
input_text = ""

with tab1:
    uploaded_file = st.file_uploader("Upload PDF or Text", type=["pdf", "txt"])
    if uploaded_file:
        try:
            input_text = extract_text_from_pdf(uploaded_file) if uploaded_file.type == "application/pdf" else uploaded_file.getvalue().decode()
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")

with tab2:
    input_text = st.text_area("Paste Content", height=200)

# Generate quiz
if st.button("Generate Quiz") and input_text.strip():
    with st.spinner(f"Creating {num_easy + num_mid} questions..."):
        questions = generate_questions(input_text, num_easy, num_mid, hf_api_key)
        if questions and not any("error" in q for q in questions):
            st.session_state.questions = questions
            st.session_state.current_question = 0
            st.session_state.score = 0
            st.success("Quiz generated!")
        else:
            st.error("Failed to generate questions. Try again or check input text.")

# Quiz display
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
        st.info(f"💡 {q.get('explanation', 'No explanation provided')}")
        
        if st.session_state.current_question < len(st.session_state.questions) - 1:
            st.session_state.current_question += 1
            st.rerun()
        else:
            st.balloons()
            st.success(f"Final Score: {st.session_state.score}/{len(st.session_state.questions)}")

    st.progress((st.session_state.current_question + 1) / len(st.session_state.questions))

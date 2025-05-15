import streamlit as st
import openai
from text_processor import extract_text_from_pdf
from question_generator import generate_questions

# Initialize session state
if 'questions' not in st.session_state:
    st.session_state.questions = []
if 'current_question' not in st.session_state:
    st.session_state.current_question = 0
if 'score' not in st.session_state:
    st.session_state.score = 0

# Sidebar for API key
with st.sidebar:
    openai_api_key = st.text_input("OpenAI API Key", type="password")
    openai.api_key = openai_api_key

# Main interface
st.title("AI Question Generator")

uploaded_file = st.file_uploader("Upload PDF/text file", type=["pdf", "txt"])

if uploaded_file and openai_api_key:
    if st.button("Generate Questions"):
        if uploaded_file.type == "application/pdf":
            text = extract_text_from_pdf(uploaded_file)
        else:
            text = uploaded_file.getvalue().decode()
        
        questions = generate_questions(text)
        st.session_state.questions = questions
        st.session_state.current_question = 0
        st.session_state.score = 0

if st.session_state.questions:
    q = st.session_state.questions[st.session_state.current_question]
    
    st.subheader(f"Question {st.session_state.current_question + 1}")
    st.write(q['question'])
    
    selected = st.radio("Options", q['options'])
    
    if st.button("Submit"):
        if selected == q['correct']:
            st.session_state.score += 1
        if st.session_state.current_question < len(st.session_state.questions) - 1:
            st.session_state.current_question += 1
        else:
            st.success(f"Quiz Complete! Score: {st.session_state.score}/{len(st.session_state.questions)}")
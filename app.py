import streamlit as st
import PyPDF2
import json
from io import BytesIO
import google.generativeai as genai
import os
import time

# Initialize session state
if 'questions' not in st.session_state:
    st.session_state.questions = []
if 'current_question' not in st.session_state:
    st.session_state.current_question = 0
if 'score' not in st.session_state:
    st.session_state.score = 0
if 'user_answers' not in st.session_state:
    st.session_state.user_answers = []
if 'quiz_complete' not in st.session_state:
    st.session_state.quiz_complete = False

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
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        st.error(f"Failed to initialize model: {str(e)}")
        model = None

def extract_text_from_file(uploaded_file):
    if uploaded_file is None:
        return ""
    if uploaded_file.type == "application/pdf":
        pdf_reader = PyPDF2.PdfReader(BytesIO(uploaded_file.read()))
        return "\n".join([page.extract_text() for page in pdf_reader.pages])
    elif uploaded_file.type == "text/plain":
        return uploaded_file.read().decode("utf-8")
    else:
        st.error("Unsupported file type. Please upload a PDF or text file.")
        return ""

def generate_questions(text, total_questions, easy_pct, mid_pct, hard_pct):
    if not model:
        st.error("Model not initialized. Please check API key and model availability.")
        return []
    
    if not text.strip():
        st.error("Please provide some text content")
        return []
    
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
        if "429" in str(e):
            st.error("Quota exceeded. Please wait and try again.")
            time.sleep(26)
        else:
            st.error(f"Failed to generate questions: {str(e)}")
        return []

# Initialize text variable
text = ""

# Main app layout
st.set_page_config(page_title="AI Quiz Generator", layout="wide")
st.title("🧠 AI Quiz Generator")
st.caption("Powered by Google Gemini API")

with st.sidebar:
    st.markdown("### ⚙️ Quiz Settings")
    total_questions = st.slider("Total questions", 5, 20, 10)
    easy_pct = st.slider("% Easy", 0, 100, 30)
    mid_pct = st.slider("% Medium", 0, 100, 50)
    hard_pct = 100 - easy_pct - mid_pct
    st.metric("Hard questions", f"{hard_pct}%")
    st.markdown("### 🔒 Security Note\nYour API key is securely stored")

# Input method selection
input_method = st.radio("Choose input method:", ("📄 Upload PDF or Text File", "✍️ Enter Text"), horizontal=True)

if input_method == "📄 Upload PDF or Text File":
    uploaded_file = st.file_uploader("Upload a file", type=["pdf", "txt"])
    if uploaded_file:
        text = extract_text_from_file(uploaded_file)
else:
    text = st.text_area("Enter your text here:", height=200, value="")

# Only show Generate Quiz button if we have text
if text and text.strip():
    if st.button("✨ Generate Quiz"):
        with st.spinner("Generating questions..."):
            st.session_state.questions = generate_questions(text, total_questions, easy_pct, mid_pct, hard_pct)
            if st.session_state.questions:  # Only reset if questions were generated
                st.session_state.user_answers = []
                st.session_state.score = 0
                st.session_state.current_question = 0
                st.session_state.quiz_complete = False
else:
    st.warning("Please provide some text content or upload a file")

# Quiz display logic
if st.session_state.questions and not st.session_state.quiz_complete:
    q = st.session_state.questions[st.session_state.current_question]
    
    st.subheader(f"Question {st.session_state.current_question + 1} of {len(st.session_state.questions)}")
    st.markdown(f"**Difficulty:** :{'green' if q['difficulty'] == 'easy' else 'orange' if q['difficulty'] == 'mid' else 'red'}[{q['difficulty'].upper()}]")
    st.markdown(f"### {q['question']}")
    
    # Create a mapping of option letters to their values
    options_dict = {chr(65+i): opt for i, opt in enumerate(q['options'])}
    
    selected_key = st.radio("Select your answer:",
                          options=list(options_dict.keys()),
                          format_func=lambda x: f"{x}) {options_dict[x]}",
                          key=f"q_{st.session_state.current_question}")
    
    if st.button("Submit Answer"):
        is_correct = selected_key == q['correct']
        st.session_state.user_answers.append({
            "question": q['question'],
            "selected": options_dict[selected_key],
            "selected_key": selected_key,
            "correct": options_dict[q['correct']],
            "correct_key": q['correct'],
            "explanation": q['explanation'],
            "is_correct": is_correct
        })
        
        if is_correct:
            st.session_state.score += 1
            st.success("✅ Correct!")
        else:
            st.error(f"❌ Incorrect (Correct answer: {q['correct']}) {options_dict[q['correct']]}")
        
        st.markdown(f"**Explanation:** {q['explanation']}")
        
        # Move to next question or finish quiz
        if st.session_state.current_question < len(st.session_state.questions) - 1:
            st.session_state.current_question += 1
            st.rerun()
        else:
            st.session_state.quiz_complete = True
            st.rerun()

# Quiz completion screen
if st.session_state.quiz_complete:
    st.balloons()
    st.success("🎉 Quiz Completed!")
    
    # Score summary
    correct = st.session_state.score
    total = len(st.session_state.questions)
    percentage = (correct / total) * 100
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Correct Answers", f"{correct}/{total}")
    with col2:
        st.metric("Incorrect Answers", f"{total - correct}/{total}")
    with col3:
        st.metric("Percentage", f"{percentage:.1f}%")
    
    # Detailed review
    st.subheader("🔍 Detailed Review")
    for i, ans in enumerate(st.session_state.user_answers, 1):
        with st.expander(f"Question {i}: {ans['question']}", expanded=False):
            status = "✅ Correct" if ans['is_correct'] else "❌ Incorrect"
            st.markdown(f"**Your Answer:** {status} {ans['selected_key']}) {ans['selected']}")
            if not ans['is_correct']:
                st.markdown(f"**Correct Answer:** {ans['correct_key']}) {ans['correct']}")
            st.markdown(f"**Explanation:** {ans['explanation']}")
    
    if st.button("🔄 Start New Quiz"):
        st.session_state.questions = []
        st.session_state.current_question = 0
        st.session_state.score = 0
        st.session_state.user_answers = []
        st.session_state.quiz_complete = False
        st.rerun()

# Reset button (visible during quiz)
if st.session_state.questions and not st.session_state.quiz_complete:
    if st.button("🔁 Reset Quiz"):
        st.session_state.questions = []
        st.session_state.current_question = 0
        st.session_state.score = 0
        st.session_state.user_answers = []
        st.session_state.quiz_complete = False
        st.rerun()

st.markdown("---")
st.caption("Note: Uses Google's Gemini API for question generation")

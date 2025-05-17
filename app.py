import streamlit as st
import PyPDF2
import json
from io import BytesIO
import google.generativeai as genai
import os
import time
from datetime import datetime

# MUST BE FIRST COMMAND
st.set_page_config(page_title="AI Quiz Generator", layout="wide")

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
if 'text_content' not in st.session_state:
    st.session_state.text_content = ""
if 'language' not in st.session_state:
    st.session_state.language = "en"  # Default to English
if 'last_api_call' not in st.session_state:
    st.session_state.last_api_call = 0

# RTL CSS for Arabic
RTL_CSS = """
<style>
.rtl-text {
    direction: rtl;
    text-align: right;
    font-family: 'Arial', sans-serif;
}
.ltr-text {
    direction: ltr;
    text-align: left;
}
</style>
"""

# Language Selector
with st.sidebar:
    st.markdown("### 🌍 Language")
    lang = st.selectbox(
        "Select Language",
        ["English", "العربية"],
        index=0 if st.session_state.language == "en" else 1,
        key="lang_selector"
    )
    st.session_state.language = "ar" if lang == "العربية" else "en"
    st.markdown(RTL_CSS, unsafe_allow_html=True)

# Apply language direction
lang_dir = "rtl" if st.session_state.language == "ar" else "ltr"
st.markdown(f'<div class="{lang_dir}-text">', unsafe_allow_html=True)

# Translations dictionary
translations = {
    "en": {
        "title": "🧠 AI Quiz Generator",
        "caption": "Powered by Google Gemini API",
        "input_method_label": "Choose input method:",
        "upload_file_option": "📄 Upload PDF or Text File",
        "enter_text_option": "✍️ Enter Text",
        "upload_prompt": "Upload a file",
        "generate_questions_button": "✨ Generate Questions",
        "generating_questions": "Generating questions...",
        "file_uploaded_successfully": "File uploaded successfully!",
        "empty_file_warning": "The uploaded file appears to be empty",
        "question_format": "Question {current} of {total}",
        "difficulty": "Difficulty",
        "correct": "✅ Correct!",
        "incorrect": "❌ Incorrect (Correct answer: {correct})",
        "explanation": "Explanation:",
        "quiz_completed": "🎉 Quiz Completed!",
        "correct_answers": "Correct Answers",
        "incorrect_answers": "Incorrect Answers",
        "percentage": "Percentage",
        "performance_by_difficulty": "📊 Performance by Difficulty",
        "detailed_review": "🔍 Detailed Review",
        "start_new_quiz": "🔄 Start New Quiz",
        "reset_quiz": "🔁 Reset Quiz",
        "note": "Note: Uses Google's Gemini API for question generation",
        "select_answer": "Select your answer:",
        "submit_answer": "Submit Answer",
        "your_answer": "**Your Answer:**",
        "correct_answer": "**Correct Answer:**",
        "api_wait": "Please wait {seconds} seconds before generating more questions",
        "processing_file": "Processing file...",
        "api_error": "API Error: Please check your API key and try again",
        "loading_model": "Loading AI model..."
    },
    "ar": {
        "title": "🧠 منشئ الأسئلة بالذكاء الاصطناعي",
        "caption": "مدعوم بواسطة واجهة برمجة جوجل Gemini",
        "input_method_label": "اختر طريقة الإدخال:",
        "upload_file_option": "📄 رفع ملف PDF أو نصي",
        "enter_text_option": "✍️ إدخال النص",
        "upload_prompt": "رفع ملف",
        "generate_questions_button": "✨ إنشاء الأسئلة",
        "generating_questions": "جارٍ إنشاء الأسئلة...",
        "file_uploaded_successfully": "تم رفع الملف بنجاح!",
        "empty_file_warning": "يبدو أن الملف المرفوع فارغ",
        "question_format": "السؤال {current} من {total}",
        "difficulty": "الصعوبة",
        "correct": "✅ صحيح!",
        "incorrect": "❌ خطأ (الإجابة الصحيحة: {correct})",
        "explanation": "التفسير:",
        "quiz_completed": "🎉 اكتمل الاختبار!",
        "correct_answers": "الإجابات الصحيحة",
        "incorrect_answers": "الإجابات الخاطئة",
        "percentage": "النسبة المئوية",
        "performance_by_difficulty": "📊 الأداء حسب الصعوبة",
        "detailed_review": "🔍 مراجعة تفصيلية",
        "start_new_quiz": "🔄 بدء اختبار جديد",
        "reset_quiz": "🔁 إعادة تعيين الاختبار",
        "note": "ملاحظة: يستخدم واجهة برمجة جوجل Gemini لإنشاء الأسئلة",
        "select_answer": "اختر إجابتك:",
        "submit_answer": "إرسال الإجابة",
        "your_answer": "**إجابتك:**",
        "correct_answer": "**الإجابة الصحيحة:**",
        "api_wait": "الرجاء الانتظار {seconds} ثانية قبل إنشاء المزيد من الأسئلة",
        "processing_file": "جارٍ معالجة الملف...",
        "api_error": "خطأ في الواجهة البرمجية: يرجى التحقق من مفتاح API والمحاولة مرة أخرى",
        "loading_model": "جارٍ تحميل نموذج الذكاء الاصطناعي..."
    }
}

# Configure Gemini API with caching
@st.cache_resource(show_spinner=False)
def configure_google_api():
    t = translations[st.session_state.language]
    with st.spinner(t["loading_model"]):
        if "GOOGLE_API_KEY" in os.environ:
            genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
        elif "GOOGLE_API_KEY" in st.secrets:
            genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        else:
            st.error(t["api_error"])
            return None
        
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            return model
        except Exception as e:
            st.error(f"{t['api_error']}: {str(e)}")
            return None

model = configure_google_api()

# Extract text from file with progress
def extract_text_from_file(uploaded_file):
    t = translations[st.session_state.language]
    if uploaded_file is None:
        return ""
    
    progress_bar = st.progress(0, text=t["processing_file"])
    try:
        if uploaded_file.type == "application/pdf":
            pdf_reader = PyPDF2.PdfReader(BytesIO(uploaded_file.read()))
            text = ""
            total_pages = len(pdf_reader.pages)
            for i, page in enumerate(pdf_reader.pages):
                text += page.extract_text() + "\n"
                progress_bar.progress((i + 1) / total_pages)
            return text
        elif uploaded_file.type == "text/plain":
            return uploaded_file.read().decode("utf-8")
        else:
            st.error("Unsupported file type. Please upload a PDF or text file.")
            return ""
    except Exception as e:
        st.error(f"Error reading file: {str(e)}")
        return ""
    finally:
        progress_bar.empty()

# Generate quiz questions with rate limiting
def generate_questions(text, total_questions, easy_pct, mid_pct, hard_pct):
    t = translations[st.session_state.language]
    
    # Rate limiting - 20 requests per minute
    current_time = time.time()
    if current_time - st.session_state.last_api_call < 3:  # 3 second cooldown
        wait_time = int(3 - (current_time - st.session_state.last_api_call))
        st.warning(t["api_wait"].format(seconds=wait_time))
        time.sleep(wait_time)
    
    if not model:
        st.error(t["api_error"])
        return []
    
    if not text.strip():
        st.error("Please provide some text content")
        return []

    num_easy = int(total_questions * (easy_pct / 100))
    num_mid = int(total_questions * (mid_pct / 100))
    num_hard = total_questions - num_easy - num_mid

    if st.session_state.language == "ar":
        prompt = f"""قم بإنشاء {total_questions} أسئلة اختيار من متعدد بصيغة JSON من النص التالي:
{text[:3000]}
كل سؤال يجب أن يكون بهذا الشكل:
{{
    "question": "...",
    "options": ["A", "B", "C", "D"],
    "correct": "A",
    "difficulty": "easy|mid|hard",
    "explanation": "..."
}}
المتطلبات:
- {num_easy} أسئلة سهلة (استرجاع بسيط)
- {num_mid} أسئلة متوسطة (تطبيق)
- {num_hard} أسئلة صعبة (تحليل)
- لا تُرجع سوى المصفوفة JSON، ولا شيء آخر"""
    else:
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
        st.session_state.last_api_call = time.time()
        response = model.generate_content(prompt)
        json_str = response.text.strip().replace('```json\n', '').replace('\n```', '')
        return json.loads(json_str)
    except json.JSONDecodeError:
        st.error("Failed to parse questions. Please try again with different content.")
        return []
    except Exception as e:
        if "429" in str(e):
            st.error("Quota exceeded. Please wait and try again.")
            time.sleep(26)
        else:
            st.error(f"Failed to generate questions: {str(e)}")
        return []

# Main App UI
t = translations[st.session_state.language]
st.title(t["title"])
st.caption(t["caption"])

# Sidebar Settings
with st.sidebar:
    st.markdown("### ⚙️ Quiz Settings")
    total_questions = st.slider("Number of Questions" if st.session_state.language == "en" else "عدد الأسئلة", 
                               5, 20, 10)
    easy_pct = st.slider("% Easy" if st.session_state.language == "en" else "% سهلة", 0, 100, 30)
    mid_pct = st.slider("% Medium" if st.session_state.language == "en" else "% متوسطة", 0, 100, 50)
    hard_pct = 100 - easy_pct - mid_pct
    st.metric("Hard" if st.session_state.language == "en" else "صعبة", f"{hard_pct}%")
    st.markdown("### 🔒 Security Note")
    st.markdown("Your API key is securely stored" if st.session_state.language == "en" else "مفتاح API الخاص بك مخزن بأمان")

# Input Method Selection
input_method = st.radio(
    t["input_method_label"],
    [t["upload_file_option"], t["enter_text_option"]],
    horizontal=True,
    key="input_method"
)

# File Upload Section
if input_method == t["upload_file_option"]:
    uploaded_file = st.file_uploader(
        t["upload_prompt"],
        type=["pdf", "txt"],
        key="file_uploader"
    )
    if uploaded_file:
        st.session_state.text_content = extract_text_from_file(uploaded_file)
        if st.session_state.text_content.strip():
            st.success(t["file_uploaded_successfully"])
            if st.button(t["generate_questions_button"], key="generate_from_file"):
                with st.spinner(t["generating_questions"]):
                    st.session_state.questions = generate_questions(
                        st.session_state.text_content,
                        total_questions,
                        easy_pct,
                        mid_pct,
                        hard_pct
                    )
                    if st.session_state.questions:
                        st.session_state.user_answers = []
                        st.session_state.score = 0
                        st.session_state.current_question = 0
                        st.session_state.quiz_complete = False
                        st.rerun()
        else:
            st.warning(t["empty_file_warning"])
else:
    st.session_state.text_content = st.text_area(
        t["enter_text_option"],
        height=200,
        value=st.session_state.text_content,
        key="text_input"
    )
    if st.session_state.text_content.strip():
        if st.button(t["generate_questions_button"], key="generate_from_text"):
            with st.spinner(t["generating_questions"]):
                st.session_state.questions = generate_questions(
                    st.session_state.text_content,
                    total_questions,
                    easy_pct,
                    mid_pct,
                    hard_pct
                )
                if st.session_state.questions:
                    st.session_state.user_answers = []
                    st.session_state.score = 0
                    st.session_state.current_question = 0
                    st.session_state.quiz_complete = False
                    st.rerun()

# Quiz Display Logic
if st.session_state.questions and not st.session_state.quiz_complete:
    q = st.session_state.questions[st.session_state.current_question]
    st.subheader(t["question_format"].format(
        current=st.session_state.current_question + 1,
        total=len(st.session_state.questions)
    ))

    difficulty_color = 'green' if q['difficulty'] == 'easy' else 'orange' if q['difficulty'] == 'mid' else 'red'
    st.markdown(f"**{t['difficulty']}:** :{difficulty_color}[{q['difficulty'].upper()}]")

    question_text = q['question']
    if st.session_state.language == "ar":
        question_text = f'<div class="rtl-text">{q["question"]}</div>'
    st.markdown(f"### {question_text}", unsafe_allow_html=True)

    options_dict = {chr(65 + i): opt for i, opt in enumerate(q['options'])}

    def format_option(x):
        return f"{x}) {options_dict[x]}" if st.session_state.language == "en" else f"{options_dict[x]} ) {x}"

    selected_key = st.radio(
        t["select_answer"],
        options=list(options_dict.keys()),
        format_func=format_option,
        key=f"q_{st.session_state.current_question}"
    )

    if st.button(t["submit_answer"], key=f"submit_{st.session_state.current_question}"):
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
            st.success(t["correct"])
        else:
            st.error(t["incorrect"].format(correct=q['correct']))
        st.markdown(f"**{t['explanation']}** {q['explanation']}")
        if st.session_state.current_question < len(st.session_state.questions) - 1:
            st.session_state.current_question += 1
            st.rerun()
        else:
            st.session_state.quiz_complete = True
            st.rerun()

# Quiz Completion Screen
if st.session_state.quiz_complete:
    st.balloons()
    st.success(t["quiz_completed"])

    correct = st.session_state.score
    total = len(st.session_state.questions)
    percentage = (correct / total) * 100
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(t["correct_answers"], f"{correct}/{total}")
    with col2:
        st.metric(t["incorrect_answers"], f"{total - correct}/{total}")
    with col3:
        st.metric(t["percentage"], f"{percentage:.1f}%")

    st.subheader(t["performance_by_difficulty"])
    difficulty_stats = {"Easy": 0, "Medium": 0, "Hard": 0}
    for q, ans in zip(st.session_state.questions, st.session_state.user_answers):
        if ans['is_correct']:
            if q['difficulty'] == 'easy':
                difficulty_stats["Easy"] += 1
            elif q['difficulty'] == 'mid':
                difficulty_stats["Medium"] += 1
            elif q['difficulty'] == 'hard':
                difficulty_stats["Hard"] += 1
    st.bar_chart(difficulty_stats)

    st.subheader(t["detailed_review"])
    for i, ans in enumerate(st.session_state.user_answers, 1):
        with st.expander(f"Question {i}: {ans['question']}" if st.session_state.language == "en" else f"السؤال {i}: {ans['question']}", expanded=False):
            status = "✅ Correct" if ans['is_correct'] else "❌ Incorrect"
            st.markdown(f"{t['your_answer']} {status} {ans['selected_key']}) {ans['selected']}")
            if not ans['is_correct']:
                st.markdown(f"{t['correct_answer']} {ans['correct_key']}) {ans['correct']}")
            st.markdown(f"**Explanation:** {ans['explanation']}")

    if st.button(t["start_new_quiz"]):
        st.session_state.questions = []
        st.session_state.current_question = 0
        st.session_state.score = 0
        st.session_state.user_answers = []
        st.session_state.quiz_complete = False
        st.rerun()

# Reset Button
if st.session_state.questions and not st.session_state.quiz_complete:
    if st.button(t["reset_quiz"]):
        st.session_state.questions = []
        st.session_state.current_question = 0
        st.session_state.score = 0
        st.session_state.user_answers = []
        st.session_state.quiz_complete = False
        st.rerun()

st.markdown("---")
st.caption(t["note"])

# Close RTL div
st.markdown('</div>', unsafe_allow_html=True)

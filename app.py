import streamlit as st
import PyPDF2
import json
from io import BytesIO
import google.generativeai as genai
import os
import time
import arabic_reshaper
from bidi.algorithm import get_display
import re

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

# Language Direction CSS
RTL_CSS = """
<style>
.rtl-text {
    direction: rtl;
    text-align: right;
    font-family: 'Arial', 'Tahoma', sans-serif;
    font-size: 18px;
    line-height: 2.0;
}
.ltr-text {
    direction: ltr;
    text-align: left;
}
.rtl-input > div > input {
    direction: rtl;
    text-align: right;
}
</style>
"""

# Translations
translations = {
    "en": {
        "title": "🧠 AI Quiz Generator",
        "caption": "Powered by Google Gemini API",
        "input_method": "Choose input method:",
        "upload_file": "📄 Upload PDF or Text File",
        "enter_text": "✍️ Enter Text",
        "upload_prompt": "Upload a file",
        "text_prompt": "Enter your text here:",
        "empty_file": "The uploaded file appears to be empty",
        "generate_questions": "✨ Generate Questions",
        "generating_questions": "Generating questions...",
        "file_uploaded_successfully": "File uploaded successfully!",
        "question_format": "Question {current} of {total}",
        "difficulty": "Difficulty:",
        "easy": "Easy",
        "medium": "Medium",
        "hard": "Hard",
        "select_answer": "Select your answer:",
        "submit_answer": "Submit Answer",
        "correct": "✅ Correct!",
        "incorrect": "❌ Incorrect (Correct answer: {correct})",
        "explanation": "Explanation:",
        "quiz_completed": "🎉 Quiz Completed!",
        "correct_answers": "Correct Answers",
        "incorrect_answers": "Incorrect Answers",
        "percentage": "Percentage",
        "performance_by_difficulty": "📊 Performance by Difficulty",
        "detailed_review": "🔍 Detailed Review",
        "your_answer": "Your Answer:",
        "start_new_quiz": "🔄 Start New Quiz",
        "reset_quiz": "🔁 Reset Quiz",
        "note": "Note: Uses Google's Gemini API for question generation",
        "total_questions": "Total questions",
        "easy_pct": "% Easy",
        "medium_pct": "% Medium",
        "hard_questions": "Hard questions",
        "security_note": "### 🔒 Security Note",
        "api_note": "Your API key is securely stored",
    },
    "ar": {
        "title": "🧠 منشئ الاختبارات بالذكاء الاصطناعي",
        "caption": "مدعوم بواسطة Google Gemini API",
        "input_method": "اختر طريقة الإدخال:",
        "upload_file": "📄 رفع ملف PDF أو نصي",
        "enter_text": "✍️ إدخال النص",
        "upload_prompt": "رفع ملف",
        "text_prompt": "أدخل النص هنا:",
        "empty_file": "يبدو أن الملف المرفوع فارغ",
        "generate_questions": "✨ إنشاء الأسئلة",
        "generating_questions": "جارٍ إنشاء الأسئلة...",
        "file_uploaded_successfully": "تم رفع الملف بنجاح!",
        "question_format": "السؤال {current} من {total}",
        "difficulty": "الصعوبة:",
        "easy": "سهلة",
        "medium": "متوسطة",
        "hard": "صعبة",
        "select_answer": "اختر الإجابة:",
        "submit_answer": "إرسال الإجابة",
        "correct": "✅ صحيح!",
        "incorrect": "❌ غير صحيح (الإجابة الصحيحة: {correct})",
        "explanation": "التفسير:",
        "quiz_completed": "🎉 اكتمل الاختبار!",
        "correct_answers": "الإجابات الصحيحة",
        "incorrect_answers": "الإجابات الخاطئة",
        "percentage": "النسبة المئوية",
        "performance_by_difficulty": "📊 الأداء حسب الصعوبة",
        "detailed_review": "🔍 مراجعة تفصيلية",
        "your_answer": "إجابتك:",
        "start_new_quiz": "🔄 بدء اختبار جديد",
        "reset_quiz": "🔁 إعادة تعيين الاختبار",
        "note": "ملاحظة: يستخدم Google Gemini API لإنشاء الأسئلة",
        "total_questions": "عدد الأسئلة",
        "easy_pct": "% سهلة",
        "medium_pct": "% متوسطة",
        "hard_questions": "أسئلة صعبة",
        "security_note": "### 🔒 ملاحظة أمنية",
        "api_note": "مفتاح API الخاص بك مخزن بشكل آمن",
    }
}

def t(key):
    """Translation helper function"""
    return translations[st.session_state.language].get(key, key)

def format_arabic_text(text):
    """Format Arabic text for proper display"""
    if st.session_state.language == "ar":
        try:
            # Clean text first
            text = re.sub(r'[^\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF\s]', '', text)
            text = text.replace('ى', 'ي').replace('ك', 'ک')
            # Reshape and apply bidi algorithm
            reshaped_text = arabic_reshaper.reshape(text)
            return get_display(reshaped_text)
        except:
            return text
    return text

# Language Selector
with st.sidebar:
    st.markdown("### 🌍 " + ("Language" if st.session_state.language == "en" else "اللغة"))
    lang = st.selectbox(
        "Choose language" if st.session_state.language == "en" else "اختر اللغة",
        ["English", "العربية"],
        index=0 if st.session_state.language == "en" else 1,
        key="lang_selector",
        label_visibility="collapsed"
    )
    st.session_state.language = "ar" if lang == "العربية" else "en"
    st.markdown(RTL_CSS, unsafe_allow_html=True)

# Apply language direction
lang_dir = "rtl" if st.session_state.language == "ar" else "ltr"
st.markdown(f'<div class="{lang_dir}-text">', unsafe_allow_html=True)

def configure_google_api():
    if "GOOGLE_API_KEY" in os.environ:
        genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    elif "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    else:
        st.error(t("api_note"))
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
    try:
        if uploaded_file.type == "application/pdf":
            pdf_reader = PyPDF2.PdfReader(BytesIO(uploaded_file.read()))
            text = "\n".join([page.extract_text() for page in pdf_reader.pages])
            return format_arabic_text(text)
        elif uploaded_file.type == "text/plain":
            text = uploaded_file.read().decode("utf-8")
            return format_arabic_text(text)
        else:
            st.error(t("empty_file"))
            return ""
    except Exception as e:
        st.error(f"Error reading file: {str(e)}")
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
    
    if st.session_state.language == "ar":
        prompt = f"""قم بإنشاء {total_questions} أسئلة اختيار من متعدد باللغة العربية من هذا النص:
{text[:3000]}

يجب أن يكون كل سؤال بهذا الشكل:
{{
    "question": "...",
    "options": ["A", "B", "C", "D"],
    "correct": "A",
    "difficulty": "easy|mid|hard",
    "explanation": "..."
}}

المتطلبات:
- {num_easy} أسئلة سهلة (استدعاء أساسي)
- {num_mid} أسئلة متوسطة (تطبيق)
- {num_hard} أسئلة صعبة (تحليل)
- يجب أن تكون جميع الأسئلة باللغة العربية
- لا تقم بإرجاع أي شيء سوى مصفوفة JSON"""
    else:
        prompt = f"""Generate {total_questions} multiple choice questions in English from this text:
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
- All questions must be in English
- Only return the JSON array, nothing else"""

    try:
        response = model.generate_content(prompt)
        json_str = response.text.strip().replace('```json\n', '').replace('\n```', '')
        questions = json.loads(json_str)
        
        # Format Arabic text if needed
        if st.session_state.language == "ar":
            for q in questions:
                q['question'] = format_arabic_text(q['question'])
                q['options'] = [format_arabic_text(opt) for opt in q['options']]
                q['explanation'] = format_arabic_text(q['explanation'])
        return questions
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

# Main app layout
st.title(t("title"))
st.caption(t("caption"))

# Sidebar Settings
with st.sidebar:
    st.markdown(t("security_note"))
    st.markdown(t("api_note"))
    st.markdown("---")
    st.markdown("### ⚙️ " + ("Quiz Settings" if st.session_state.language == "en" else "إعدادات الاختبار"))
    total_questions = st.slider(t("total_questions"), 5, 20, 10)
    easy_pct = st.slider(t("easy_pct"), 0, 100, 30)
    mid_pct = st.slider(t("medium_pct"), 0, 100, 50)
    hard_pct = 100 - easy_pct - mid_pct
    st.metric(t("hard_questions"), f"{hard_pct}%")

# Input method selection
input_method = st.radio(
    t("input_method"),
    [t("upload_file"), t("enter_text")],
    horizontal=True,
    key="input_method"
)

# File Upload Section
if input_method == t("upload_file"):
    uploaded_file = st.file_uploader(
        t("upload_prompt"),
        type=["pdf", "txt"],
        key="file_uploader"
    )
    if uploaded_file:
        st.session_state.text_content = extract_text_from_file(uploaded_file)
        if st.session_state.text_content.strip():
            st.success(t("file_uploaded_successfully"))
            if st.button(t("generate_questions"), key="generate_from_file"):
                with st.spinner(t("generating_questions")):
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
            st.warning(t("empty_file"))
else:
    st.session_state.text_content = st.text_area(
        t("text_prompt"),
        height=200,
        value=st.session_state.text_content,
        key="text_input"
    )
    if st.session_state.text_content.strip():
        if st.button(t("generate_questions"), key="generate_from_text"):
            with st.spinner(t("generating_questions")):
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
    
    st.subheader(t("question_format").format(
        current=st.session_state.current_question + 1,
        total=len(st.session_state.questions)
    ))

    difficulty_map = {
        "easy": t("easy"),
        "mid": t("medium"),
        "hard": t("hard")
    }
    difficulty_color = {
        "easy": "green",
        "mid": "orange",
        "hard": "red"
    }.get(q['difficulty'], "blue")
    
    st.markdown(f"**{t('difficulty')}:** :{difficulty_color}[{difficulty_map.get(q['difficulty'], q['difficulty'])}]")
    
    question_text = q['question']
    if st.session_state.language == "ar":
        question_text = f'<div class="rtl-text">{question_text}</div>'
    st.markdown(f"### {question_text}", unsafe_allow_html=True)

    options_dict = {chr(65 + i): opt for i, opt in enumerate(q['options'])}

    selected_key = st.radio(
        t("select_answer"),
        options=list(options_dict.keys()),
        format_func=lambda x: f"{x}) {options_dict[x]}",
        key=f"q_{st.session_state.current_question}"
    )

    if st.button(t("submit_answer"), key=f"submit_{st.session_state.current_question}"):
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
            st.success(t("correct"))
        else:
            st.error(t("incorrect").format(correct=q['correct']))
        
        explanation_text = q['explanation']
        if st.session_state.language == "ar":
            explanation_text = f'<div class="rtl-text">{explanation_text}</div>'
        st.markdown(f"**{t('explanation')}** {explanation_text}", unsafe_allow_html=True)
        
        if st.session_state.current_question < len(st.session_state.questions) - 1:
            st.session_state.current_question += 1
            st.rerun()
        else:
            st.session_state.quiz_complete = True
            st.rerun()

# Quiz Completion Screen
if st.session_state.quiz_complete:
    st.balloons()
    st.success(t("quiz_completed"))

    correct = st.session_state.score
    total = len(st.session_state.questions)
    percentage = (correct / total) * 100
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(t("correct_answers"), f"{correct}/{total}")
    with col2:
        st.metric(t("incorrect_answers"), f"{total - correct}/{total}")
    with col3:
        st.metric(t("percentage"), f"{percentage:.1f}%")

    st.subheader(t("performance_by_difficulty"))
    difficulty_stats = {
        t("easy"): 0,
        t("medium"): 0,
        t("hard"): 0
    }
    for q, ans in zip(st.session_state.questions, st.session_state.user_answers):
        if ans['is_correct']:
            difficulty_stats[difficulty_map.get(q['difficulty'], q['difficulty'])] += 1
    st.bar_chart(difficulty_stats)

    st.subheader(t("detailed_review"))
    for i, ans in enumerate(st.session_state.user_answers, 1):
        with st.expander(f"{t('question_format').format(current=i, total=len(st.session_state.questions))}: {ans['question']}", expanded=False):
            status = t("correct") if ans['is_correct'] else t("incorrect").format(correct=ans['correct_key'])
            st.markdown(f"**{t('your_answer')}** {status} {ans['selected_key']}) {ans['selected']}")
            if not ans['is_correct']:
                st.markdown(f"**{t('correct')}** {ans['correct_key']}) {ans['correct']}")
            explanation_text = ans['explanation']
            if st.session_state.language == "ar":
                explanation_text = f'<div class="rtl-text">{explanation_text}</div>'
            st.markdown(f"**{t('explanation')}** {explanation_text}", unsafe_allow_html=True)

    if st.button(t("start_new_quiz")):
        st.session_state.questions = []
        st.session_state.current_question = 0
        st.session_state.score = 0
        st.session_state.user_answers = []
        st.session_state.quiz_complete = False
        st.rerun()

# Reset Button
if st.session_state.questions and not st.session_state.quiz_complete:
    if st.button(t("reset_quiz")):
        st.session_state.questions = []
        st.session_state.current_question = 0
        st.session_state.score = 0
        st.session_state.user_answers = []
        st.session_state.quiz_complete = False
        st.rerun()

st.markdown("---")
st.caption(t("note"))

# Close the language direction div
st.markdown('</div>', unsafe_allow_html=True)

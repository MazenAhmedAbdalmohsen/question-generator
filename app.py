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
if 'text_content' not in st.session_state:
    st.session_state.text_content = ""
if 'language' not in st.session_state:
    st.session_state.language = "en"  # Default to English

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
    try:
        if uploaded_file.type == "application/pdf":
            pdf_reader = PyPDF2.PdfReader(BytesIO(uploaded_file.read()))
            return "\n".join([page.extract_text() for page in pdf_reader.pages])
        elif uploaded_file.type == "text/plain":
            return uploaded_file.read().decode("utf-8")
        else:
            st.error("Unsupported file type. Please upload a PDF or text file.")
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

    num_easy = int(total_questions * (easy_pct / 100))
    num_mid = int(total_questions * (mid_pct / 100))
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

# Language Direction CSS
RTL_CSS = """
<style>
.rtl-text {
    direction: rtl;
    text-align: right;
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
        "Choose language" if st.session_state.language == "en" else "اختر اللغة",
        ["English", "العربية"],
        index=0 if st.session_state.language == "en" else 1,
        key="lang_selector"
    )
    st.session_state.language = "ar" if lang == "العربية" else "en"
    st.markdown(RTL_CSS, unsafe_allow_html=True)

# Apply language direction
lang_dir = "rtl" if st.session_state.language == "ar" else "ltr"
st.markdown(f'<div class="{lang_dir}-text">', unsafe_allow_html=True)

# Main app layout
st.set_page_config(page_title="AI Quiz Generator", layout="wide")
st.title("🧠 AI Quiz Generator")
st.caption("Powered by Google Gemini API")

# Sidebar Settings
with st.sidebar:
    st.markdown("### ⚙️ Quiz Settings")
    total_questions = st.slider("Total questions" if st.session_state.language == "en" else "عدد الأسئلة", 5, 20, 10)
    easy_pct = st.slider("% Easy" if st.session_state.language == "en" else "% سهلة", 0, 100, 30)
    mid_pct = st.slider("% Medium" if st.session_state.language == "en" else "% متوسطة", 0, 100, 50)
    hard_pct = 100 - easy_pct - mid_pct
    st.metric("Hard questions" if st.session_state.language == "en" else "أسئلة صعبة", f"{hard_pct}%")
    st.markdown("### 🔒 Security Note" if st.session_state.language == "en" else "### 🔒 ملاحظة الأمان")
    st.markdown("Your API key is securely stored" if st.session_state.language == "en" else "يتم تخزين مفتاح API الخاص بك بأمان")

# Input method selection
input_method = st.radio(
    "Choose input method:" if st.session_state.language == "en" else "اختر طريقة الإدخال:",
    ("📄 Upload PDF or Text File" if st.session_state.language == "en" else "📄 رفع ملف PDF أو نص",
     "✍️ Enter Text" if st.session_state.language == "en" else "✍️ أدخل النص"),
    horizontal=True,
    key="input_method"
)

# File Upload Section
if input_method == "📄 Upload PDF or Text File":
    uploaded_file = st.file_uploader(
        "Upload a file" if st.session_state.language == "en" else "ارفع ملفًا",
        type=["pdf", "txt"], key="file_uploader"
    )
    if uploaded_file:
        st.session_state.text_content = extract_text_from_file(uploaded_file)
        if st.session_state.text_content.strip():
            st.success("File uploaded successfully!" if st.session_state.language == "en" else "تم رفع الملف بنجاح!")
            if st.button("✨ Generate Questions" if st.session_state.language == "en" else "✨ إنشاء أسئلة", key="generate_from_file"):
                with st.spinner("Generating questions..." if st.session_state.language == "en" else "جارٍ إنشاء الأسئلة..."):
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
            st.warning("The uploaded file appears to be empty" if st.session_state.language == "en" else "يبدو أن الملف الذي تم رفعه فارغ")
else:
    st.session_state.text_content = st.text_area(
        "Enter your text here:" if st.session_state.language == "en" else "أدخل النص هنا:",
        height=200,
        value=st.session_state.text_content,
        key="text_input"
    )
    if st.session_state.text_content.strip():
        if st.button("✨ Generate Questions" if st.session_state.language == "en" else "✨ إنشاء أسئلة", key="generate_from_text"):
            with st.spinner("Generating questions..." if st.session_state.language == "en" else "جارٍ إنشاء الأسئلة..."):
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
    st.subheader(f"Question {st.session_state.current_question + 1} of {len(st.session_state.questions)}"
                 if st.session_state.language == "en" else
                 f"السؤال {st.session_state.current_question + 1} من {len(st.session_state.questions)}")

    difficulty_color = 'green' if q['difficulty'] == 'easy' else 'orange' if q['difficulty'] == 'mid' else 'red'
    st.markdown(f"**Difficulty:** :{difficulty_color}[{q['difficulty'].upper()}]")

    question_text = q['question']
    if st.session_state.language == "ar":
        question_text = f'<div class="rtl-text">{q["question"]}</div>'
    st.markdown(f"### {question_text}", unsafe_allow_html=True)

    options_dict = {chr(65 + i): opt for i, opt in enumerate(q['options'])}

    def format_option(x):
        return f"{x}) {options_dict[x]}" if st.session_state.language == "en" else f"{options_dict[x]} ) {x}"

    selected_key = st.radio(
        "Select your answer:" if st.session_state.language == "en" else "اختر إجابتك:",
        options=list(options_dict.keys()),
        format_func=format_option,
        key=f"q_{st.session_state.current_question}"
    )

    if st.button("Submit Answer" if st.session_state.language == "en" else "إرسال الإجابة", key=f"submit_{st.session_state.current_question}"):
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
            st.success("✅ Correct!" if st.session_state.language == "en" else "✅ صحيح!")
        else:
            st.error(f"❌ Incorrect (Correct answer: {q['correct']}) {options_dict[q['correct']]}" if st.session_state.language == "en" else f"❌ خطأ (الإجابة الصحيحة: {q['correct']} {options_dict[q['correct']]})")
        st.markdown(f"**Explanation:** {q['explanation']}")
        if st.session_state.current_question < len(st.session_state.questions) - 1:
            st.session_state.current_question += 1
            st.rerun()
        else:
            st.session_state.quiz_complete = True
            st.rerun()

# Quiz Completion Screen
if st.session_state.quiz_complete:
    st.balloons()
    st.success("🎉 Quiz Completed!" if st.session_state.language == "en" else "🎉 اكتمل الاختبار!")

    correct = st.session_state.score
    total = len(st.session_state.questions)
    percentage = (correct / total) * 100
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Correct Answers" if st.session_state.language == "en" else "الإجابات الصحيحة", f"{correct}/{total}")
    with col2:
        st.metric("Incorrect Answers" if st.session_state.language == "en" else "الإجابات الخاطئة", f"{total - correct}/{total}")
    with col3:
        st.metric("Percentage" if st.session_state.language == "en" else "النسبة المئوية", f"{percentage:.1f}%")

    st.subheader("📊 Performance by Difficulty" if st.session_state.language == "en" else "📊 الأداء حسب الصعوبة")
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

    st.subheader("🔍 Detailed Review" if st.session_state.language == "en" else "🔍 مراجعة تفصيلية")
    for i, ans in enumerate(st.session_state.user_answers, 1):
        with st.expander(f"Question {i}: {ans['question']}" if st.session_state.language == "en" else f"السؤال {i}: {ans['question']}", expanded=False):
            status = "✅ Correct" if ans['is_correct'] else "❌ Incorrect"
            st.markdown(f"**Your Answer:** {status} {ans['selected_key']}) {ans['selected']}")
            if not ans['is_correct']:
                st.markdown(f"**Correct Answer:** {ans['correct_key']}) {ans['correct']}")
            st.markdown(f"**Explanation:** {ans['explanation']}")

    if st.button("🔄 Start New Quiz" if st.session_state.language == "en" else "🔄 بدء اختبار جديد"):
        st.session_state.questions = []
        st.session_state.current_question = 0
        st.session_state.score = 0
        st.session_state.user_answers = []
        st.session_state.quiz_complete = False
        st.rerun()

# Reset Button
if st.session_state.questions and not st.session_state.quiz_complete:
    if st.button("🔁 Reset Quiz" if st.session_state.language == "en" else "🔁 إعادة تعيين الاختبار"):
        st.session_state.questions = []
        st.session_state.current_question = 0
        st.session_state.score = 0
        st.session_state.user_answers = []
        st.session_state.quiz_complete = False
        st.rerun()

st.markdown("---")
st.caption("Note: Uses Google's Gemini API for question generation" if st.session_state.language == "en" else "ملاحظة: يستخدم هذا التطبيق واجهة برمجة جوجل Gemini لإنشاء الأسئلة")

# Close the language direction div
st.markdown('</div>', unsafe_allow_html=True)

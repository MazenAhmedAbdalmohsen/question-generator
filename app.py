import streamlit as st
import PyPDF2
import json
from io import BytesIO
import google.generativeai as genai
import os
import time
import arabic_reshaper
from bidi.algorithm import get_display
from arabic_support_tools import fix_arabic_text  # Custom function for Arabic text cleaning

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
    st.session_state.language = "English"

# Custom Arabic text processing
def format_arabic_text(text):
    """Clean and properly format Arabic text"""
    try:
        # Clean text first
        text = fix_arabic_text(text)
        # Reshape and apply bidi algorithm
        reshaped_text = arabic_reshaper.reshape(text)
        return get_display(reshaped_text)
    except:
        return text

def configure_google_api():
    if "GOOGLE_API_KEY" in os.environ:
        genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    elif "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    else:
        error_msg = "Google API key not configured"
        st.error(format_arabic_text(error_msg) if st.session_state.language == "Arabic" else error_msg)
        return False
    return True

if configure_google_api():
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        error_msg = f"Failed to initialize model: {str(e)}"
        st.error(format_arabic_text(error_msg) if st.session_state.language == "Arabic" else error_msg)
        model = None

def extract_text_from_file(uploaded_file):
    if uploaded_file is None:
        return ""
    try:
        if uploaded_file.type == "application/pdf":
            pdf_reader = PyPDF2.PdfReader(BytesIO(uploaded_file.read()))
            text = "\n".join([page.extract_text() for page in pdf_reader.pages])
            return format_arabic_text(text) if st.session_state.language == "Arabic" else text
        elif uploaded_file.type == "text/plain":
            text = uploaded_file.read().decode("utf-8")
            return format_arabic_text(text) if st.session_state.language == "Arabic" else text
        else:
            error_msg = "Unsupported file type. Please upload a PDF or text file."
            st.error(format_arabic_text(error_msg) if st.session_state.language == "Arabic" else error_msg)
            return ""
    except Exception as e:
        error_msg = f"Error reading file: {str(e)}"
        st.error(format_arabic_text(error_msg) if st.session_state.language == "Arabic" else error_msg)
        return ""

def generate_questions(text, total_questions, easy_pct, mid_pct, hard_pct):
    if not model:
        error_msg = "Model not initialized. Please check API key and model availability."
        st.error(format_arabic_text(error_msg) if st.session_state.language == "Arabic" else error_msg)
        return []
    
    if not text.strip():
        error_msg = "Please provide some text content"
        st.error(format_arabic_text(error_msg) if st.session_state.language == "Arabic" else error_msg)
        return []
    
    num_easy = int(total_questions * (easy_pct/100))
    num_mid = int(total_questions * (mid_pct/100))
    num_hard = total_questions - num_easy - num_mid
    
    language_instruction = "in Arabic" if st.session_state.language == "Arabic" else "in English"
    
    prompt = f"""Generate {total_questions} multiple choice questions {language_instruction} as a JSON array from this text:
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
- Only return the JSON array, nothing else
- All content must be in {st.session_state.language}
- For Arabic: Ensure proper diacritics and formatting
- Questions should be clear and easy to read"""

    try:
        response = model.generate_content(prompt)
        json_str = response.text.strip().replace('```json\n', '').replace('\n```', '')
        questions = json.loads(json_str)
        
        # Format Arabic text if needed
        if st.session_state.language == "Arabic":
            for q in questions:
                q['question'] = format_arabic_text(q['question'])
                q['options'] = [format_arabic_text(opt) for opt in q['options']]
                q['explanation'] = format_arabic_text(q['explanation'])
        return questions
    except json.JSONDecodeError:
        error_msg = "Failed to parse questions. Please try again with different content."
        st.error(format_arabic_text(error_msg) if st.session_state.language == "Arabic" else error_msg)
        return []
    except Exception as e:
        if "429" in str(e):
            error_msg = "Quota exceeded. Please wait and try again."
            st.error(format_arabic_text(error_msg) if st.session_state.language == "Arabic" else error_msg)
            time.sleep(26)
        else:
            error_msg = f"Failed to generate questions: {str(e)}"
            st.error(format_arabic_text(error_msg) if st.session_state.language == "Arabic" else error_msg)
        return []

# Main app layout
st.set_page_config(
    page_title=format_arabic_text("منشئ الاختبارات بالذكاء الاصطناعي") if st.session_state.language == "Arabic" else "AI Quiz Generator",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Add custom CSS for Arabic text
st.markdown("""
<style>
.arabic-text {
    font-family: 'Arial', 'Tahoma', sans-serif;
    font-size: 18px;
    line-height: 2.0;
    text-align: right;
    direction: rtl;
}
</style>
""", unsafe_allow_html=True)

# Language selection at the top
language = st.radio("اللغة / Language", ["English", "Arabic"], horizontal=True, index=0 if st.session_state.language == "English" else 1)
st.session_state.language = language

if language == "Arabic":
    st.markdown('<div class="arabic-text">', unsafe_allow_html=True)
    st.title(format_arabic_text("🧠 منشئ الاختبارات بالذكاء الاصطناعي"))
    st.caption(format_arabic_text("مدعوم بواسطة Google Gemini API"))
    st.markdown('</div>', unsafe_allow_html=True)
else:
    st.title("🧠 AI Quiz Generator")
    st.caption("Powered by Google Gemini API")

with st.sidebar:
    if language == "Arabic":
        st.markdown(format_arabic_text("### ⚙️ إعدادات الاختبار"))
        total_questions = st.slider(format_arabic_text("عدد الأسئلة"), 5, 20, 10)
        easy_pct = st.slider(format_arabic_text("% سهلة"), 0, 100, 30)
        mid_pct = st.slider(format_arabic_text("% متوسطة"), 0, 100, 50)
        hard_pct = 100 - easy_pct - mid_pct
        st.metric(format_arabic_text("أسئلة صعبة"), f"{hard_pct}%")
        st.markdown(format_arabic_text("### 🔒 ملاحظة أمنية\nمفتاح API الخاص بك مخزن بشكل آمن"))
    else:
        st.markdown("### ⚙️ Quiz Settings")
        total_questions = st.slider("Total questions", 5, 20, 10)
        easy_pct = st.slider("% Easy", 0, 100, 30)
        mid_pct = st.slider("% Medium", 0, 100, 50)
        hard_pct = 100 - easy_pct - mid_pct
        st.metric("Hard questions", f"{hard_pct}%")
        st.markdown("### 🔒 Security Note\nYour API key is securely stored")

# Input method selection
if language == "Arabic":
    input_method = st.radio(format_arabic_text("اختر طريقة الإدخال:"), 
                          (format_arabic_text("📄 تحميل ملف PDF أو نصي"), format_arabic_text("✍️ إدخال نص")), 
                          horizontal=True,
                          key="input_method")
else:
    input_method = st.radio("Choose input method:", 
                          ("📄 Upload PDF or Text File", "✍️ Enter Text"), 
                          horizontal=True,
                          key="input_method")

if input_method == "📄 Upload PDF or Text File" or input_method == format_arabic_text("📄 تحميل ملف PDF أو نصي"):
    if language == "Arabic":
        uploaded_file = st.file_uploader(format_arabic_text("تحميل ملف"), 
                                      type=["pdf", "txt"], 
                                      key="file_uploader")
    else:
        uploaded_file = st.file_uploader("Upload a file", 
                                      type=["pdf", "txt"], 
                                      key="file_uploader")
    
    if uploaded_file:
        st.session_state.text_content = extract_text_from_file(uploaded_file)
        if st.session_state.text_content.strip():
            if language == "Arabic":
                st.success(format_arabic_text("تم تحميل الملف بنجاح!"))
                if st.button(format_arabic_text("✨ إنشاء الأسئلة"), key="generate_from_file"):
                    with st.spinner(format_arabic_text("جارٍ إنشاء الأسئلة...")):
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
                st.success("File uploaded successfully!")
                if st.button("✨ Generate Questions", key="generate_from_file"):
                    with st.spinner("Generating questions..."):
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
            if language == "Arabic":
                st.warning(format_arabic_text("يبدو أن الملف المحمل فارغ"))
            else:
                st.warning("The uploaded file appears to be empty")
else:
    if language == "Arabic":
        st.session_state.text_content = st.text_area(
            format_arabic_text("أدخل النص هنا:"), 
            height=200, 
            value=st.session_state.text_content,
            key="text_input"
        )
    else:
        st.session_state.text_content = st.text_area(
            "Enter your text here:", 
            height=200, 
            value=st.session_state.text_content,
            key="text_input"
        )
    
    if st.session_state.text_content.strip():
        if language == "Arabic":
            if st.button(format_arabic_text("✨ إنشاء الأسئلة"), key="generate_from_text"):
                with st.spinner(format_arabic_text("جارٍ إنشاء الأسئلة...")):
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
            if st.button("✨ Generate Questions", key="generate_from_text"):
                with st.spinner("Generating questions..."):
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

# Quiz display logic
if st.session_state.questions and not st.session_state.quiz_complete:
    q = st.session_state.questions[st.session_state.current_question]
    
    if language == "Arabic":
        st.subheader(format_arabic_text(f"السؤال {st.session_state.current_question + 1} من {len(st.session_state.questions)}"))
        st.markdown(format_arabic_text(f"**الصعوبة:** :{'green' if q['difficulty'] == 'easy' else 'orange' if q['difficulty'] == 'mid' else 'red'}[{'سهلة' if q['difficulty'] == 'easy' else 'متوسطة' if q['difficulty'] == 'mid' else 'صعبة'}]"))
        st.markdown(f"### {q['question']}")
    else:
        st.subheader(f"Question {st.session_state.current_question + 1} of {len(st.session_state.questions)}")
        st.markdown(f"**Difficulty:** :{'green' if q['difficulty'] == 'easy' else 'orange' if q['difficulty'] == 'mid' else 'red'}[{q['difficulty'].upper()}]")
        st.markdown(f"### {q['question']}")
    
    # Create a mapping of option letters to their values
    options_dict = {chr(65+i): opt for i, opt in enumerate(q['options'])}
    
    selected_key = st.radio(
        format_arabic_text("اختر الإجابة:") if language == "Arabic" else "Select your answer:",
        options=list(options_dict.keys()),
        format_func=lambda x: f"{x}) {options_dict[x]}",
        key=f"q_{st.session_state.current_question}")
    
    if st.button(format_arabic_text("إرسال الإجابة") if language == "Arabic" else "Submit Answer", 
                key=f"submit_{st.session_state.current_question}"):
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
            st.success(format_arabic_text("✅ صحيح!") if language == "Arabic" else "✅ Correct!")
        else:
            if language == "Arabic":
                st.error(format_arabic_text(f"❌ غير صحيح (الإجابة الصحيحة: {q['correct']}) {options_dict[q['correct']]}"))
            else:
                st.error(f"❌ Incorrect (Correct answer: {q['correct']}) {options_dict[q['correct']]}")
        
        st.markdown(f"**{format_arabic_text('التفسير') if language == 'Arabic' else 'Explanation'}:** {q['explanation']}")
        
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
    if language == "Arabic":
        st.success(format_arabic_text("🎉 اكتمل الاختبار!"))
    else:
        st.success("🎉 Quiz Completed!")
    
    # Score summary
    correct = st.session_state.score
    total = len(st.session_state.questions)
    percentage = (correct / total) * 100
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if language == "Arabic":
            st.metric(format_arabic_text("الإجابات الصحيحة"), f"{correct}/{total}")
        else:
            st.metric("Correct Answers", f"{correct}/{total}")
    with col2:
        if language == "Arabic":
            st.metric(format_arabic_text("الإجابات الخاطئة"), f"{total - correct}/{total}")
        else:
            st.metric("Incorrect Answers", f"{total - correct}/{total}")
    with col3:
        if language == "Arabic":
            st.metric(format_arabic_text("النسبة المئوية"), f"{percentage:.1f}%")
        else:
            st.metric("Percentage", f"{percentage:.1f}%")
    
    # Difficulty analysis
    if language == "Arabic":
        st.subheader(format_arabic_text("📊 الأداء حسب الصعوبة"))
        difficulty_stats = {"سهلة": 0, "متوسطة": 0, "صعبة": 0}
    else:
        st.subheader("📊 Performance by Difficulty")
        difficulty_stats = {"Easy": 0, "Medium": 0, "Hard": 0}
    
    for q, ans in zip(st.session_state.questions, st.session_state.user_answers):
        if ans['is_correct']:
            if q['difficulty'] == 'easy':
                difficulty_stats["سهلة" if language == "Arabic" else "Easy"] += 1
            elif q['difficulty'] == 'mid':
                difficulty_stats["متوسطة" if language == "Arabic" else "Medium"] += 1
            elif q['difficulty'] == 'hard':
                difficulty_stats["صعبة" if language == "Arabic" else "Hard"] += 1
    
    st.bar_chart(difficulty_stats)
    
    # Detailed review
    if language == "Arabic":
        st.subheader(format_arabic_text("🔍 مراجعة مفصلة"))
    else:
        st.subheader("🔍 Detailed Review")
    
    for i, ans in enumerate(st.session_state.user_answers, 1):
        with st.expander(f"{format_arabic_text('السؤال') if language == 'Arabic' else 'Question'} {i}: {ans['question']}", expanded=False):
            status = format_arabic_text("✅ صحيح") if ans['is_correct'] else format_arabic_text("❌ غير صحيح") if language == "Arabic" else "✅ Correct" if ans['is_correct'] else "❌ Incorrect"
            st.markdown(f"**{format_arabic_text('إجابتك') if language == 'Arabic' else 'Your Answer'}:** {status} {ans['selected_key']}) {ans['selected']}")
            if not ans['is_correct']:
                st.markdown(f"**{format_arabic_text('الإجابة الصحيحة') if language == 'Arabic' else 'Correct Answer'}:** {ans['correct_key']}) {ans['correct']}")
            st.markdown(f"**{format_arabic_text('التفسير') if language == 'Arabic' else 'Explanation'}:** {ans['explanation']}")
    
    if st.button(format_arabic_text("🔄 بدء اختبار جديد") if language == "Arabic" else "🔄 Start New Quiz"):
        st.session_state.questions = []
        st.session_state.current_question = 0
        st.session_state.score = 0
        st.session_state.user_answers = []
        st.session_state.quiz_complete = False
        st.rerun()

# Reset button (visible during quiz)
if st.session_state.questions and not st.session_state.quiz_complete:
    if st.button(format_arabic_text("🔁 إعادة تعيين الاختبار") if language == "Arabic" else "🔁 Reset Quiz"):
        st.session_state.questions = []
        st.session_state.current_question = 0
        st.session_state.score = 0
        st.session_state.user_answers = []
        st.session_state.quiz_complete = False
        st.rerun()

st.markdown("---")
if language == "Arabic":
    st.caption(format_arabic_text("ملاحظة: يستخدم Google Gemini API لإنشاء الأسئلة"))
else:
    st.caption("Note: Uses Google's Gemini API for question generation")

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
for key, default in {
    'questions': [], 'current_question': 0, 'score': 0,
    'user_answers': [], 'quiz_complete': False,
    'text_content': '', 'language': 'English'
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# Arabic formatting helpers
def format_arabic_text(text: str) -> str:
    try:
        cleaned = fix_arabic_text(text)
        reshaped = arabic_reshaper.reshape(cleaned)
        return get_display(reshaped)
    except Exception:
        return text

def wrap(text: str) -> str:
    """Wrap text in RTL container or leave as-is"""
    if st.session_state.language == "Arabic":
        return f'<div class="arabic-text">{text}</div>'
    return text

# Configure Google API
def configure_google_api() -> bool:
    key = os.environ.get("GOOGLE_API_KEY") or st.secrets.get("GOOGLE_API_KEY", None)
    if not key:
        msg = "Google API key not configured"
        st.error(wrap(format_arabic_text(msg)))
        return False
    genai.configure(api_key=key)
    return True

if configure_google_api():
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        st.error(wrap(format_arabic_text(f"Failed to init model: {e}")))
        model = None
else:
    model = None

# Extract text function
def extract_text_from_file(file) -> str:
    if not file:
        return ''
    try:
        if file.type == 'application/pdf':
            reader = PyPDF2.PdfReader(BytesIO(file.read()))
            text = '\n'.join(p.extract_text() or '' for p in reader.pages)
        else:
            text = file.read().decode('utf-8')
        return format_arabic_text(text) if st.session_state.language=='Arabic' else text
    except Exception as e:
        st.error(wrap(format_arabic_text(f"Error reading file: {e}")))
        return ''

# Question generation
def generate_questions(text, total, easy_pct, mid_pct, hard_pct):
    if not model:
        st.error(wrap(format_arabic_text("Model not initialized")))
        return []
    if not text.strip():
        st.error(wrap(format_arabic_text("Please provide text content")))
        return []
    num_easy = int(total * easy_pct/100)
    num_mid = int(total * mid_pct/100)
    num_hard = total - num_easy - num_mid
    lang_instr = 'in Arabic' if st.session_state.language=='Arabic' else 'in English'
    prompt = f"""
Generate {total} multiple choice questions {lang_instr} as a JSON array from this text:
{text[:3000]}

Include {num_easy} easy, {num_mid} medium, {num_hard} hard. Only return JSON array.
"""
    try:
        resp = model.generate_content(prompt)
        qlist = json.loads(resp.text.strip().strip('```json').strip('```'))
        if st.session_state.language=='Arabic':
            for q in qlist:
                q['question'] = format_arabic_text(q['question'])
                q['options'] = [format_arabic_text(o) for o in q['options']]
                q['explanation'] = format_arabic_text(q['explanation'])
        return qlist
    except Exception as e:
        st.error(wrap(format_arabic_text(f"Failed to generate questions: {e}")))
        return []

# Page config & CSS
st.set_page_config(page_title=wrap(format_arabic_text("منشئ الاختبارات")), layout="wide")
st.markdown("""
<style>
.arabic-text {direction: rtl; unicode-bidi: embed; text-align: right; font-family: Tahoma, Arial;}
</style>
""", unsafe_allow_html=True)

# Title and language selector
lang = st.radio("اللغة / Language", ["English","Arabic"], index=1 if st.session_state.language=='Arabic' else 0, horizontal=True)
st.session_state.language = lang
if lang=='Arabic':
    st.markdown(wrap(format_arabic_text("🧠 منشئ الاختبارات بالذكاء الاصطناعي")), unsafe_allow_html=True)
else:
    st.title("🧠 AI Quiz Generator")
    st.caption("Powered by Google Gemini API")

# Sidebar settings
with st.sidebar:
    if lang=='Arabic':
        st.markdown(wrap("### ⚙️ إعدادات الاختبار"), unsafe_allow_html=True)
        total = st.slider(wrap(format_arabic_text("عدد الأسئلة")),5,20,10)
        easy = st.slider(wrap(format_arabic_text("٪ سهلة")),0,100,30)
        mid = st.slider(wrap(format_arabic_text("٪ متوسطة")),0,100,50)
        hard = 100-easy-mid
        st.metric(wrap(format_arabic_text("صعبة")),f"{hard}%")
    else:
        st.markdown("### ⚙️ Quiz Settings")
        total = st.slider("Total questions",5,20,10)
        easy = st.slider("% Easy",0,100,30)
        mid = st.slider("% Medium",0,100,50)
        hard = 100-easy-mid
        st.metric("Hard questions",f"{hard}%")

# Input
methods = ("📄 Upload PDF or Text","✍️ Enter Text")
if lang=='Arabic':
    methods = tuple(format_arabic_text(m) for m in methods)
inp = st.radio(wrap(format_arabic_text("اختر طريقة الإدخال:")) if lang=='Arabic' else "Choose input method:", methods, horizontal=True)

if "Upload" in inp or "تحميل" in inp:
    up = st.file_uploader(wrap(format_arabic_text("تحميل ملف")) if lang=='Arabic' else "Upload PDF or TXT", type=['pdf','txt'])
    if up:
        st.session_state.text_content = extract_text_from_file(up)
        if st.session_state.text_content.strip():
            btn = st.button(wrap(format_arabic_text("✨ إنشاء الأسئلة")) if lang=='Arabic' else "✨ Generate Questions")
            if btn:
                with st.spinner(wrap(format_arabic_text("جارٍ إنشاء الأسئلة...")) if lang=='Arabic' else "Generating questions..."):
                    st.session_state.questions = generate_questions(st.session_state.text_content, total, easy, mid, hard)
                    if st.session_state.questions:
                        st.session_state.user_answers=[]; st.session_state.score=0
                        st.session_state.current_question=0; st.session_state.quiz_complete=False
                        st.experimental_rerun()
elif "Enter" in inp or "أدخل" in inp:
    ta = st.text_area(wrap(format_arabic_text("أدخل النص هنا:")) if lang=='Arabic' else "Enter your text here:", value=st.session_state.text_content, height=200)
    st.session_state.text_content = ta
    if ta.strip():
        btn = st.button(wrap(format_arabic_text("✨ إنشاء الأسئلة")) if lang=='Arabic' else "✨ Generate Questions")
        if btn:
            with st.spinner(wrap(format_arabic_text("جارٍ إنشاء الأسئلة...")) if lang=='Arabic' else "Generating questions..."):
                st.session_state.questions = generate_questions(ta, total, easy, mid, hard)
                if st.session_state.questions:
                    st.session_state.user_answers=[]; st.session_state.score=0
                    st.session_state.current_question=0; st.session_state.quiz_complete=False
                    st.experimental_rerun()

# Quiz Display
if st.session_state.questions and not st.session_state.quiz_complete:
    q = st.session_state.questions[st.session_state.current_question]
    idx = st.session_state.current_question+1
    total_q = len(st.session_state.questions)
    hdr = f"السؤال {idx} من {total_q}" if lang=='Arabic' else f"Question {idx} of {total_q}"
    st.subheader(wrap(format_arabic_text(hdr) if lang=='Arabic' else hdr), unsafe_allow_html=True)
    question_text = wrap(format_arabic_text(q['question']) if lang=='Arabic' else q['question'])
    st.markdown(question_text, unsafe_allow_html=True)
    # Options
    opts = {chr(65+i): opt for i,opt in enumerate(q['options'])}
    def label(letter):
        txt = f"{letter}) {opts[letter]}"
        return wrap(format_arabic_text(txt) if lang=='Arabic' else txt)
    sel = st.radio(wrap(format_arabic_text("اختر الإجابة:")) if lang=='Arabic' else "Select your answer:", list(opts.keys()), format_func=lambda x: label(x), key=f"q{idx}", unsafe_allow_html=True)
    if st.button(wrap(format_arabic_text("إرسال الإجابة")) if lang=='Arabic' else "Submit Answer", key=f"sub{idx}"):
        correct = (sel == q['correct'])
        st.session_state.user_answers.append({
            'selected': opts[sel], 'selected_key': sel,
            'correct': opts[q['correct']], 'correct_key': q['correct'],
            'explanation': q['explanation'], 'is_correct': correct
        })
        if correct:
            st.success(wrap(format_arabic_text("✅ صحيح!")))
        else:
            msg = f"❌ غير صحيح (الإجابة الصحيحة: {q['correct']}) {opts[q['correct']]}" if lang=='Arabic' else f"❌ Incorrect (Correct: {q['correct']}) {opts[q['correct']]}"
            st.error(wrap(format_arabic_text(msg) if lang=='Arabic' else msg))
        expl = wrap(format_arabic_text(f"التفسير: {q['explanation']}") if lang=='Arabic' else f"Explanation: {q['explanation']}")
        st.markdown(expl, unsafe_allow_html=True)
        # Next or finish
        if idx < total_q:
            st.session_state.current_question +=1
            st.experimental_rerun()
        else:
            st.session_state.quiz_complete=True
            st.experimental_rerun()

# Completion Screen
if st.session_state.quiz_complete:
    st.balloons()
    msg = "🎉 اكتمل الاختبار!" if lang=='Arabic' else "🎉 Quiz Completed!"
    st.success(wrap(format_arabic_text(msg) if lang=='Arabic' else msg), unsafe_allow_html=True)
    corr = st.session_state.score; tot = len(st.session_state.questions)
    pct = (corr/tot)*100
    c1,c2,c3 = st.columns(3)
    with c1:
        st.metric(wrap(format_arabic_text("الإجابات الصحيحة") if lang=='Arabic' else "Correct Answers"), f"{corr}/{tot}")
    with c2:
        st.metric(wrap(format_arabic_text("الإجابات الخاطئة") if lang=='Arabic' else "Incorrect Answers"), f"{tot-corr}/{tot}")
    with c3:
        st.metric(wrap(format_arabic_text("النسبة المئوية") if lang=='Arabic' else "Percentage"), f"{pct:.1f}%")
    # Bar chart
    stats = {'Easy':0,'Medium':0,'Hard':0} if lang=='English' else {'سهلة':0,'متوسطة':0,'صعبة':0}
    for q,a in zip(st.session_state.questions, st.session_state.user_answers):
        if a['is_correct']:
            key = 'سهلة' if q['difficulty']=='easy' and lang=='Arabic' else 'Easy' if q['difficulty']=='easy' else \
                  'متوسطة' if q['difficulty']=='mid' and lang=='Arabic' else 'Medium' if q['difficulty']=='mid' else \
                  'صعبة' if lang=='Arabic' else 'Hard'
            stats[key] +=1
    st.bar_chart(stats)
    # Detailed review
    hdr = "🔍 مراجعة مفصلة" if lang=='Arabic' else "🔍 Detailed Review"
    st.subheader(wrap(format_arabic_text(hdr) if lang=='Arabic' else hdr), unsafe_allow_html=True)
    for i,a in enumerate(st.session_state.user_answers,1):
        title = f"السؤال {i}: {a['question']}" if lang=='Arabic' else f"Question {i}: {a['question']}"
        with st.expander(wrap(format_arabic_text(title) if lang=='Arabic' else title), expanded=False):
            status = "✅ صحيح" if a['is_correct'] and lang=='Arabic' else "❌ غير صحيح" if not a['is_correct'] and lang=='Arabic' else "✅ Correct" if a['is_correct'] else "❌ Incorrect"
            ans_txt = f"{a['selected_key']}) {a['selected']}"
            st.markdown(wrap(format_arabic_text(f"إجابتك: {status} {ans_txt}") if lang=='Arabic' else f"Your Answer: {status} {ans_txt}"), unsafe_allow_html=True)
            if not a['is_correct']:
                corr_txt = f"{a['correct_key']}) {a['correct']}"
                st.markdown(wrap(format_arabic_text(f"الإجابة الصحيحة: {corr_txt}") if lang=='Arabic' else f"Correct Answer: {corr_txt}"), unsafe_allow_html=True)
            st.markdown(wrap(format_arabic_text(f"التفسير: {a['explanation']}") if lang=='Arabic' else f"Explanation: {a['explanation']}"), unsafe_allow_html=True)
    # Restart
    if st.button(wrap(format_arabic_text("🔄 بدء اختبار جديد") if lang=='Arabic' else "🔄 Start New Quiz")):
        for reset_key in ['questions','current_question','score','user_answers','quiz_complete']:
            st.session_state[reset_key] = [] if reset_key in ['questions','user_answers'] else 0 if reset_key!='quiz_complete' else False
        st.experimental_rerun()

st.markdown("---")
st.caption(wrap(format_arabic_text("ملاحظة: يستخدم Google Gemini API لإنشاء الأسئلة")) if lang=='Arabic' else "Note: Uses Google Gemini API for question generation")

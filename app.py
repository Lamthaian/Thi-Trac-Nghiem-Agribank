import streamlit as st
import docx
import re
import random
import io
import json
import os

# --- 1. CẤU HÌNH TRANG WEB ---
st.set_page_config(page_title="Thi Trắc Nghiệm Agribank", page_icon="🌱", layout="centered")

# --- 2. KHỞI TẠO BỘ NHỚ TẠM VÀ TỰ ĐỘNG ĐỌC DỮ LIỆU ---
if 'question_bank' not in st.session_state:
    if os.path.exists('NganHangCauHoi.json'):
        with open('NganHangCauHoi.json', 'r', encoding='utf-8') as f:
            st.session_state.question_bank = json.load(f)
    else:
        st.session_state.question_bank = {}

if 'session_questions' not in st.session_state:
    st.session_state.session_questions = []
if 'current_idx' not in st.session_state:
    st.session_state.current_idx = 0
if 'user_answers' not in st.session_state:
    st.session_state.user_answers = {}
if 'checked_status' not in st.session_state:
    st.session_state.checked_status = {}
if 'is_submitted' not in st.session_state:
    st.session_state.is_submitted = False

# Hàm đọc file docx trên Web (Đã đồng bộ bộ key với bản Desktop)
def parse_docx(file_bytes):
    doc = docx.Document(io.BytesIO(file_bytes))
    text = "\n".join([p.text for p in doc.paragraphs])
    
    questions_list = []
    lines = text.split('\n')
    current_q = None
    
    for line in lines:
        line = line.strip()
        if not line: continue
        if line.startswith('### Câu'):
            if current_q and len(current_q.get('raw_options', {})) > 0: 
                questions_list.append(current_q)
            clean_q = re.sub(r'^### Câu \d+[:\.\-]?\s*', '', line)
            current_q = {'question': clean_q, 'raw_options': {}, 'raw_answers': [], 'explanation': ''}
        elif current_q is not None:
            if re.match(r'^[A-Z]\.', line):
                letter = line[0]
                text_part = line[1:].strip().lstrip('.').strip()
                current_q['raw_options'][letter] = text_part
            elif line.startswith('* Đáp án đúng:'):
                ans_str = line.split(':', 1)[1].strip().replace('*', '').strip()
                current_q['raw_answers'] = [x.strip() for x in ans_str.split(',') if x.strip()]
            elif line.startswith('* Căn cứ') or line.startswith('* Giải thích'):
                current_q['explanation'] += line + '\n'
                
    if current_q and len(current_q.get('raw_options', {})) > 0:
        questions_list.append(current_q)
    return questions_list

# --- 3. GIAO DIỆN THANH BÊN (SIDEBAR) ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/vi/thumb/1/1b/Agribank_Logo.svg/1200px-Agribank_Logo.svg.png", width=150)
    
    st.header("📂 NẠP THÊM CHUYÊN ĐỀ")
    uploaded_file = st.file_uploader("Tải file .docx", type=['docx'])
    topic_name = st.text_input("Tên chuyên đề:")
    
    if st.button("Nạp vào bộ nhớ tạm"):
        if uploaded_file and topic_name:
            qs = parse_docx(uploaded_file.getvalue())
            if qs:
                st.session_state.question_bank[topic_name] = qs
                st.success(f"Đã nạp {len(qs)} câu vào '{topic_name}'!")
                st.rerun()
        else:
            st.error("Vui lòng tải file và nhập tên chuyên đề.")
            
    st.divider()
    
    st.header("⚙️ TẠO ĐỀ THI")
    if st.session_state.question_bank:
        st.success(f"📚 Hệ thống đang có {len(st.session_state.question_bank)} chuyên đề.")
        selected_topics = st.multiselect("Chọn chuyên đề thi:", list(st.session_state.question_bank.keys()))
        total_qs = st.number_input("Tổng số câu", min_value=1, value=50)
        
        if st.button("🚀 Bắt đầu thi", use_container_width=True):
            if not selected_topics:
                st.warning("Vui lòng chọn ít nhất 1 chuyên đề.")
            else:
                pool = []
                for t in selected_topics:
                    pool.extend(st.session_state.question_bank[t])
                
                random.shuffle(pool)
                final_pool = pool[:total_qs]
                
                st.session_state.session_questions = final_pool
                st.session_state.current_idx = 0
                st.session_state.user_answers = {i: [] for i in range(len(final_pool))}
                st.session_state.checked_status = {i: False for i in range(len(final_pool))}
                st.session_state.is_submitted = False
                st.rerun()
    else:
        st.warning("Ngân hàng câu hỏi đang trống.")

# --- 4. GIAO DIỆN CHÍNH (KHU VỰC THI) ---
st.title("🌱 HỆ THỐNG ÔN THI TRẮC NGHIỆM")

if not st.session_state.session_questions:
    st.info("👈 Bắt đầu bằng cách chọn chuyên đề và bấm 'Bắt đầu thi' ở menu bên trái.")
else:
    idx = st.session_state.current_idx
    q = st.session_state.session_questions[idx]
    
    # KẾT NỐI DỮ LIỆU ĐA NGUỒN (Xử lý mượt cả JSON máy tính và DOCX web)
    q_options = q.get('options', q.get('raw_options', {}))
    q_answers = q.get('answers', q.get('raw_answers', []))
    
    st.progress((idx + 1) / len(st.session_state.session_questions), text=f"Câu {idx + 1} / {len(st.session_state.session_questions)}")
    
    st.markdown(f"### Câu {idx + 1}: {q['question']}")
    
    options_list = [f"{k}. {v}" for k, v in q_options.items()]
    
    if not st.session_state.is_submitted and not st.session_state.checked_status.get(idx, False):
        if len(q_answers) > 1:
            st.caption("*(Câu này có nhiều đáp án đúng)*")
            selected = st.multiselect("Chọn các đáp án:", options_list, default=st.session_state.user_answers[idx])
            st.session_state.user_answers[idx] = selected
            
            if st.button("✅ Chốt đáp án", key=f"check_{idx}"):
                if not st.session_state.user_answers[idx]:
                    st.warning("Vui lòng chọn ít nhất 1 đáp án để kiểm tra!")
                else:
                    st.session_state.checked_status[idx] = True
                    st.rerun()
        else:
            selected = st.radio("Chọn đáp án:", options_list, index=None, key=f"radio_{idx}")
            if selected:
                st.session_state.user_answers[idx] = [selected]
                st.session_state.checked_status[idx] = True
                st.rerun()
    else:
        st.markdown("---")
        correct_full = [f"{k}. {q_options[k]}" for k in q_answers]
        user_full = st.session_state.user_answers.get(idx, [])
        
        is_fully_correct = (set(user_full) == set(correct_full))
        
        if is_fully_correct:
            st.markdown("🎉 **Tuyệt vời! Bạn đã trả lời CHÍNH XÁC.**")
        else:
            st.markdown("⚠️ **Chưa chính xác! Xem lại đáp án bên dưới.**")

        for opt in options_list:
            if opt in correct_full and opt in user_full:
                st.success(f"✅ **{opt}**")
            elif opt in correct_full and opt not in user_full:
                st.success(f"☑️ **{opt}** *(Đáp án đúng bị sót)*")
            elif opt not in correct_full and opt in user_full:
                st.error(f"❌ **{opt}** *(Sai)*")
            else:
                st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp; {opt}")
                
        st.info(f"**Giải thích chi tiết:**\n{q.get('explanation', '')}")

    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("⬅ Câu trước") and idx > 0:
            st.session_state.current_idx -= 1
            st.rerun()
    with col2:
        if not st.session_state.is_submitted:
            if st.button("✅ NỘP BÀI", type="primary", use_container_width=True):
                st.session_state.is_submitted = True
                st.rerun()
        else:
            score = 0
            for i, question in enumerate(st.session_state.session_questions):
                q_opt = question.get('options', question.get('raw_options', {}))
                q_ans = question.get('answers', question.get('raw_answers', []))
                correct_arr = [f"{k}. {q_opt[k]}" for k in q_ans]
                if set(st.session_state.user_answers.get(i, [])) == set(correct_arr):
                    score += 1
            st.metric(label="ĐIỂM SỐ CỦA BẠN", value=f"{score} / {len(st.session_state.session_questions)}")
            
    with col3:
        if st.button("Câu tiếp ➡") and idx < len(st.session_state.session_questions) - 1:
            st.session_state.current_idx += 1
            st.rerun()

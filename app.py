import streamlit as st
import docx
import re
import random
import io

# --- 1. CẤU HÌNH TRANG WEB ---
st.set_page_config(page_title="Thi Trắc Nghiệm Agribank", page_icon="🌱", layout="centered")

# --- 2. KHỞI TẠO BỘ NHỚ TẠM (SESSION STATE) ---
if 'question_bank' not in st.session_state:
    st.session_state.question_bank = {}
if 'session_questions' not in st.session_state:
    st.session_state.session_questions = []
if 'current_idx' not in st.session_state:
    st.session_state.current_idx = 0
if 'user_answers' not in st.session_state:
    st.session_state.user_answers = {}
if 'is_submitted' not in st.session_state:
    st.session_state.is_submitted = False

# Hàm đọc file (Tái sử dụng logic cũ)
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
            if current_q and len(current_q['options']) > 0: 
                questions_list.append(current_q)
            clean_q = re.sub(r'^### Câu \d+[:\.\-]?\s*', '', line)
            current_q = {'question': clean_q, 'options': {}, 'answers': [], 'explanation': ''}
        elif current_q is not None:
            if re.match(r'^[A-Z]\.', line):
                letter = line[0]
                text_part = line[1:].strip().lstrip('.').strip()
                current_q['options'][letter] = text_part
            elif line.startswith('* Đáp án đúng:'):
                ans_str = line.split(':', 1)[1].strip().replace('*', '').strip()
                current_q['answers'] = [x.strip() for x in ans_str.split(',') if x.strip()]
            elif line.startswith('* Căn cứ') or line.startswith('* Giải thích'):
                current_q['explanation'] += line + '\n'
                
    if current_q and len(current_q['options']) > 0:
        questions_list.append(current_q)
    return questions_list

# --- 3. GIAO DIỆN THANH BÊN (SIDEBAR) ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/vi/thumb/1/1b/Agribank_Logo.svg/1200px-Agribank_Logo.svg.png", width=150)
    st.header("📂 NẠP DỮ LIỆU")
    uploaded_file = st.file_uploader("Tải file .docx đã chuẩn hóa", type=['docx'])
    topic_name = st.text_input("Tên chuyên đề:")
    
    if st.button("Lưu vào Ngân hàng"):
        if uploaded_file and topic_name:
            qs = parse_docx(uploaded_file.getvalue())
            if qs:
                st.session_state.question_bank[topic_name] = qs
                st.success(f"Đã nạp {len(qs)} câu vào '{topic_name}'!")
        else:
            st.error("Vui lòng tải file và nhập tên chuyên đề.")
            
    st.divider()
    st.header("⚙️ TẠO ĐỀ THI")
    if st.session_state.question_bank:
        selected_topics = st.multiselect("Chọn chuyên đề thi:", list(st.session_state.question_bank.keys()))
        total_qs = st.number_input("Tổng số câu hỏi", min_value=1, value=50)
        
        if st.button("🚀 Bắt đầu thi", use_container_width=True):
            if not selected_topics:
                st.warning("Vui lòng chọn ít nhất 1 chuyên đề.")
            else:
                pool = []
                for t in selected_topics:
                    pool.extend(st.session_state.question_bank[t])
                
                # Trộn và lấy đủ số câu
                random.shuffle(pool)
                final_pool = pool[:total_qs]
                
                # Cấu hình đề
                st.session_state.session_questions = final_pool
                st.session_state.current_idx = 0
                st.session_state.user_answers = {i: [] for i in range(len(final_pool))}
                st.session_state.is_submitted = False
                st.rerun()

# --- 4. GIAO DIỆN CHÍNH (KHU VỰC THI) ---
st.title("🌱 HỆ THỐNG ÔN THI TRẮC NGHIỆM")

if not st.session_state.session_questions:
    st.info("👈 Bắt đầu bằng cách nạp dữ liệu và chọn 'Bắt đầu thi' ở menu bên trái.")
else:
    idx = st.session_state.current_idx
    q = st.session_state.session_questions[idx]
    
    # Hiển thị tiến độ
    st.progress((idx + 1) / len(st.session_state.session_questions), text=f"Câu {idx + 1} / {len(st.session_state.session_questions)}")
    
    # Hiển thị câu hỏi
    st.markdown(f"### Câu {idx + 1}: {q['question']}")
    
    # Tùy chọn đáp án
    options_list = [f"{k}. {v}" for k, v in q['options'].items()]
    
    # Nếu chưa nộp bài, cho phép chọn
    if not st.session_state.is_submitted:
        # Nếu câu hỏi có nhiều đáp án đúng -> Dùng Multiselect hoặc Checkbox
        if len(q['answers']) > 1:
            st.caption("*(Câu này có nhiều đáp án đúng)*")
            selected = st.multiselect("Chọn các đáp án:", options_list, default=st.session_state.user_answers[idx])
            st.session_state.user_answers[idx] = selected
        else:
            # Câu hỏi 1 đáp án -> Dùng Radio
            current_ans = st.session_state.user_answers[idx][0] if st.session_state.user_answers[idx] else None
            selected = st.radio("Chọn đáp án:", options_list, index=options_list.index(current_ans) if current_ans in options_list else None)
            if selected:
                st.session_state.user_answers[idx] = [selected]
    else:
        # Khi đã nộp bài, hiển thị kết quả
        st.markdown("---")
        correct_full = [f"{k}. {q['options'][k]}" for k in q['answers']]
        user_full = st.session_state.user_answers[idx]
        
        if set(correct_full) == set(user_full):
            st.success("✅ Bạn đã trả lời CHÍNH XÁC!")
        else:
            st.error(f"❌ Sai. Đáp án đúng là: **{', '.join([k for k in q['answers']])}**")
            
        st.info(f"**Chi tiết:**\n{q['explanation']}")

    # Các nút điều hướng
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
                correct_arr = [f"{k}. {question['options'][k]}" for k in question['answers']]
                if set(st.session_state.user_answers.get(i, [])) == set(correct_arr):
                    score += 1
            st.metric(label="ĐIỂM SỐ CỦA BẠN", value=f"{score}/{len(st.session_state.session_questions)}")
            
    with col3:
        if st.button("Câu tiếp ➡") and idx < len(st.session_state.session_questions) - 1:
            st.session_state.current_idx += 1
            st.rerun()

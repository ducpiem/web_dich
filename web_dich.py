import streamlit as st
from google import genai

# --- CẤU HÌNH TRANG WEB ---
st.set_page_config(
    page_title="Trạm Dịch Thuật AI",
    page_icon="⚡",
    layout="centered"
)

# --- CẤU HÌNH API GEMINI ---
API_KEY = "AQ.Ab8RN6IPcFJXHkBheWMnhOgtDLFp-V314nyblKIFZL7_v6y2ug"

# TỐI ƯU TỐC ĐỘ: Lưu client vào bộ nhớ đệm vĩnh viễn của phiên làm việc
if "gemini_client" not in st.session_state:
    st.session_state.gemini_client = genai.Client(api_key=API_KEY)

# --- HÀM XỬ LÝ DỊCH (TỐI ƯU SIÊU NHANH) ---
def dich_van_ban(text_goc, huong_dich, ngon_ngu_dich="Tiếng Anh"):
    if not text_goc.strip():
        return ""
    try:
        # Lấy client đã mở sẵn từ trước, không tạo lại kết nối mới
        client = st.session_state.gemini_client
        
        if huong_dich == "vi":
            prompt = f"Dịch câu sau sang Tiếng Việt sát nghĩa, đúng văn phong nhắn tin trò chuyện. Chỉ trả về kết quả dịch: '{text_goc}'"
        else:
            prompt = f"Dịch câu Tiếng Việt sau sang {ngon_ngu_dich} tự nhiên như người bản xứ nhắn tin. Chỉ trả về kết quả dịch: '{text_goc}'"
            
        # Dùng trực tiếp gemini-2.5-flash cho tốc độ phản hồi nhanh nhất
        res = client.models.generate_content(
            model="gemini-3.5-flash", 
            contents=prompt
        )
        return res.text.strip()
    except Exception as e:
        return f"Lỗi: {e}"

# --- GIAO DIỆN CHÍNH ---
st.title("⚡ Trạm Dịch Thuật Chat AI")
st.caption("Tối ưu cho trò chuyện 2 chiều — Dùng mượt trên cả Điện thoại & PC")

st.divider()

# === PHẦN 1: HỌ NÓI GÌ? ===
st.subheader("1️⃣ Đối tác gửi tin nhắn:")
msg_nhan = st.text_area("Dán tin nhắn ngoại ngữ vào đây:", height=100, placeholder="Hello! How are you today?...")

col1, col2 = st.columns([1, 1])
with col1:
    btn_dich_nhan = st.button("⬇️ Dịch sang Tiếng Việt", use_container_width=True, type="primary")

if btn_dich_nhan and msg_nhan:
    with st.spinner("Đang dịch..."):
        ket_qua_vi = dich_van_ban(msg_nhan, huong_dich="vi")
        st.info(f"**Ý nghĩa Tiếng Việt:**\n\n{ket_qua_vi}")

st.divider()

# === PHẦN 2: BẠN TRẢ LỜI ===
st.subheader("2️⃣ Bạn trả lời:")
msg_gui = st.text_area("Gõ câu trả lời Tiếng Việt:", height=100, placeholder="Tôi khỏe, cảm ơn bạn...")

col_lang, col_btn = st.columns([1, 1])
with col_lang:
    lang_select = st.selectbox("Chọn ngôn ngữ dịch sang:", [
        "Tiếng Anh", "Tiếng Trung (Phồn thể/Giản thể)", "Tiếng Nhật", "Tiếng Hàn", "Tiếng Pháp"
    ])
with col_btn:
    st.write("") 
    btn_dich_gui = st.button("⬇️ Dịch để Gửi đi", use_container_width=True, type="primary")

if btn_dich_gui and msg_gui:
    with st.spinner("Đang dịch..."):
        ket_qua_ngoai_ngu = dich_van_ban(msg_gui, huong_dich="out", ngon_ngu_dich=lang_select)
        
        st.success("**Kết quả (Bấm biểu tượng copy ở góc phải ô dưới để sao chép):**")
        st.code(ket_qua_ngoai_ngu, language=None)

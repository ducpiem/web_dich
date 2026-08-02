import streamlit as st
from google import genai
import edge_tts
import asyncio

# --- CẤU HÌNH TRANG WEB ---
st.set_page_config(
    page_title="Trạm Dịch Thuật AI & Giọng Đọc",
    page_icon="⚡",
    layout="centered"
)

# --- CẤU HÌNH API GEMINI (TỪ KÉT SẮT STREAMLIT) ---
API_KEY = st.secrets["GEMINI_API_KEY"]

if "gemini_client" not in st.session_state:
    st.session_state.gemini_client = genai.Client(api_key=API_KEY.strip())

# --- BỘ TỪ ĐIỂN GIỌNG ĐỌC AI (MICROSOFT NEURAL VOICES) ---
VOICE_MAP = {
    "Tiếng Việt": {
        "Nữ": "vi-VN-HoaiMyNeural",
        "Nam": "vi-VN-NamMinhNeural"
    },
    "Tiếng Anh": {
        "Nữ": "en-US-JennyNeural",
        "Nam": "en-US-GuyNeural"
    },
    "Tiếng Trung (Phồn thể/Giản thể)": {
        "Nữ": "zh-CN-XiaoxiaoNeural",
        "Nam": "zh-CN-YunxiNeural"
    },
    "Tiếng Nhật": {
        "Nữ": "ja-JP-NanamiNeural",
        "Nam": "ja-JP-KeitaNeural"
    },
    "Tiếng Hàn": {
        "Nữ": "ko-KR-SunHiNeural",
        "Nam": "ko-KR-InJoonNeural"
    },
    "Tiếng Pháp": {
        "Nữ": "fr-FR-DeniseNeural",
        "Nam": "fr-FR-HenriNeural"
    }
}

# --- HÀM TẠO ÂM THANH AI (EDGE-TTS) ---
def tao_am_thanh(text, voice_code):
    async def _generate():
        tts = edge_tts.Communicate(text, voice_code)
        audio_bytes = b""
        async for chunk in tts.stream():
            if chunk["type"] == "audio":
                audio_bytes += chunk["data"]
        return audio_bytes

    # Xử lý vòng lặp bất đồng bộ cho Streamlit
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    return loop.run_until_complete(_generate())

# --- HÀM XỬ LÝ DỊCH ---
def dich_van_ban(text_goc, huong_dich, ngon_ngu_dich="Tiếng Anh"):
    if not text_goc.strip():
        return ""
    try:
        client = st.session_state.gemini_client
        if huong_dich == "vi":
            prompt = f"Dịch câu sau sang Tiếng Việt sát nghĩa, đúng văn phong nhắn tin trò chuyện. Chỉ trả về kết quả dịch: '{text_goc}'"
        else:
            prompt = f"Dịch câu Tiếng Việt sau sang {ngon_ngu_dich} tự nhiên như người bản xứ nhắn tin. Chỉ trả về kết quả dịch: '{text_goc}'"
            
        res = client.models.generate_content(
            model="gemini-3.5-flash", 
            contents=prompt
        )
        return res.text.strip()
    except Exception as e:
        return f"Lỗi: {e}"

# --- GIAO DIỆN CHÍNH ---
st.title("⚡ Trạm Dịch Thuật & Giọng Đọc AI")
st.caption("Tối ưu cho trò chuyện 2 chiều — Nghe giọng đọc bản xứ tự nhiên")

# Thanh chọn giới tính giọng đọc chung cho toàn App
gioi_tinh_doc = st.radio(
    "🎙️ Chọn giọng đọc AI:", 
    ["Nữ", "Nam"], 
    horizontal=True
)

st.divider()

# === PHẦN 1: HỌ NÓI GÌ? ===
st.subheader("1️⃣ Đối tác gửi tin nhắn:")
msg_nhan = st.text_area("Dán tin nhắn ngoại ngữ vào đây:", height=90, placeholder="Hello! How are you today?...")

if st.button("⬇️ Dịch sang Tiếng Việt & Đọc", use_container_width=True, type="primary"):
    if msg_nhan:
        with st.spinner("AI đang dịch và tạo giọng đọc..."):
            ket_qua_vi = dich_van_ban(msg_nhan, huong_dich="vi")
            st.info(f"**Ý nghĩa Tiếng Việt:**\n\n{ket_qua_vi}")
            
            # Tạo âm thanh Tiếng Việt
            ma_giong_vi = VOICE_MAP["Tiếng Việt"][gioi_tinh_doc]
            audio_data = tao_am_thanh(ket_qua_vi, ma_giong_vi)
            
            st.caption("🔊 Nghe thử giọng đọc Tiếng Việt:")
            st.audio(audio_data, format="audio/mp3")

st.divider()

# === PHẦN 2: BẠN TRẢ LỜI ===
st.subheader("2️⃣ Bạn trả lời:")
msg_gui = st.text_area("Gõ câu trả lời Tiếng Việt:", height=90, placeholder="Tôi khỏe, cảm ơn bạn...")

col_lang, col_btn = st.columns([1, 1])
with col_lang:
    lang_select = st.selectbox("Chọn ngôn ngữ dịch sang:", list(VOICE_MAP.keys())[1:]) # Bỏ tiếng Việt ra khỏi danh sách đích
with col_btn:
    st.write("") 
    btn_dich_gui = st.button("⬇️ Dịch để Gửi & Đọc mẫu", use_container_width=True, type="primary")

if btn_dich_gui and msg_gui:
    with st.spinner("AI đang dịch và tạo giọng đọc..."):
        ket_qua_ngoai_ngu = dich_van_ban(msg_gui, huong_dich="out", ngon_ngu_dich=lang_select)
        
        st.success("**Kết quả (Bấm biểu tượng copy ở góc phải ô dưới để sao chép):**")
        st.code(ket_qua_ngoai_ngu, language=None)
        
        # Tạo âm thanh Ngoại ngữ chuẩn bản xứ
        ma_giong_ngoai_ngu = VOICE_MAP[lang_select][gioi_tinh_doc]
        audio_data_ngoai_ngu = tao_am_thanh(ket_qua_ngoai_ngu, ma_giong_ngoai_ngu)
        
        st.caption(f"🔊 Nghe thử giọng phát âm ({lang_select} - {gioi_tinh_doc}):")
        st.audio(audio_data_ngoai_ngu, format="audio/mp3")

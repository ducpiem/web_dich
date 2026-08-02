import streamlit as st
from google import genai
import edge_tts
import asyncio
import time

# --- CẤU HÌNH TRANG WEB ---
st.set_page_config(
    page_title="Trạm Dịch Thuật AI & Giọng Đọc",
    page_icon="⚡",
    layout="centered"
)
# === DIỆT TẬN GỐC BẢNG CLEAR CACHE KHI BẤM CTRL+C ===
st.markdown(
    """
    <script>
    const doc = window.parent.document;
    doc.addEventListener('keydown', function(e) {
        // Nếu bấm chữ C (hoặc Shift+C) mà không ở trong ô nhập liệu -> Chặn lệnh của Streamlit
        if ((e.key === 'c' || e.key === 'C') && !e.ctrlKey && !e.metaKey) {
            e.stopPropagation();
        }
    }, true);
    </script>
    """,
    unsafe_allow_html=True
)

# --- QUẢN LÝ NHIỀU API KEY XOAY VÒNG ---
# Lấy danh sách key từ két sắt Streamlit
if "GEMINI_KEYS" in st.secrets:
    list_keys = st.secrets["GEMINI_KEYS"]
else:
    # Dự phòng nếu chưa cấu hình danh sách
    list_keys = [st.secrets.get("GEMINI_API_KEY", "DEFAULT_KEY")]

# Khởi tạo vị trí key đang dùng trong session state
if "key_index" not in st.session_state:
    st.session_state.key_index = 0

def get_current_client():
    current_key = list_keys[st.session_state.key_index].strip()
    return genai.Client(api_key=current_key)

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

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    return loop.run_until_complete(_generate())

# --- HÀM DỊCH THÔNG MINH (CÓ TỰ ĐỘNG XOAY VÒNG KEY KHI HẾT QUOTA) ---
def dich_van_ban(text_goc, huong_dich, ngon_ngu_dich="Tiếng Anh"):
    if not text_goc.strip():
        return ""
    
    # Thử tối đa số lượng key đang có trong danh sách
    for attempt in range(len(list_keys)):
        try:
            client = get_current_client()
            
            if huong_dich == "vi":
                prompt = f"Dịch câu sau sang Tiếng Việt sát nghĩa, đúng văn phong nhắn tin trò chuyện. Chỉ trả về kết quả dịch: '{text_goc}'"
            else:
                prompt = f"Dịch câu Tiếng Việt sau sang {ngon_ngu_dich} tự nhiên như người bản xứ nhắn tin. Chỉ trả về kết quả dịch: '{text_goc}'"
                
            res = client.models.generate_content(
                model="gemini-3.5-flash-lite", 
                contents=prompt
            )
            return res.text.strip()
            
        except Exception as e:
            error_str = str(e)
            # Nếu dính lỗi hết quota (429), tự động chuyển sang Key của tài khoản Gmail tiếp theo
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                st.session_state.key_index = (st.session_state.key_index + 1) % len(list_keys)
                continue # Vòng lặp tiếp theo sẽ dùng key mới ngay lập tức
            else:
                return f"Lỗi: {e}"
                
    return "⚠️ Tất cả các tài khoản Gmail (API Key) của bạn đều đã tạm hết hạn mức lượt dùng. Vui lòng đợi lát nữa!"

# --- GIAO DIỆN CHÍNH ---
st.title("⚡ Trạm Dịch Thuật & Giọng Đọc AI")
st.caption(f"Đang quản lý {len(list_keys)} tài khoản Gmail tự động xoay vòng phòng thủ quá tải!")

gioi_tinh_doc = st.radio(
    "🎙️ Chọn giọng đọc AI:", 
    ["Nữ", "Nam"], 
    horizontal=True
)

st.divider()

# === PHẦN 1: HỌ NÓI GÌ? ===
st.subheader("1️⃣ Đối tác gửi tin nhắn:")
msg_nhan = st.text_area("Dán tin nhắn đa  ngữ vào đây  :", height=90, placeholder="Hello! How are you today?...")

if st.button("⬇️ Dịch sang Tiếng Việt & Đọc", use_container_width=True, type="primary"):
    if msg_nhan:
        with st.spinner("AI đang dịch và tạo giọng đọc..."):
            ket_qua_vi = dich_van_ban(msg_nhan, huong_dich="vi")
            st.info(f"**Ý nghĩa Tiếng Việt:**\n\n{ket_qua_vi}")
            
            ma_giong_vi = VOICE_MAP["Tiếng Việt"][gioi_tinh_doc]
            audio_data = tao_am_thanh(ket_qua_vi, ma_giong_vi)
            
            st.caption("🔊 Nghe thử giọng đọc Tiếng Việt:")
            st.audio(audio_data, format="audio/mp3")

st.divider()

# === PHẦN 2: BẠN TRẢ LỜI ===
st.subheader("2️⃣ Bạn trả lời:")
msg_gui = st.text_area("Gõ câu trả lời Tiếng Việt mà bạn muốn dịch sang ngôn ngữ  :", height=90, placeholder="Tôi khỏe, cảm ơn bạn...")

col_lang, col_btn = st.columns([1, 1])
with col_lang:
    lang_select = st.selectbox("Chọn ngôn ngữ dịch sang:", list(VOICE_MAP.keys())[1:])
with col_btn:
    st.write("") 
    btn_dich_gui = st.button("⬇️ Dịch để Gửi & Đọc mẫu", use_container_width=True, type="primary")

if btn_dich_gui and msg_gui:
    with st.spinner("AI đang dịch và tạo giọng đọc..."):
        ket_qua_ngoai_ngu = dich_van_ban(msg_gui, huong_dich="out", ngon_ngu_dich=lang_select)
        
        st.success("**Kết quả (Bấm biểu tượng copy ở góc phải ô dưới để sao chép):**")
        st.code(ket_qua_ngoai_ngu, language=None)
        
        ma_giong_ngoai_ngu = VOICE_MAP[lang_select][gioi_tinh_doc]
        audio_data_ngoai_ngu = tao_am_thanh(ket_qua_ngoai_ngu, ma_giong_ngoai_ngu)
        
        st.caption(f"🔊 Nghe thử giọng phát âm ({lang_select} - {gioi_tinh_doc}):")
        st.audio(audio_data_ngoai_ngu, format="audio/mp3")

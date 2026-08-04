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

# === CSS & JAVASCRIPT: NÚT NỔI Ở GÓC DƯỚI KHUNG NHẬP LIỆU (Y HỆT HÌNH MẪU) ===
st.markdown(
    """
    <style>
    /* Định vị khung nhập liệu làm chuẩn */
    div[data-testid="stTextArea"] {
        position: relative !important;
    }
    
    /* Chống chữ bị đè lên các nút ở góc dưới bên phải */
    div[data-testid="stTextArea"] textarea {
        padding-right: 90px !important;
        padding-bottom: 30px !important;
    }

    /* Khung chứa nút nằm nổi góc dưới bên phải */
    .floating-btn-container {
        position: absolute;
        right: 10px;
        bottom: 10px;
        display: flex;
        gap: 6px;
        z-index: 99;
    }

    /* Phong cách nút icon bo góc màu tối giống ảnh */
    .floating-btn {
        background-color: rgba(30, 34, 45, 0.85);
        color: #e0e0e0;
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 8px;
        padding: 6px 10px;
        font-size: 12px;
        font-weight: 500;
        cursor: pointer;
        backdrop-filter: blur(4px);
        transition: all 0.2s ease-in-out;
        display: flex;
        align-items: center;
        gap: 4px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.4);
    }

    .floating-btn:hover {
        background-color: rgba(50, 58, 75, 0.95);
        border-color: rgba(255, 255, 255, 0.3);
        color: #ffffff;
        transform: translateY(-1px);
    }

    .floating-btn:active {
        transform: translateY(1px);
    }
    </style>

    <script>
    const doc = window.parent.document;

    // Chặn phím C mở bảng clear cache Streamlit
    doc.addEventListener('keydown', function(e) {
        if ((e.key === 'c' || e.key === 'C') && !e.ctrlKey && !e.metaKey) {
            e.stopPropagation();
        }
    }, true);

    // Hàm tự động gắn nút Dán & Xóa vào góc dưới các ô nhập liệu
    function injectFloatingButtons() {
        const containers = doc.querySelectorAll('div[data-testid="stTextArea"]');
        
        containers.forEach((container) => {
            if (container.querySelector('.floating-btn-container')) return;
            
            const textarea = container.querySelector('textarea');
            if (!textarea) return;

            const btnBox = doc.createElement('div');
            btnBox.className = 'floating-btn-container';

            // Nút Dán (Paste)
            const pasteBtn = doc.createElement('button');
            pasteBtn.className = 'floating-btn';
            pasteBtn.type = 'button';
            pasteBtn.innerHTML = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"></path><rect x="8" y="2" width="8" height="4" rx="1" ry="1"></rect></svg> Dán`;
            pasteBtn.onclick = async (e) => {
                e.preventDefault();
                e.stopPropagation();
                try {
                    const text = await navigator.clipboard.readText();
                    textarea.value = text;
                    textarea.dispatchEvent(new Event('input', { bubbles: true }));
                    textarea.dispatchEvent(new Event('change', { bubbles: true }));
                } catch (err) {
                    textarea.focus();
                    alert('Chạm giữ trực tiếp vào ô để chọn "Dán" nếu trình duyệt chưa cấp quyền Clipboard!');
                }
            };

            // Nút Xóa (Clear)
            const clearBtn = doc.createElement('button');
            clearBtn.className = 'floating-btn';
            clearBtn.type = 'button';
            clearBtn.innerHTML = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg> Xóa`;
            clearBtn.onclick = (e) => {
                e.preventDefault();
                e.stopPropagation();
                textarea.value = '';
                textarea.dispatchEvent(new Event('input', { bubbles: true }));
                textarea.dispatchEvent(new Event('change', { bubbles: true }));
            };

            btnBox.appendChild(pasteBtn);
            btnBox.appendChild(clearBtn);
            container.appendChild(btnBox);
        });
    }

    // Chạy liên tục để luôn giữ nút ở góc ô nhập liệu ngay cả khi load lại trang
    setInterval(injectFloatingButtons, 400);
    </script>
    """,
    unsafe_allow_html=True
)

# --- QUẢN LÝ NHIỀU API KEY XOAY VÒNG ---
if "GEMINI_KEYS" in st.secrets:
    list_keys = st.secrets["GEMINI_KEYS"]
else:
    list_keys = [st.secrets.get("GEMINI_API_KEY", "DEFAULT_KEY")]

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
    "Tiếng Đức": {
        "Nữ": "de-DE-KatjaNeural",
        "Nam": "de-DE-ConradNeural"
    },
    "Tiếng Tây Ban Nha (Mexico)": {
        "Nữ": "es-MX-DaliaNeural",
        "Nam": "es-MX-JorgeNeural"
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

# --- HÀM DỊCH THÔNG MINH ---
def dich_van_ban(text_goc, huong_dich, ngon_ngu_dich="Tiếng Anh"):
    if not text_goc.strip():
        return ""
    
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
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                st.session_state.key_index = (st.session_state.key_index + 1) % len(list_keys)
                continue
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
msg_nhan = st.text_area("Dán tin nhắn đa ngôn ngữ vào đây:", height=100, placeholder="Hello! How are you today?...", key="input_nhan")

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
msg_gui = st.text_area("Gõ câu trả lời Tiếng Việt mà bạn muốn dịch sang ngôn ngữ:", height=100, placeholder="Tôi khỏe, cảm ơn bạn...", key="input_gui")

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

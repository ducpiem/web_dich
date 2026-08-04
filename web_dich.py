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
        if ((e.key === 'c' || e.key === 'C') && !e.ctrlKey && !e.metaKey) {
            e.stopPropagation();
        }
    }, true);
    </script>
    """,
    unsafe_allow_html=True
)

# --- JAVASCRIPT HỖ TRỢ XÓA & COPY AN TOÀN CHO CẢ SAFARI & CHROME ---
st.markdown(
    """
    <script>
    function copyToClipboard(text) {
        navigator.clipboard.writeText(text).then(() => {
            showToast('📋 Đã copy kết quả vào bộ nhớ tạm!');
        }).catch(err => {
            const el = document.createElement('textarea');
            el.value = text;
            document.body.appendChild(el);
            el.select();
            document.execCommand('copy');
            document.body.removeChild(el);
            showToast('📋 Đã copy kết quả!');
        });
    }

    function clearBox(boxType) {
        const doc = window.parent.document;
        const textareas = doc.querySelectorAll('textarea');
        let target = (boxType === 'nhan') ? textareas[0] : textareas[textareas.length > 2 ? 2 : 1];
        
        if (target) {
            target.value = '';
            target.dispatchEvent(new Event('input', { bubbles: true }));
            showToast('🗑️ Đã xóa nội dung!');
        }
    }

    function showToast(message) {
        const toast = document.createElement('div');
        toast.innerText = message;
        toast.style.position = 'fixed';
        toast.style.bottom = '30px';
        toast.style.left = '50%';
        toast.style.transform = 'translateX(-50%)';
        toast.style.background = '#28a745';
        toast.style.color = 'white';
        toast.style.padding = '10px 20px';
        toast.style.borderRadius = '20px';
        toast.style.zIndex = '99999';
        toast.style.fontSize = '14px';
        toast.style.boxShadow = '0px 4px 10px rgba(0,0,0,0.3)';
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 2000);
    }
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

# --- LƯU TRỮ TRẠNG THÁI KẾT QUẢ ---
if "ket_qua_vi" not in st.session_state:
    st.session_state.ket_qua_vi = ""
if "audio_vi" not in st.session_state:
    st.session_state.audio_vi = None

if "ket_qua_NN" not in st.session_state:
    st.session_state.ket_qua_NN = ""
if "audio_NN" not in st.session_state:
    st.session_state.audio_NN = None

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

# --- HÀM TẠO ÂM THANH AI ---
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
                
    return "⚠️ Tất cả các tài khoản Gmail đều tạm hết hạn mức. Vui lòng thử lại sau giây lát!"

# --- GIAO DIỆN CHÍNH ---
st.title("⚡ Trạm Dịch Thuật & Giọng Đọc AI")
st.caption(f"Hệ thống quản lý {len(list_keys)} tài khoản Gmail xoay vòng tự động")

gioi_tinh_doc = st.radio(
    "🎙️ Chọn giọng đọc AI:", 
    ["Nữ", "Nam"], 
    horizontal=True
)

st.divider()

# === PHẦN 1: HỌ NÓI GÌ? ===
col_h1, col_b1 = st.columns([2, 2])
with col_h1:
    st.subheader("1️⃣ Đối tác gửi tin nhắn:")
with col_b1:
    st.markdown("""
        <div style="text-align: right; padding-top: 6px;">
            <span style="font-size: 11px; color: #888; margin-right: 8px;">💡 Chạm ô dưới để dán</span>
            <button onclick="clearBox('nhan')" style="background: #2b313e; color: #ff4b4b; border: 1px solid #555; padding: 4px 10px; border-radius: 4px; font-size: 12px; cursor: pointer;">🗑️ Xóa</button>
        </div>
    """, unsafe_allow_html=True)

msg_nhan = st.text_area("Dán tin nhắn ngoại ngữ vào đây:", height=90, placeholder="Chạm vào đây rồi bấm 'Dán' từ điện thoại...", key="input_nhan")

if st.button("⬇️ Dịch sang Tiếng Việt & Đọc", use_container_width=True, type="primary", key="btn_dich_1"):
    if msg_nhan:
        with st.spinner("AI đang dịch và tạo giọng đọc..."):
            st.session_state.ket_qua_vi = dich_van_ban(msg_nhan, huong_dich="vi")
            ma_giong_vi = VOICE_MAP["Tiếng Việt"][gioi_tinh_doc]
            st.session_state.audio_vi = tao_am_thanh(st.session_state.ket_qua_vi, ma_giong_vi)

# Hiển thị kết quả phần 1
if st.session_state.ket_qua_vi:
    st.info("**Ý nghĩa Tiếng Việt:**")
    st.text_area("Kết quả tiếng Việt:", value=st.session_state.ket_qua_vi, height=80, key="txt_vi_out")
    
    st.markdown(f"""
        <div style="text-align: right; margin-top: -6px; margin-bottom: 15px;">
            <button onclick="copyToClipboard(`{st.session_state.ket_qua_vi.replace('`', '\\`')}`)" style="background: #ff4b4b; color: white; border: none; padding: 6px 14px; border-radius: 6px; font-size: 13px; font-weight: bold; cursor: pointer;">📋 Copy Kết Quả</button>
        </div>
    """, unsafe_allow_html=True)
    
    if st.session_state.audio_vi:
        st.caption("🔊 Nghe thử giọng đọc Tiếng Việt:")
        st.audio(st.session_state.audio_vi, format="audio/mp3")

st.divider()

# === PHẦN 2: BẠN TRẢ LỜI ===
col_h2, col_b2 = st.columns([2, 2])
with col_h2:
    st.subheader("2️⃣ Bạn trả lời:")
with col_b2:
    st.markdown("""
        <div style="text-align: right; padding-top: 6px;">
            <span style="font-size: 11px; color: #888; margin-right: 8px;">💡 Chạm ô dưới để dán</span>
            <button onclick="clearBox('gui')" style="background: #2b313e; color: #ff4b4b; border: 1px solid #555; padding: 4px 10px; border-radius: 4px; font-size: 12px; cursor: pointer;">🗑️ Xóa</button>
        </div>
    """, unsafe_allow_html=True)

msg_gui = st.text_area("Gõ câu trả lời Tiếng Việt:", height=90, placeholder="Gõ hoặc dán nội dung vào đây...", key="input_gui")

col_lang, col_btn = st.columns([1, 1])
with col_lang:
    lang_select = st.selectbox("Chọn ngôn ngữ dịch sang:", list(VOICE_MAP.keys())[1:])
with col_btn:
    st.write("") 
    btn_dich_gui = st.button("⬇️ Dịch để Gửi & Đọc mẫu", use_container_width=True, type="primary", key="btn_dich_2")

if btn_dich_gui and msg_gui:
    with st.spinner("AI đang dịch và tạo giọng đọc..."):
        st.session_state.ket_qua_NN = dich_van_ban(msg_gui, huong_dich="out", ngon_ngu_dich=lang_select)
        ma_giong_ngoai_ngu = VOICE_MAP[lang_select][gioi_tinh_doc]
        st.session_state.audio_NN = tao_am_thanh(st.session_state.ket_qua_NN, ma_giong_ngoai_ngu)

# Hiển thị kết quả phần 2
if st.session_state.ket_qua_NN:
    st.success("**Kết quả dịch ngoại ngữ:**")
    st.text_area("Kết quả dịch:", value=st.session_state.ket_qua_NN, height=80, key="txt_nn_out")
    
    st.markdown(f"""
        <div style="text-align: right; margin-top: -6px; margin-bottom: 15px;">
            <button onclick="copyToClipboard(`{st.session_state.ket_qua_NN.replace('`', '\\`')}`)" style="background: #ff4b4b; color: white; border: none; padding: 6px 14px; border-radius: 6px; font-size: 13px; font-weight: bold; cursor: pointer;">📋 Copy Kết Quả</button>
        </div>
    """, unsafe_allow_html=True)
    
    if st.session_state.audio_NN:
        st.caption(f"🔊 Nghe thử giọng phát âm ({lang_select} - {gioi_tinh_doc}):")
        st.audio(st.session_state.audio_NN, format="audio/mp3")

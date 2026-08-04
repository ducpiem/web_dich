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

# === CSS & JAVASCRIPT: ICON COPY/PASTE NHỎ GỌN TRONG GÓC TẤT CẢ CÁC Ô ===
st.markdown(
    """
    <style>
    /* Ép tất cả các ô text phải chừa lại một khoảng trống bên dưới để chữ không đè lên icon */
    div[data-baseweb="textarea"] textarea {
        padding-bottom: 30px !important;
    }
    </style>

    <script>
    const targetDoc = window.parent.document;

    function injectTinyIcons() {
        // Tìm chính xác cái khung nền xám của tất cả các ô trên web
        const wrappers = targetDoc.querySelectorAll('div[data-baseweb="textarea"]');
        
        wrappers.forEach(wrapper => {
            // Nếu ô này đã được gắn icon rồi thì bỏ qua
            if (wrapper.querySelector('.tiny-icons-box')) return;
            
            const textarea = wrapper.querySelector('textarea');
            if(!textarea) return;

            // Tạo khung chứa 2 icon nho nhỏ
            const iconBox = targetDoc.createElement('div');
            iconBox.className = 'tiny-icons-box';
            iconBox.style.position = 'absolute';
            iconBox.style.right = '10px';
            iconBox.style.bottom = '8px';
            iconBox.style.display = 'flex';
            iconBox.style.gap = '12px';
            iconBox.style.zIndex = '99';
            
            // --- ICON DÁN (PASTE) ---
            const pasteBtn = targetDoc.createElement('div');
            pasteBtn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#a0a0a0" stroke-width="2"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"></path><rect x="8" y="2" width="8" height="4" rx="1" ry="1"></rect></svg>`;
            pasteBtn.style.cursor = 'pointer';
            pasteBtn.title = 'Dán';
            pasteBtn.onclick = async (e) => {
                e.preventDefault();
                try {
                    const text = await navigator.clipboard.readText();
                    // Lệnh bắt buộc Streamlit nhận diện chữ vừa dán
                    const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value").set;
                    setter.call(textarea, text);
                    textarea.dispatchEvent(new Event('input', { bubbles: true }));
                } catch(err) {
                    alert('Chạm giữ vào ô để chọn "Dán" nếu trình duyệt chặn quyền!');
                }
            };
            
            // --- ICON COPY ---
            const copySvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#a0a0a0" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>`;
            const checkSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#00ff00" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg>`;
            
            const copyBtn = targetDoc.createElement('div');
            copyBtn.innerHTML = copySvg;
            copyBtn.style.cursor = 'pointer';
            copyBtn.title = 'Copy';
            copyBtn.onclick = (e) => {
                e.preventDefault();
                navigator.clipboard.writeText(textarea.value).then(() => {
                    // Đổi sang dấu tích xanh 1.5s để báo hiệu đã copy
                    copyBtn.innerHTML = checkSvg;
                    setTimeout(() => copyBtn.innerHTML = copySvg, 1500);
                });
            };

            // Hiệu ứng rê chuột vào thì icon sáng lên
            [pasteBtn, copyBtn].forEach(btn => {
                btn.onmouseover = () => { btn.querySelector('svg').setAttribute('stroke', '#ffffff'); };
                btn.onmouseout = () => { btn.querySelector('svg').setAttribute('stroke', '#a0a0a0'); };
            });

            iconBox.appendChild(pasteBtn);
            iconBox.appendChild(copyBtn);
            wrapper.appendChild(iconBox);
        });
    }

    // Vòng lặp quét liên tục siêu nhanh (300ms) để ô nào vừa hiện ra là gắn icon ngay lập tức
    setInterval(injectTinyIcons, 300);

    // Chặn bảng clear cache khó chịu của Streamlit
    targetDoc.addEventListener('keydown', function(e) {
        if ((e.key === 'c' || e.key === 'C') && !e.ctrlKey && !e.metaKey) {
            e.stopPropagation();
        }
    }, true);
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

# --- BỘ TỪ ĐIỂN GIỌNG ĐỌC AI ---
VOICE_MAP = {
    "Tiếng Việt": {"Nữ": "vi-VN-HoaiMyNeural", "Nam": "vi-VN-NamMinhNeural"},
    "Tiếng Anh": {"Nữ": "en-US-JennyNeural", "Nam": "en-US-GuyNeural"},
    "Tiếng Đức": {"Nữ": "de-DE-KatjaNeural", "Nam": "de-DE-ConradNeural"},
    "Tiếng Tây Ban Nha (Mexico)": {"Nữ": "es-MX-DaliaNeural", "Nam": "es-MX-JorgeNeural"},
    "Tiếng Trung (Phồn thể/Giản thể)": {"Nữ": "zh-CN-XiaoxiaoNeural", "Nam": "zh-CN-YunxiNeural"},
    "Tiếng Nhật": {"Nữ": "ja-JP-NanamiNeural", "Nam": "ja-JP-KeitaNeural"},
    "Tiếng Hàn": {"Nữ": "ko-KR-SunHiNeural", "Nam": "ko-KR-InJoonNeural"},
    "Tiếng Pháp": {"Nữ": "fr-FR-DeniseNeural", "Nam": "fr-FR-HenriNeural"}
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
                
            res = client.models.generate_content(model="gemini-3.5-flash-lite", contents=prompt)
            return res.text.strip()
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                st.session_state.key_index = (st.session_state.key_index + 1) % len(list_keys)
                continue
            else:
                return f"Lỗi: {e}"
    return "⚠️ Tất cả tài khoản Gmail đều tạm hết hạn mức. Vui lòng thử lại sau!"

# --- GIAO DIỆN CHÍNH ---
st.title("⚡ Trạm Dịch Thuật & Giọng Đọc AI")
st.caption(f"Đang quản lý {len(list_keys)} tài khoản Gmail tự động xoay vòng!")

gioi_tinh_doc = st.radio("🎙️ Chọn giọng đọc AI:", ["Nữ", "Nam"], horizontal=True)

st.divider()

# === PHẦN 1: HỌ NÓI GÌ? ===
st.subheader("1️⃣ Đối tác gửi tin nhắn:")
msg_nhan = st.text_area("Dán tin nhắn đa ngôn ngữ vào đây:", height=100, placeholder="Hello! How are you today?...", key="input_nhan")

if st.button("⬇️ Dịch sang Tiếng Việt & Đọc", use_container_width=True, type="primary"):
    if msg_nhan:
        with st.spinner("AI đang dịch và tạo giọng đọc..."):
            ket_qua_vi = dich_van_ban(msg_nhan, huong_dich="vi")
            
            # Xuất kết quả bằng text_area để nó tự động được gắn icon copy/paste
            st.text_area("Ý nghĩa Tiếng Việt:", value=ket_qua_vi, height=100, key="out_vi")
            
            ma_giong_vi = VOICE_MAP["Tiếng Việt"][gioi_tinh_doc]
            audio_data = tao_am_thanh(ket_qua_vi, ma_giong_vi)
            st.caption("🔊 Nghe thử giọng đọc Tiếng Việt:")
            st.audio(audio_data, format="audio/mp3")

st.divider()

# === PHẦN 2: BẠN TRẢ LỜI ===
st.subheader("2️⃣ Bạn trả lời:")
msg_gui = st.text_area("Gõ câu trả lời Tiếng Việt mà bạn muốn dịch:", height=100, placeholder="Tôi khỏe, cảm ơn bạn...", key="input_gui")

col_lang, col_btn = st.columns([1, 1])
with col_lang:
    lang_select = st.selectbox("Chọn ngôn ngữ dịch sang:", list(VOICE_MAP.keys())[1:])
with col_btn:
    st.write("") 
    btn_dich_gui = st.button("⬇️ Dịch để Gửi & Đọc mẫu", use_container_width=True, type="primary")

if btn_dich_gui and msg_gui:
    with st.spinner("AI đang dịch và tạo giọng đọc..."):
        ket_qua_ngoai_ngu = dich_van_ban(msg_gui, huong_dich="out", ngon_ngu_dich=lang_select)
        
        # Xuất kết quả bằng text_area để tự động được gắn icon copy/paste
        st.text_area(f"Kết quả ({lang_select}):", value=ket_qua_ngoai_ngu, height=100, key="out_nn")
        
        ma_giong_ngoai_ngu = VOICE_MAP[lang_select][gioi_tinh_doc]
        audio_data_ngoai_ngu = tao_am_thanh(ket_qua_ngoai_ngu, ma_giong_ngoai_ngu)
        st.caption(f"🔊 Nghe thử giọng phát âm ({lang_select} - {gioi_tinh_doc}):")
        st.audio(audio_data_ngoai_ngu, format="audio/mp3")

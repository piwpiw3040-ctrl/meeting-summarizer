# -*- coding: utf-8 -*-
"""
app.py - AI Meeting Summarizer (iOS Edition)
Mobile-first Thai meeting audio summarizer with Speaker Mapping, Direct Native PDF,
and clean iOS Human Interface Design.
"""

import os
import io
import re
import sys
import json
import time
import tempfile
from pathlib import Path
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv

# Ensure console supports UTF-8 on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Import Native PDF generator safely
try:
    from pdf_generator import create_pdf_bytes
except Exception as _pdf_err:
    create_pdf_bytes = None

# Load environment
base_dir = Path(__file__).resolve().parent
env_file = base_dir / ".env"
if env_file.exists():
    load_dotenv(dotenv_path=env_file)
else:
    load_dotenv()

# Page config for Mobile iOS Experience
st.set_page_config(
    page_title="สรุปการประชุม AI",
    page_icon="🎙️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Custom iOS Native Theme CSS
st.markdown("""
<style>
    /* iOS System Base */
    html, body, [data-testid="stAppViewContainer"] {
        background-color: #F2F2F7 !important;
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Sarabun", sans-serif !important;
        color: #1C1C1E;
    }

    /* Container Spacing */
    .block-container {
        padding-top: 1.25rem !important;
        padding-bottom: 3.5rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 720px !important;
    }

    /* iOS Cards */
    .ios-card {
        background: #FFFFFF;
        border-radius: 18px;
        padding: 1.25rem 1.4rem;
        margin-bottom: 1.1rem;
        box-shadow: 0 4px 18px rgba(0, 0, 0, 0.04);
        border: 1px solid rgba(0, 0, 0, 0.04);
    }

    /* iOS Buttons */
    .stButton>button {
        width: 100%;
        border-radius: 14px !important;
        height: 3.1rem !important;
        font-weight: 600 !important;
        font-size: 1.02rem !important;
        background: #007AFF !important;
        color: #FFFFFF !important;
        border: none !important;
        box-shadow: 0 4px 12px rgba(0, 122, 255, 0.25) !important;
        transition: all 0.15s ease !important;
    }
    .stButton>button:hover {
        background: #0062CC !important;
        box-shadow: 0 6px 16px rgba(0, 122, 255, 0.35) !important;
        transform: translateY(-1px) !important;
    }
    .stButton>button:active {
        transform: scale(0.98) !important;
    }

    /* Download Buttons */
    .stDownloadButton>button {
        width: 100%;
        border-radius: 12px !important;
        height: 2.9rem !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        border: 1px solid #E5E5EA !important;
        background: #FFFFFF !important;
        color: #007AFF !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03) !important;
        transition: all 0.15s ease !important;
    }
    .stDownloadButton>button:hover {
        background: #F2F2F7 !important;
        border-color: #007AFF !important;
    }

    /* Text inputs */
    .stTextInput input {
        border-radius: 12px !important;
        border: 1px solid #D1D1D6 !important;
        background-color: #F8F8FA !important;
        padding: 0.6rem 0.9rem !important;
        font-size: 0.95rem !important;
    }
    .stTextInput input:focus {
        border-color: #007AFF !important;
        background-color: #FFFFFF !important;
        box-shadow: 0 0 0 3px rgba(0, 122, 255, 0.15) !important;
    }

    /* Speaker badge */
    .speaker-pill {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        font-size: 0.82rem;
        font-weight: 700;
        border-radius: 20px;
        background-color: #E5F1FF;
        color: #007AFF;
        margin-bottom: 0.35rem;
    }

    .quote-box {
        background: #F9F9FB;
        border-left: 3px solid #007AFF;
        padding: 0.6rem 0.85rem;
        border-radius: 0 10px 10px 0;
        font-size: 0.88rem;
        color: #48484A;
        margin: 0.4rem 0 0.8rem 0;
        line-height: 1.45;
    }
</style>
""", unsafe_allow_html=True)


# ================= SECURITY / PIN LOCK =================
APP_PIN = "304000"
try:
    if hasattr(st, "secrets") and "APP_PASSWORD" in st.secrets:
        APP_PIN = str(st.secrets["APP_PASSWORD"]).strip()
except Exception:
    pass

if not st.session_state.get("authenticated", False):
    st.markdown("""
    <div style="text-align: center; margin-top: 3.5rem; margin-bottom: 2rem;">
        <div style="font-size: 3.5rem; margin-bottom: 0.4rem;">🎙️</div>
        <h2 style="font-size: 1.65rem; color: #1C1C1E; font-weight: 700; margin-bottom: 0.2rem;">สรุปบันทึกการประชุม AI</h2>
        <p style="color: #8E8E93; font-size: 0.95rem;">พื้นที่ส่วนตัว — กรุณากรอกรหัสผ่านเพื่อเข้าใช้งาน</p>
    </div>
    """, unsafe_allow_html=True)

    with st.form("login_form"):
        entered_pin = st.text_input("รหัสผ่าน (Passcode PIN):", type="password", placeholder="ใส่รหัสผ่าน 6 หลัก")
        login_btn = st.form_submit_button("🔓 ปลดล็อกเข้าใช้งาน")
        if login_btn:
            if entered_pin.strip() == APP_PIN:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("❌ รหัสผ่านไม่ถูกต้อง กรุณาลองใหม่อีกครั้งครับ")

    st.stop()


# ================= CONFIGURATION & SECRETS =================
api_key_env = ""
try:
    if hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
        api_key_env = str(st.secrets["GEMINI_API_KEY"]).strip()
except Exception:
    pass

if not api_key_env:
    api_key_env = os.getenv("GEMINI_API_KEY", "").strip()

model_default = "gemini-3.8-flash"
try:
    if hasattr(st, "secrets") and "GEMINI_MODEL" in st.secrets:
        model_default = str(st.secrets["GEMINI_MODEL"]).strip()
except Exception:
    pass
if not model_default:
    model_default = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()

# Sidebar: Preferences & Logout
with st.sidebar:
    st.header("⚙️ การตั้งค่าระบบ")
    api_key_input = st.text_input(
        "Google Gemini API Key:",
        value=api_key_env,
        type="password",
        help="ขอ API Key ฟรีได้ที่ https://aistudio.google.com/app/apikey"
    )
    model_name = st.selectbox(
        "โมเดลหลัก (Primary Model):",
        options=["gemini-3.8-flash", "gemini-flash-latest", "gemini-3.7-flash"],
        index=0
    )
    st.markdown("---")
    st.markdown("### 📱 ติดตั้งลงหน้าจอมือถือ (PWA)")
    st.caption("• **iPhone (Safari):** กดปุ่มแชร์ (สี่เหลี่ยมลูกศรชี้ขึ้น) แล้วเลือก 'Add to Home Screen'")
    st.caption("• **Android (Chrome):** กดปุ่ม 3 จุด (⋮) แล้วเลือก 'เพิ่มลงในหน้าจอหลัก'")
    st.markdown("---")
    if st.button("🔒 ล็อกหน้าจอ / ออกจากระบบ", key="logout_btn"):
        st.session_state["authenticated"] = False
        st.rerun()

# Resolve API Key
active_key = api_key_input.strip() or api_key_env.strip()
if not active_key or active_key == "YOUR_GEMINI_API_KEY_HERE":
    st.warning("⚠️ ยังไม่พบ Gemini API Key ในระบบ")
    with st.expander("🔑 แตะที่นี่เพื่อใส่ API Key ของคุณได้ทันที", expanded=True):
        main_key_input = st.text_input(
            "วาง Gemini API Key ของคุณที่นี่:",
            type="password",
            placeholder="AIzaSy... หรือ AQ.Ab...",
            help="ขอ API Key ฟรีได้ที่ https://aistudio.google.com/app/apikey"
        )
        if main_key_input:
            st.session_state["custom_api_key"] = main_key_input.strip()
            active_key = main_key_input.strip()
            st.rerun()

    if "custom_api_key" in st.session_state:
        active_key = st.session_state["custom_api_key"]

    if not active_key or active_key == "YOUR_GEMINI_API_KEY_HERE":
        st.info("💡 สามารถขอ API Key ฟรีได้ที่ Google AI Studio แล้วนำมาวางในกล่องข้อความด้านบนครับ")
        st.stop()


# ================= HELPER FUNCTIONS =================
def get_mime_type(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    mime_map = {
        ".mp3": "audio/mp3",
        ".m4a": "audio/mp4",
        ".wav": "audio/wav",
        ".aac": "audio/aac",
        ".ogg": "audio/ogg",
        ".flac": "audio/flac",
        ".webm": "audio/webm",
        ".mp4": "video/mp4",
        ".m4v": "video/mp4",
    }
    return mime_map.get(ext, "audio/mp3")


def create_docx_bytes(markdown_text: str) -> bytes:
    """Generate Word .docx in memory from markdown."""
    import docx
    from docx.shared import Inches, Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
    from docx.oxml import parse_xml
    from docx.oxml.ns import nsdecls

    font_name = "TH Sarabun New"
    doc = docx.Document()

    for section in doc.sections:
        section.page_width = Inches(8.27)
        section.page_height = Inches(11.69)
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.8)
        section.right_margin = Inches(0.8)

        hp = section.header.paragraphs[0]
        hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        hrun = hp.add_run("บันทึกการประชุมภายใน (Meeting Minutes)")
        hrun.font.name = font_name
        hrun.font.size = Pt(10)
        hrun.font.color.rgb = RGBColor(113, 128, 150)

    lines = markdown_text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line or line in ['---', '***', '___']:
            i += 1
            continue

        if line.startswith('|') and line.endswith('|'):
            t_lines = [line]
            i += 1
            while i < len(lines) and lines[i].strip().startswith('|') and lines[i].strip().endswith('|'):
                t_lines.append(lines[i].strip())
                i += 1
            if len(t_lines) >= 3:
                raw_hdr = [c.strip() for c in t_lines[0].split('|')[1:-1]]
                rows_data = [[c.strip() for c in l.split('|')[1:-1]] for l in t_lines[2:]]
                tbl = doc.add_table(rows=len(rows_data) + 1, cols=len(raw_hdr))
                tbl.alignment = WD_TABLE_ALIGNMENT.CENTER

                for idx, h in enumerate(raw_hdr):
                    c = tbl.rows[0].cells[idx]
                    c._tc.get_or_add_tcPr().append(parse_xml(f'<w:shd {nsdecls("w")} w:fill="1B365D"/>'))
                    p = c.paragraphs[0]
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER if idx != 1 else WD_ALIGN_PARAGRAPH.LEFT
                    r = p.add_run(h)
                    r.font.name = font_name
                    r.font.size = Pt(12.5)
                    r.font.bold = True
                    r.font.color.rgb = RGBColor(255, 255, 255)

                for r_idx, r_data in enumerate(rows_data):
                    r_el = tbl.rows[r_idx + 1]
                    bg = "F1F5F9" if r_idx % 2 == 1 else "FFFFFF"
                    for col_idx in range(len(raw_hdr)):
                        c = r_el.cells[col_idx]
                        if bg != "FFFFFF":
                            c._tc.get_or_add_tcPr().append(parse_xml(f'<w:shd {nsdecls("w")} w:fill="{bg}"/>'))
                        val = r_data[col_idx] if col_idx < len(r_data) else ""
                        p = c.paragraphs[0]
                        p.alignment = WD_ALIGN_PARAGRAPH.CENTER if col_idx in [0, 2, 3] else WD_ALIGN_PARAGRAPH.LEFT
                        r = p.add_run(val)
                        r.font.name = font_name
                        r.font.size = Pt(12)
            continue

        p = doc.add_paragraph()
        if line.startswith('# '):
            p.paragraph_format.space_before = Pt(6)
            p.paragraph_format.space_after = Pt(12)
            r = p.add_run(line[2:].strip())
            r.font.name = font_name
            r.font.size = Pt(20)
            r.font.bold = True
            r.font.color.rgb = RGBColor(27, 54, 93)
        elif line.startswith('## '):
            p.paragraph_format.space_before = Pt(14)
            p.paragraph_format.space_after = Pt(6)
            r = p.add_run(line[3:].strip())
            r.font.name = font_name
            r.font.size = Pt(15)
            r.font.bold = True
            r.font.color.rgb = RGBColor(27, 54, 93)
        elif line.startswith('### '):
            p.paragraph_format.space_before = Pt(10)
            p.paragraph_format.space_after = Pt(4)
            r = p.add_run(line[4:].strip())
            r.font.name = font_name
            r.font.size = Pt(13.5)
            r.font.bold = True
            r.font.color.rgb = RGBColor(43, 108, 176)
        else:
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(4)
            p.paragraph_format.line_spacing = 1.15
            tokens = re.split(r'(\*\*.*?\*\*)', line)
            for t in tokens:
                if t.startswith('**') and t.endswith('**'):
                    r = p.add_run(t[2:-2])
                    r.font.bold = True
                else:
                    r = p.add_run(t)
                r.font.name = font_name
                r.font.size = Pt(13)
        i += 1

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()


def parse_gemini_response(response_text: str) -> dict:
    """Robustly parse JSON response from Gemini, handling markdown code fences."""
    cleaned = response_text.strip()
    if "```json" in cleaned:
        cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in cleaned:
        cleaned = cleaned.split("```", 1)[1].split("```", 1)[0].strip()

    try:
        return json.loads(cleaned)
    except Exception:
        # Fallback if model responded in plain markdown
        return {
            "speakers": [],
            "summary_markdown_template": response_text
        }


def apply_speaker_mapping(template_text: str, speaker_mapping: dict) -> str:
    """Replace {{speaker_id}} or [speaker_id] placeholders with real user-entered names."""
    result = template_text
    for spk_id, real_name in speaker_mapping.items():
        chosen_name = real_name.strip() if real_name and real_name.strip() else spk_id
        # Replace {{Speaker X}}
        result = result.replace(f"{{{{{spk_id}}}}}", chosen_name)
        # Replace [Speaker X]
        result = result.replace(f"[{spk_id}]", chosen_name)
    return result


AI_JSON_PROMPT = """คุณคือเลขานุการและผู้เชี่ยวชาญด้านการวิเคราะห์การประชุมระดับผู้บริหาร (Senior Executive Meeting Analyst)
โปรดฟังเสียงบันทึกการประชุมที่แนบมานี้อย่างละเอียด แล้วสกัดข้อมูลออกมาเป็น JSON อย่างเคร่งครัดตามโครงสร้างดังต่อไปนี้:

{{
  "speakers": [
    {{
      "speaker_id": "ผู้พูด A",
      "voice_traits": "เสียงผู้ชาย ทุ้มลึก พูดจังหวะมั่นคง สุขุม",
      "sample_quote": "ประโยคจริงที่คนนี้พูดในที่ประชุมสั้นๆ เพื่อให้เจ้าของจำเสียงได้",
      "suggested_role": "ประธานที่ประชุม / ผู้จัดการ"
    }}
  ],
  "summary_markdown_template": "เนื้อหาบทสรุปการประชุมแบบ Markdown โดยในส่วนที่มีการเอ่ยถึงผู้พูด ให้ใช้ Placeholder เช่น {{{{ผู้พูด A}}}} หรือ {{{{ผู้พูด B}}}} เพื่อให้ผู้ใช้สามารถนำชื่อจริงมาแทนที่ได้"
}}

ข้อกำหนดสำหรับเนื้อหาใน summary_markdown_template:
- ต้องครอบคลุมหัวข้อ:
  1. # 📋 บันทึกการประชุม: {meeting_name}
  2. ## 🎯 สรุปภาพรวมสำหรับผู้บริหาร (Executive Summary)
  3. ## ⚖️ มติที่ประชุมและข้อตกลงร่วมกัน (Decisions & Key Agreements)
  4. ## ✅ รายการสิ่งที่ต้องทำ (Action Items) (จัดทำเป็นตาราง Markdown ระบุ ลำดับ, สิ่งที่ต้องทำ, ผู้รับผิดชอบ (ใช้ {{{{ผู้พูด X}}}}), กำหนดส่ง)
  5. ## 📝 ประเด็นสำคัญแยกตามวาระการพูดคุย (Key Discussion Points)
  6. ## ⚠️ ปัญหา อุปสรรค และความเสี่ยง (Blockers & Risks)
  7. ## 📅 การติดตามงานและนัดหมายครั้งถัดไป (Next Steps & Follow-up)
- ตอบกลับเฉพาะ JSON เท่านั้น ไม่ต้องมีข้อความเกริ่นนำ
"""


# ================= MAIN USER INTERFACE =================
st.markdown("""
<div style="text-align: center; margin-bottom: 1.5rem;">
    <h1 style="font-size: 1.85rem; color: #1C1C1E; font-weight: 700; margin-bottom: 0.2rem;">🎙️ สรุปบันทึกการประชุม AI</h1>
    <p style="color: #8E8E93; font-size: 0.95rem;">อัปโหลดเสียงการประชุม • ระบุชื่อผู้พูด • ดาวน์โหลด PDF แท้ในคลิกเดียว</p>
</div>
""", unsafe_allow_html=True)

# Step 1: Upload Card
with st.container():
    st.markdown('<div class="ios-card">', unsafe_allow_html=True)
    st.markdown("<h4 style='margin-top:0; color:#1C1C1E;'>1. เลือกไฟล์เสียงการประชุม</h4>", unsafe_allow_html=True)
    
    audio_file = st.file_uploader(
        "รองรับไฟล์เสียงบันทึกจาก iPhone และ Android (.mp3, .m4a, .wav, .aac, .ogg, .mp4):",
        type=["mp3", "m4a", "wav", "aac", "ogg", "flac", "mp4", "webm"],
        label_visibility="collapsed"
    )

    custom_title = st.text_input(
        "หัวข้อหรือชื่อการประชุม (ไม่บังคับ):",
        placeholder="เช่น ประชุมวางแผนงานระบบ Smart Farm ประจำสัปดาห์"
    )

    if audio_file is not None:
        file_size_mb = audio_file.size / (1024 * 1024)
        st.caption(f"📁 ชื่อไฟล์: **{audio_file.name}** | ขนาด: **{file_size_mb:.2f} MB**")

        # Audio player preview
        st.audio(audio_file)

        analyze_btn = st.button("🚀 เริ่มวิเคราะห์และสรุปการประชุม")

        if analyze_btn:
            tmp_path = None
            uploaded_remote_file = None
            progress_bar = st.progress(0, text="กำลังเตรียมไฟล์เสียง...")

            try:
                from google import genai
                from google.genai import types

                client = genai.Client(api_key=active_key)

                # Save temporary file
                suffix = Path(audio_file.name).suffix or ".mp3"
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_f:
                    tmp_f.write(audio_file.getvalue())
                    tmp_path = Path(tmp_f.name)

                # Upload to Gemini File API
                mime_type = get_mime_type(audio_file.name)
                progress_bar.progress(25, text="⬆️ กำลังส่งไฟล์เสียงไปยัง Gemini API...")

                with open(tmp_path, "rb") as f:
                    uploaded_remote_file = client.files.upload(
                        file=f,
                        config=types.UploadFileConfig(
                            mime_type=mime_type,
                            display_name=audio_file.name[:40]
                        )
                    )

                # Wait for active
                while uploaded_remote_file.state.name == "PROCESSING":
                    progress_bar.progress(45, text="⏳ ระบบกำลังถอดความและแยกแยะเสียงผู้พูด...")
                    time.sleep(3)
                    uploaded_remote_file = client.files.get(name=uploaded_remote_file.name)

                if uploaded_remote_file.state.name == "FAILED":
                    raise RuntimeError("การประมวลผลไฟล์เสียงของ Gemini API ล้มเหลว")

                # Build Structured Prompt
                meeting_title = custom_title.strip() if custom_title.strip() else audio_file.name.rsplit('.', 1)[0]
                prompt_content = AI_JSON_PROMPT.format(meeting_name=meeting_title)

                progress_bar.progress(65, text="🧠 AI กำลังสังเคราะห์บทสรุปและแยกแยะผู้พูด...")

                # Fallback models loop
                candidate_models = [model_name]
                for m in ["gemini-flash-latest", "gemini-3.7-flash", "gemini-3.5-flash"]:
                    if m not in candidate_models:
                        candidate_models.append(m)

                raw_ai_text = None
                max_retries = 3

                for attempt in range(1, max_retries + 1):
                    cur_model = candidate_models[(attempt - 1) % len(candidate_models)]
                    try:
                        resp = client.models.generate_content(
                            model=cur_model,
                            contents=[uploaded_remote_file, prompt_content],
                            config=types.GenerateContentConfig(
                                temperature=0.2,
                                response_mime_type="application/json"
                            )
                        )
                        raw_ai_text = resp.text
                        if raw_ai_text:
                            break
                    except Exception as ge:
                        err_str = str(ge)
                        if ("503" in err_str or "UNAVAILABLE" in err_str) and attempt < max_retries:
                            progress_bar.progress(75, text="⚠️ ระบบหนาแน่น กำลังสลับโมเดลสำรองอัตโนมัติ...")
                            time.sleep(6)
                        else:
                            raise ge

                if not raw_ai_text:
                    raise ValueError("ไม่ได้รับข้อมูลตอบกลับจากโมเดล")

                # Parse JSON
                parsed_data = parse_gemini_response(raw_ai_text)
                st.session_state["meeting_data"] = parsed_data
                st.session_state["meeting_title"] = meeting_title

                # Initialize speaker mappings in state
                speaker_list = parsed_data.get("speakers", [])
                for spk in speaker_list:
                    spk_id = spk.get("speaker_id", "")
                    sug_role = spk.get("suggested_role", "")
                    if f"spk_name_{spk_id}" not in st.session_state:
                        st.session_state[f"spk_name_{spk_id}"] = sug_role

                progress_bar.progress(100, text="✅ สรุปและแยกแยะผู้พูดสำเร็จแล้ว!")
                time.sleep(0.5)
                progress_bar.empty()

            except Exception as e:
                progress_bar.empty()
                st.error(f"❌ เกิดข้อผิดพลาดในการประมวลผล: {e}")

            finally:
                # Guaranteed cleanup
                if tmp_path is not None:
                    try:
                        tmp_path.unlink(missing_ok=True)
                    except Exception:
                        pass
                if uploaded_remote_file is not None:
                    try:
                        client.files.delete(name=uploaded_remote_file.name)
                    except Exception:
                        pass

    st.markdown('</div>', unsafe_allow_html=True)


# ================= STEP 2: SPEAKER MAPPING & DOWNLOADS =================
if "meeting_data" in st.session_state:
    meeting_data = st.session_state["meeting_data"]
    meeting_title = st.session_state.get("meeting_title", "บันทึกการประชุม")
    speakers = meeting_data.get("speakers", [])
    raw_template = meeting_data.get("summary_markdown_template", "")

    # Speaker Mapping Card
    if speakers:
        st.markdown('<div class="ios-card">', unsafe_allow_html=True)
        st.markdown("<h4 style='margin-top:0; color:#1C1C1E;'>👥 ระบุชื่อผู้พูด (Speaker Mapping)</h4>", unsafe_allow_html=True)
        st.caption("AI แยกแยะเสียงผู้พูดให้แล้ว สามารถพิมพ์ชื่อจริงเพื่อแทนที่ในบทสรุปและไฟล์เอกสารได้ทันที:")

        current_speaker_map = {}
        for idx, spk in enumerate(speakers):
            spk_id = spk.get("speaker_id", f"ผู้พูด {idx+1}")
            voice_traits = spk.get("voice_traits", "ไม่ระบุลักษณะเสียง")
            sample_quote = spk.get("sample_quote", "")
            suggested_role = spk.get("suggested_role", "")

            st.markdown(f"<span class='speaker-pill'>🗣️ {spk_id}</span> <span style='font-size:0.85rem; color:#8E8E93;'>({voice_traits})</span>", unsafe_allow_html=True)
            if sample_quote:
                st.markdown(f"<div class='quote-box'>💬 <em>\"{sample_quote}\"</em></div>", unsafe_allow_html=True)

            user_entered_name = st.text_input(
                f"ชื่อจริง / บทบาทของ {spk_id}:",
                value=st.session_state.get(f"spk_name_{spk_id}", suggested_role),
                key=f"spk_input_{idx}",
                placeholder=f"เช่น คุณสมชาย หรือ {suggested_role}"
            )
            current_speaker_map[spk_id] = user_entered_name
            st.session_state[f"spk_name_{spk_id}"] = user_entered_name
            st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)
    else:
        current_speaker_map = {}

    # Apply real-time mapping
    final_summary_md = apply_speaker_mapping(raw_template, current_speaker_map)

    # Step 3: Action Bar & Downloads
    st.markdown('<div class="ios-card">', unsafe_allow_html=True)
    st.markdown("<h4 style='margin-top:0; color:#1C1C1E;'>📥 ดาวน์โหลดเอกสารสรุปการประชุม</h4>", unsafe_allow_html=True)
    st.caption("ไฟล์ PDF แท้ จัดสระและวรรณยุกต์ภาษาไทยสมบูรณ์แบบ เปิดอ่านหรือส่งต่อใน LINE ได้ทันที:")

    safe_title = re.sub(r'[^\w\s-]', '', meeting_title).strip() or "meeting"

    col_pdf, col_docx, col_md = st.columns(3)

    # 1. Native PDF
    with col_pdf:
        if create_pdf_bytes is not None:
            try:
                pdf_bytes = create_pdf_bytes(final_summary_md, title=meeting_title)
                st.download_button(
                    label="📕 ดาวน์โหลด PDF แท้",
                    data=pdf_bytes,
                    file_name=f"{safe_title}_summary.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            except Exception as pe:
                st.error(f"เกิดข้อผิดพลาดในการสร้าง PDF: {pe}")
        else:
            st.warning("⚠️ โมดูล PDF อยู่ระหว่างการโหลด")

    # 2. Word .docx
    with col_docx:
        try:
            docx_bytes = create_docx_bytes(final_summary_md)
            st.download_button(
                label="📄 ดาวน์โหลด Word",
                data=docx_bytes,
                file_name=f"{safe_title}_summary.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True
            )
        except Exception as de:
            st.error(f"Word: {de}")

    # 3. Markdown .md
    with col_md:
        st.download_button(
            label="📝 ดาวน์โหลด Markdown",
            data=final_summary_md.encode("utf-8"),
            file_name=f"{safe_title}_summary.md",
            mime="text/markdown",
            use_container_width=True
        )

    st.markdown('</div>', unsafe_allow_html=True)

    # Step 4: Summary Content Preview
    st.markdown('<div class="ios-card">', unsafe_allow_html=True)
    st.markdown("<h4 style='margin-top:0; color:#1C1C1E;'>📋 ตัวอย่างเนื้อหาบทสรุปการประชุม</h4>", unsafe_allow_html=True)
    st.markdown(final_summary_md)
    st.markdown('</div>', unsafe_allow_html=True)

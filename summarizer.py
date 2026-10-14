import os
import sys
import time
import shutil
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Ensure console supports UTF-8 on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Supported audio and media extensions
SUPPORTED_EXTENSIONS = {
    ".mp3", ".m4a", ".wav", ".aac", ".ogg",
    ".flac", ".mp4", ".m4v", ".webm", ".wma"
}

SUMMARY_PROMPT = """คุณคือเลขานุการและผู้เชี่ยวชาญด้านการบันทึกการประชุมมืออาชีพ (Senior Executive Meeting Secretary)
โปรดฟังเสียงบันทึกการประชุมที่แนบมานี้อย่างละเอียด แล้วสรุปเนื้อหาเป็นภาษาไทยที่กระชับ ชัดเจน เป็นมืออาชีพ ไม่ตกหล่นใจความสำคัญ

กรุณาจัดโครงสร้างให้อยู่ในรูปแบบ Markdown ดังต่อไปนี้อย่างเคร่งครัด:

# 📋 บันทึกการประชุม: {meeting_name}

- **📅 วันที่บันทึกสรุป:** {date_str}
- **🎙️ ไฟล์เสียงต้นฉบับ:** {filename}
- **👥 ผู้เข้าร่วมประชุม / ผู้มีบทบาทหลัก:** (สรุปรายชื่อหรือบทบาทเท่าที่สามารถระบุได้จากการสนทนา หากไม่ทราบให้ระบุตามบริบท เช่น ทีมพัฒนา, ผู้จัดการฝ่าย ฯลฯ)

---

## 🎯 สรุปภาพรวมสำหรับผู้บริหาร (Executive Summary)
(สรุปใจความสำคัญและเป้าหมายหลักของการประชุมใน 3-5 บรรทัด ครอบคลุมว่าประชุมเรื่องอะไร ทำไม และผลลัพธ์หลักคืออะไร)

---

## ⚖️ มติที่ประชุมและข้อตกลงร่วมกัน (Decisions & Key Agreements)
(สรุปการตัดสินใจขั้นสุดท้าย นโยบาย หรือข้อตกลงที่สมาชิกในที่ประชุมเห็นชอบร่วมกัน เป็นข้อๆ)
- [มติ/ข้อตกลงที่ 1]
- [มติ/ข้อตกลงที่ 2]

---

## ✅ รายการสิ่งที่ต้องทำ (Action Items)
(จัดทำเป็นตาราง Markdown ให้ละเอียด ระบุสิ่งที่ต้องทำ ผู้รับผิดชอบ และกำหนดส่งให้ชัดเจน หากไม่ระบุเดดไลน์ชัดเจนให้ใส่ 'ตามที่ตกลง' หรือ 'รอติดตาม')

| ลำดับ | สิ่งที่ต้องทำ (Action Item) | ผู้รับผิดชอบ (Owner) | กำหนดส่ง (Deadline) | หมายเหตุ / เงื่อนไข |
| :---: | :--- | :--- | :--- | :--- |
| 1 | ... | ... | ... | ... |

---

## 📝 ประเด็นสำคัญแยกตามวาระการพูดคุย (Key Discussion Points)
(สรุปเนื้อหารายละเอียดของการพูดคุย โดยจัดกลุ่มแยกตามหัวข้อหรือวาระที่ถกกันอย่างเป็นระบบ)

### 1. [หัวข้อวาระที่ 1]
- **สาระสำคัญ:** ...
- **ความคิดเห็น/ข้อเสนอแนะ:** ...

### 2. [หัวข้อวาระที่ 2]
- **สาระสำคัญ:** ...
- **ความคิดเห็น/ข้อเสนอแนะ:** ...

---

## ⚠️ ปัญหา อุปสรรค และความเสี่ยง (Blockers & Risks)
(รวบรวมประเด็นที่เป็นปัญหา ความท้าทาย สิ่งที่กำลังติดขัด หรือความเสี่ยงที่ถูกหยิบยกขึ้นมาในที่ประชุม)
- ...

---

## 📅 การติดตามงานและนัดหมายครั้งถัดไป (Next Steps & Follow-up)
(การนัดหมายประชุมรอบถัดไป วันที่ เวลา หรือขั้นตอนการติดตามความคืบหน้า)
- ...
"""


def get_mime_type(file_path: Path) -> str:
    ext = file_path.suffix.lower()
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


def get_unique_path(destination_dir: Path, filename: str) -> Path:
    """Ensure unique file path by appending a counter if file exists."""
    target_path = destination_dir / filename
    if not target_path.exists():
        return target_path

    stem = target_path.stem
    suffix = target_path.suffix
    counter = 1
    while True:
        new_name = f"{stem}_{counter}{suffix}"
        new_path = destination_dir / new_name
        if not new_path.exists():
            return new_path
        counter += 1


def main():
    base_dir = Path(__file__).resolve().parent
    env_file = base_dir / ".env"

    if env_file.exists():
        load_dotenv(dotenv_path=env_file)
    else:
        load_dotenv()

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    model_name = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()

    print("=" * 65)
    print(" 🎙️  ระบบสรุปเสียงบันทึกการประชุมอัตโนมัติ (Meeting Summarizer) ")
    print("=" * 65)

    if not api_key or api_key == "YOUR_GEMINI_API_KEY_HERE":
        print("\n❌ ยังไม่ได้ตั้งค่า GEMINI_API_KEY ในไฟล์ .env")
        print("\nวิธีตั้งค่า:")
        print("1. ไปที่ https://aistudio.google.com/app/apikey เพื่อขอ API Key (ฟรี)")
        print("2. เปิดไฟล์ .env ในโฟลเดอร์นี้ แล้ววางคีย์ เช่น:")
        print("   GEMINI_API_KEY=AIzaSyD...")
        print("3. บันทึกไฟล์แล้วเปิดโปรแกรมใหม่อีกครั้ง\n")
        return

    # Directories
    audio_dir = base_dir / "audio"
    completed_dir = base_dir / "completed"
    summaries_dir = base_dir / "summaries"

    audio_dir.mkdir(exist_ok=True)
    completed_dir.mkdir(exist_ok=True)
    summaries_dir.mkdir(exist_ok=True)

    # Scan audio files
    audio_files = [
        f for f in audio_dir.iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    ]

    if not audio_files:
        print("\n📥 โฟลเดอร์ audio/ ยังไม่มีไฟล์เสียงสำหรับการสรุป")
        print(f"👉 กรุณานำไฟล์เสียง (.mp3, .m4a, .wav ฯลฯ) มาวางไว้ที่:\n   {audio_dir}")
        print("   แล้วรันโปรแกรมใหม่อีกครั้งครับ\n")
        return

    print(f"\n📂 พบไฟล์เสียงทั้งหมด {len(audio_files)} ไฟล์:")
    for idx, f in enumerate(audio_files, 1):
        size_mb = f.stat().st_size / (1024 * 1024)
        print(f"   {idx}. {f.name} ({size_mb:.2f} MB)")
    print("-" * 65)

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        print("\n❌ ไม่พบไลบรารี google-genai กรุณารันคำสั่งติดตั้งก่อน:")
        print("   uv pip install -r requirements.txt (หรือ python -m pip install -r requirements.txt)\n")
        return

    client = genai.Client(api_key=api_key)

    success_count = 0
    fail_count = 0

    for idx, audio_file in enumerate(audio_files, 1):
        print(f"\n▶️ [{idx}/{len(audio_files)}] กำลังประมวลผล: {audio_file.name}")
        file_size_mb = audio_file.stat().st_size / (1024 * 1024)
        print(f"   📊 ขนาดไฟล์: {file_size_mb:.2f} MB")

        uploaded_remote_file = None
        try:
            print("   ⬆️  กำลังอัปโหลดไฟล์เสียงไปยัง Gemini API...")
            mime_type = get_mime_type(audio_file)
            with open(audio_file, "rb") as f:
                uploaded_remote_file = client.files.upload(
                    file=f,
                    config=types.UploadFileConfig(
                        mime_type=mime_type,
                        display_name=audio_file.stem
                    )
                )
            print(f"   ✅ อัปโหลดสำเร็จ (Remote ID: {uploaded_remote_file.name})")

            # Check status until ACTIVE
            while uploaded_remote_file.state.name == "PROCESSING":
                print("   ⏳ กำลังประมวลผลไฟล์เสียงบนคลาวด์... รอ 5 วินาที")
                time.sleep(5)
                uploaded_remote_file = client.files.get(name=uploaded_remote_file.name)

            if uploaded_remote_file.state.name == "FAILED":
                raise RuntimeError("การประมวลผลไฟล์เสียงของ Gemini API ล้มเหลว")

            meeting_name = audio_file.stem.replace("_", " ").replace("-", " ")
            current_date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            prompt_content = SUMMARY_PROMPT.format(
                meeting_name=meeting_name,
                date_str=current_date_str,
                filename=audio_file.name
            )

            summary_text = None
            max_retries = 3
            candidate_models = [model_name]
            if "gemini-flash-latest" not in candidate_models:
                candidate_models.append("gemini-flash-latest")

            for attempt in range(1, max_retries + 1):
                cur_model = candidate_models[(attempt - 1) % len(candidate_models)]
                try:
                    print(f"   🧠 กำลังให้โมเดล {cur_model} วิเคราะห์และสรุปเนื้อหาการประชุม... (รอบที่ {attempt}/{max_retries})")
                    response = client.models.generate_content(
                        model=cur_model,
                        contents=[
                            uploaded_remote_file,
                            prompt_content
                        ],
                        config=types.GenerateContentConfig(
                            temperature=0.2,
                        )
                    )
                    summary_text = response.text
                    if summary_text:
                        break
                except Exception as gen_err:
                    err_str = str(gen_err)
                    if ("503" in err_str or "UNAVAILABLE" in err_str or "high demand" in err_str) and attempt < max_retries:
                        print(f"   ⚠️ เซิร์ฟเวอร์กำลังหนาแน่น (503) กำลังรอ 10 วินาทีเพื่อลองใหม่...")
                        time.sleep(10)
                    else:
                        raise gen_err

            if not summary_text:
                raise ValueError("ไม่ได้รับข้อความสรุปจากโมเดล")

            # Save summary file
            date_prefix = datetime.now().strftime("%Y-%m-%d")
            summary_filename = f"{date_prefix}_{audio_file.stem}_summary.md"
            target_summary_path = get_unique_path(summaries_dir, summary_filename)

            with open(target_summary_path, "w", encoding="utf-8") as out_f:
                out_f.write(summary_text)

            print(f"   💾 บันทึกสรุป Markdown เรียบร้อยที่: {target_summary_path.name}")

            # Auto export to Word (.docx) and PDF (.pdf)
            try:
                from convert_to_docs import markdown_to_docx, convert_docx_to_pdf
                docx_path = target_summary_path.with_suffix(".docx")
                markdown_to_docx(target_summary_path, docx_path)
                try:
                    convert_docx_to_pdf(docx_path)
                except Exception as pdf_err:
                    print(f"   ⚠️ ไม่สามารถแปลงเป็น PDF ได้: {pdf_err}")
            except Exception as docx_err:
                print(f"   ⚠️ ไม่สามารถสร้างไฟล์ Word ได้: {docx_err}")

            # Move original audio to completed folder
            target_completed_path = get_unique_path(completed_dir, audio_file.name)
            shutil.move(str(audio_file), str(target_completed_path))
            print(f"   📦 ย้ายไฟล์เสียงไปที่ completed/{target_completed_path.name}")

            success_count += 1

        except Exception as e:
            fail_count += 1
            err_msg = str(e)
            if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                print(f"   ⚠️ ติดโควต้าจำกัด (Rate Limit / Quota Exceeded):")
                print("      - หากติดลิมิตต่อนาที: กรุณารอสัก 1-2 นาทีแล้วรันใหม่")
                print("      - หากโควต้ารายวันหมด: ระบบจะรีเซ็ตทุกวันเวลาประมาณ 14:00-15:00 น. (เวลาไทย)")
                print("      - ตรวจสอบโควต้าได้ที่: https://aistudio.google.com/app/plan_information")
            else:
                print(f"   ❌ เกิดข้อผิดพลาดกับไฟล์ {audio_file.name}: {e}")

        finally:
            # Clean up uploaded file on Gemini server to keep cloud storage tidy
            if uploaded_remote_file is not None:
                try:
                    client.files.delete(name=uploaded_remote_file.name)
                except Exception:
                    pass

    print("\n" + "=" * 65)
    print(f"🎉 เสร็จสิ้นภารกิจ! สำเร็จ: {success_count} ไฟล์ | ล้มเหลว: {fail_count} ไฟล์")
    print(f"📂 ไฟล์สรุปทั้งหมดอยู่ในโฟลเดอร์: {summaries_dir}")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()

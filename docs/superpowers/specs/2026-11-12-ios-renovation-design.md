# แผนการรีโนเวทระบบสรุปบันทึกการประชุม AI (iOS UI + Speaker Mapping + Direct PDF)

**วันที่:** 2026-11-12
**ประเภทการออกแบบ:** Architectural Renovation

## 1. เป้าหมายหลัก (Objectives)
1. **หน้าเดียวจบ (Single-Page Focus):** ตัดแท็บประวัติย้อนหลังและส่วนที่ไม่จำเป็นออก เหลือเฉพาะขั้นตอนการอัปโหลด วิเคราะห์ ระบุชื่อผู้พูด และดาวน์โหลดสรุปการประชุม
2. **ดีไซน์สไตล์ iOS (Apple Human Interface Look):**
   - พื้นหลังโทนสว่าง `#F2F2F7` (iOS System Gray 6)
   - การ์ดสีขาว `#FFFFFF` ขอบมน `20px` เงาละมุน (`box-shadow: 0 4px 20px rgba(0,0,0,0.05)`)
   - ปุ่มกดสีฟ้า `#007AFF` (iOS System Blue) ขอบมนทรง Pill/Rounded
   - หน้าใส่รหัสผ่าน PIN (`304000`) ดีไซน์แบบ iOS Passcode Card
3. **ระบบระบุชื่อผู้พูด (Post-Summary Speaker Identification):**
   - ให้ Gemini วิเคราะห์เสียงและคืนค่าเป็น JSON ที่มี 2 ส่วน:
     - `speakers`: รายการผู้พูด (`id` เช่น `ผู้พูด A`, `voice_description`, `timestamp`, `sample_quote`)
     - `summary_markdown`: เนื้อหาสรุปการประชุมที่ใช้ป้ายกำกับ `[ผู้พูด A]`, `[ผู้พูด B]`
   - แสดงการ์ดให้ผู้ใช้กรอกชื่อจริงของแต่ละคน พร้อมเครื่องเล่นเสียงเพื่อฟังเทียบเวลาได้ทันที
   - แทนที่รหัสผู้พูดด้วยชื่อจริงแบบ Real-time ทันทีโดยไม่ต้องเรียก AI ซ้ำ
4. **ส่งออกเป็นไฟล์ `.pdf` แท้โดยตรง (Direct Native PDF Generation):**
   - ใช้ `fpdf2` + `uharfbuzz` พร้อมฝังฟอนต์ภาษาไทย (`Sarabun` / `TH Sarabun New`) ในโปรเจกต์ (`fonts/`) เพื่อให้แสดงสระและวรรณยุกต์ไทยได้อย่างถูกต้อง 100% ทั้งบน Windows และ Streamlit Community Cloud (Linux)
5. **แก้ไขจุดบกพร่องจากการตรวจสอบโค้ด (Audit Fixes):**
   - ใช้ `try...finally` เพื่อรับประกันการลบไฟล์ชั่วคราวทั้งในเครื่องและบน Gemini File API
   - ตรวจสอบสถานะ `FAILED` หลังอัปโหลดไฟล์เสียง
   - เพิ่มรายการโมเดลสำรอง (`gemini-3.8-flash`, `gemini-flash-latest`, `gemini-3.7-flash`, `gemini-3.5-flash`)

## 2. ขั้นตอนการดำเนินงาน (Implementation Plan)
1. ติดตั้งแพ็กเกจ `fpdf2` และ `uharfbuzz` ใน `.venv` และอัปเดต `requirements.txt`
2. เตรียมไฟล์ฟอนต์ภาษาไทย (`Sarabun-Regular.ttf`, `Sarabun-Bold.ttf`) ไว้ในโฟลเดอร์ `fonts/` ของโปรเจกต์เพื่อให้ใช้ได้บน Cloud
3. สร้างฟังก์ชัน `create_pdf_bytes(markdown_text, title)` สำหรับแปลง Markdown (หัวข้อ, รายการย่อย, ตาราง Action Items) เป็นไฟล์ `.pdf` แท้
4. เขียน `app.py` ใหม่ด้วยดีไซน์ iOS, ระบบ JSON Speaker Extraction + Real-time Name Mapping, และปุ่มดาวน์โหลด `.pdf` ทันที
5. ทดสอบการสร้างไฟล์ PDF ภาษาไทยและการทำงานของแอป จากนั้นอัปเดตขึ้น GitHub เพื่อให้ Streamlit Cloud อัปเดตอัตโนมัติ

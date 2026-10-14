# 📱 คู่มือการนำระบบสรุปการประชุมไปใช้บนมือถือ Android (โดยไม่ต้องเปิดคอมพิวเตอร์)

ระบบนี้ถูกออกแบบให้เป็น **Web App (PWA)** รองรับหน้าจอมือถือ Android เต็มรูปแบบ คุณสามารถนำไปฝากไว้บน Cloud ฟรี (เช่น **Streamlit Community Cloud** หรือ **Hugging Face Spaces**) เพื่อให้ใช้งานได้ตลอด 24 ชั่วโมง โดยไม่ต้องเปิดคอมพิวเตอร์ทิ้งไว้

---

## 🌟 วิธีที่ 1: ติดตั้งผ่าน Streamlit Community Cloud (แนะนำที่สุด - ฟรีตลอดชีพ)

### สิ่งที่ต้องมี:
- บัญชี [GitHub.com](https://github.com) (สมัครฟรี)
- บัญชี [Streamlit Community Cloud](https://share.streamlit.io) (ล็อกอินด้วยบัญชี GitHub เดียวกัน)

### ขั้นตอนการทำ (ประมาณ 3 นาที):

#### ขั้นตอนที่ 1: นำโค้ดขึ้น GitHub
1. เข้าไปที่ [github.com](https://github.com) แล้วกด **New repository**
2. ตั้งชื่อ เช่น `meeting-summarizer` (เลือกเป็น **Private** หรือ **Public** ก็ได้) แล้วกด **Create repository**
3. อัปโหลดไฟล์ต่อไปนี้ขึ้น GitHub:
   - `app.py`
   - `requirements.txt`
   - `.streamlit/config.toml`

#### ขั้นตอนที่ 2: กด Deploy บน Streamlit Cloud
1. เข้าไปที่ [share.streamlit.io](https://share.streamlit.io)
2. กดปุ่ม **Create app**
3. เลือก Repository ที่เพิ่งสร้าง (`meeting-summarizer`) และตั้ง **Main file path** เป็น `app.py`
4. กดที่หัวข้อ **Advanced settings** -> เมนู **Secrets** แล้วใส่ค่า API Key ของคุณ:
   ```toml
   GEMINI_API_KEY = "YOUR_GEMINI_API_KEY_HERE"
   GEMINI_MODEL = "gemini-3.8-flash"
   ```
5. กดปุ่ม **Deploy!**
6. รอประมาณ 1-2 นาที คุณจะได้ URL เว็บไซต์ส่วนตัว เช่น:  
   `https://meeting-summarizer-xxxx.streamlit.app`

---

## 📲 ขั้นตอนทำเป็นไอคอนแอปบนหน้าจอมือถือ Android (ไม่ต้องโหลด APK)

1. เปิดเบราว์เซอร์ **Google Chrome** บนมือถือ Android ของคุณ
2. เข้าไปที่ลิงก์ URL เว็บที่คุณเพิ่ง Deploy เสร็จ
3. กดปุ่มเมนู **จุด 3 จุด (⋮)** ที่มุมขวาบนของหน้าจอ Chrome
4. เลือกเมนู **"เพิ่มลงในหน้าจอหลัก" (Add to Home screen)** หรือ **"ติดตั้งแอป" (Install app)**
5. กด **"เพิ่ม" (Add)**

🎉 **เรียบร้อย!** บนหน้าจอมือถือจะมีไอคอน **"สรุปการประชุม AI"** ขึ้นมาเหมือนแอปทั่วไป  
คราวนี้ ไม่ว่าจะอยู่ที่ไหน หลังประชุมเสร็จ แค่หยิบมือถือขึ้นมากดเปิดไอคอนนี้ เลือกไฟล์เสียง แล้วกดสรุปได้ทันที โดยไม่ต้องเปิดคอมพิวเตอร์อีกต่อไปครับ!

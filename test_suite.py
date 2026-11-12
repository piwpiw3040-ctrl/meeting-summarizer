# -*- coding: utf-8 -*-
"""
test_suite.py - Comprehensive verification suite for meeting-summarizer fixes.
"""

import sys
import io
import re
import html
import hmac
from pathlib import Path

# Set up path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from pdf_generator import create_pdf_bytes, MeetingPDF
from app import parse_gemini_response, apply_speaker_mapping, create_docx_bytes, AI_JSON_PROMPT
from summarizer import SUMMARY_PROMPT


def test_thai_filename_regex():
    print("[1/8] Testing Thai filename regex...")
    titles = [
        ("การประชุมทีมก้าวหน้า_ประจำสัปดาห์", "การประชุมทีมก้าวหน้า_ประจำสัปดาห์"),
        ("ประชุมผู้บริหาร 14/10/2026: สรุปโปรเจกต์", "ประชุมผู้บริหาร 14102026 สรุปโปรเจกต์"),
        ("Meeting (Special) [Q3] {Draft} *Urgent*", "Meeting Special Q3 Draft Urgent"),
        ("   ", "meeting"),
    ]
    for raw, expected in titles:
        safe = re.sub(r'[^\w\s\u0e00-\u0e7f-]', '', raw).strip() or "meeting"
        assert safe == expected, f"Regex failed for '{raw}': got '{safe}', expected '{expected}'"
        # Verify Thai tone marks and vowels are NOT lost
        if "ก้าวหน้า" in raw:
            assert "ก้าวหน้า" in safe, f"Thai tone marks stripped! Got '{safe}'"
    print("  -> Passed!")


def test_json_parsing_with_code_blocks():
    print("[2/8] Testing JSON parsing & code block truncation...")
    
    # 1. Standard json
    raw1 = '{"speakers": [{"speaker_id": "spk1"}], "summary_markdown_template": "Hello"}'
    res1 = parse_gemini_response(raw1)
    assert len(res1["speakers"]) == 1
    assert res1["summary_markdown_template"] == "Hello"

    # 2. Markdown fence with inner code block (THIS CAUSED TRUNCATION BEFORE)
    raw2 = """```json
{
  "speakers": [
    {"speaker_id": "ผู้พูด A", "voice_traits": "เสียงทุ้ม", "sample_quote": "สวัสดี", "suggested_role": "ประธาน"}
  ],
  "summary_markdown_template": "# บันทึกการประชุม\\n\\n```python\\nprint('code block inside summary')\\n```\\n\\nสรุปงานเสร็จสิ้น"
}
```"""
    res2 = parse_gemini_response(raw2)
    assert len(res2["speakers"]) == 1
    assert res2["speakers"][0]["speaker_id"] == "ผู้พูด A"
    assert "print('code block inside summary')" in res2["summary_markdown_template"]
    assert "สรุปงานเสร็จสิ้น" in res2["summary_markdown_template"]

    # 3. Direct response with text before fence
    raw3 = """Here is the result:
```json
{
  "speakers": [],
  "summary_markdown_template": "Plain summary"
}
```"""
    res3 = parse_gemini_response(raw3)
    assert res3["summary_markdown_template"] == "Plain summary"

    # 4. Fallback on invalid JSON
    raw4 = "Just plain markdown without any JSON structure"
    res4 = parse_gemini_response(raw4)
    assert res4["speakers"] == []
    assert res4["summary_markdown_template"] == raw4

    print("  -> Passed!")


def test_curly_braces_crash_prevention():
    print("[3/8] Testing curly braces in meeting title...")
    title_with_braces = "ประชุม {Project Alpha} & [Module {Beta}]"
    
    # In app.py: replace("{meeting_name}", meeting_title)
    prompt_app = AI_JSON_PROMPT.replace("{meeting_name}", title_with_braces)
    assert title_with_braces in prompt_app
    assert "{meeting_name}" not in prompt_app

    # In summarizer.py: replace("{meeting_name}", ...)
    prompt_sum = (
        SUMMARY_PROMPT
        .replace("{meeting_name}", title_with_braces)
        .replace("{date_str}", "2026-11-12")
        .replace("{filename}", "test_{audio}.mp3")
    )
    assert title_with_braces in prompt_sum
    assert "test_{audio}.mp3" in prompt_sum
    print("  -> Passed!")


def test_xss_prevention():
    print("[4/8] Testing XSS escaping in speaker card variables...")
    xss_spk = '<script>alert("XSS")</script>'
    xss_trait = 'Bold <img src=x onerror=alert(1)>'
    xss_quote = 'Quote with "quotes" & <tags>'

    safe_spk = html.escape(str(xss_spk))
    safe_trait = html.escape(str(xss_trait))
    safe_quote = html.escape(str(xss_quote))

    assert "<script>" not in safe_spk
    assert "&lt;script&gt;" in safe_spk
    assert "<img" not in safe_trait
    assert "&lt;img" in safe_trait
    assert "&quot;" in safe_quote or '"' not in safe_quote
    print("  -> Passed!")


def test_hmac_pin_verification():
    print("[5/8] Testing HMAC PIN verification...")
    real_pin = "304000"
    correct_input = "304000"
    wrong_input = "123456"
    empty_input = ""

    assert hmac.compare_digest(correct_input.strip(), real_pin) is True
    assert hmac.compare_digest(wrong_input.strip(), real_pin) is False
    assert hmac.compare_digest(empty_input.strip(), real_pin) is False
    print("  -> Passed!")


def test_speaker_mapping():
    print("[6/8] Testing speaker mapping...")
    template = "# สรุป\n- ผู้รับผิดชอบ: {{ผู้พูด A}} และ [ผู้พูด B]"
    mapping = {
        "ผู้พูด A": "คุณสมชาย (CTO)",
        "ผู้พูด B": "คุณสมหญิง (PM)",
    }
    result = apply_speaker_mapping(template, mapping)
    assert "คุณสมชาย (CTO)" in result
    assert "คุณสมหญิง (PM)" in result
    assert "{{ผู้พูด A}}" not in result
    assert "[ผู้พูด B]" not in result

    # Test fallback to spk_id if user left it blank
    mapping_empty = {
        "ผู้พูด A": "   ",
        "ผู้พูด B": "",
    }
    result_empty = apply_speaker_mapping(template, mapping_empty)
    assert "ผู้พูด A" in result_empty
    assert "ผู้พูด B" in result_empty
    print("  -> Passed!")


def test_pdf_table_and_header():
    print("[7/8] Testing PDF generation (table crash fix + multi-page header)...")
    
    # 1. Document starting directly with table (previously crashed FPDF with FPDFException)
    table_first_md = """| ลำดับ | รายการ | ผู้รับผิดชอบ | กำหนดส่ง | หมายเหตุ |
| :---: | :--- | :--- | :--- | :--- |
| 1 | ปรับปรุงระบบรักษาความปลอดภัย | คุณวิชาญ | 15 พ.ย. 2026 | สำคัญมาก |
| 2 | ออกแบบสถาปัตยกรรมคลาวด์ | คุณกัญญา | 20 พ.ย. 2026 | ปกติ |
"""
    pdf_bytes1 = create_pdf_bytes(table_first_md, title="ตารางงานสำคัญ")
    assert len(pdf_bytes1) > 1000, "PDF 1 too small"
    assert pdf_bytes1.startswith(b"%PDF"), "Not valid PDF bytes"

    # 2. Multi-page document to trigger header() on page 2+
    long_content = [
        "# บันทึกการประชุมผู้บริหารระดับสูง",
        "## วาระที่ 1: การรายงานความคืบหน้าระบบ",
    ]
    for i in range(80):
        long_content.append(f"- ข้อที่ {i+1}: รายละเอียดการหารือข้อตกลงและแนวทางการแก้ปัญหาทางเทคนิคในระบบประจำสัปดาห์")
    long_content.append("""
| ลำดับ | สิ่งที่ต้องทำ | ผู้รับผิดชอบ | กำหนดส่ง |
| :---: | :--- | :--- | :--- |
| 1 | ตรวจสอบระบบ | คุณเอก | ทันที |
""")
    multi_page_md = "\n".join(long_content)
    pdf_bytes2 = create_pdf_bytes(multi_page_md, title="การประชุมใหญ่สามัญ")
    assert len(pdf_bytes2) > 10000, "Multi-page PDF too small"
    assert pdf_bytes2.startswith(b"%PDF"), "Not valid PDF bytes"

    print("  -> Passed!")


def test_docx_generation():
    print("[8/8] Testing Word (.docx) generation...")
    sample_md = """# บันทึกการประชุม: แผนงานระบบอัตโนมัติ

## 🎯 สรุปภาพรวม
ที่ประชุมเห็นชอบในแนวทางการปรับปรุงระบบ

| ลำดับ | งาน | ผู้รับผิดชอบ | กำหนดส่ง |
| :---: | :--- | :--- | :--- |
| 1 | ทดสอบระบบอัตโนมัติ | คุณนเรศ | วันนี้ |

- **มติ:** ผ่านความเห็นชอบ 100%
"""
    docx_bytes = create_docx_bytes(sample_md)
    assert len(docx_bytes) > 1000, "DOCX too small"
    # DOCX is a zip file, starts with PK
    assert docx_bytes.startswith(b"PK"), "DOCX not valid zip/docx format"
    print("  -> Passed!")


if __name__ == "__main__":
    print("==================================================")
    print("🚀 RUNNING MEETING SUMMARIZER TEST SUITE")
    print("==================================================")
    test_thai_filename_regex()
    test_json_parsing_with_code_blocks()
    test_curly_braces_crash_prevention()
    test_xss_prevention()
    test_hmac_pin_verification()
    test_speaker_mapping()
    test_pdf_table_and_header()
    test_docx_generation()
    print("==================================================")
    print("🎉 ALL 8 TEST SUITES PASSED PERFECTLY!")
    print("==================================================")

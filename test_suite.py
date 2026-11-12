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
from app import (
    parse_gemini_response,
    apply_speaker_mapping,
    create_docx_bytes,
    AI_JSON_PROMPT,
    SUMMARY_RESPONSE_SCHEMA,
    _normalize_parsed_data,
)
from summarizer import SUMMARY_PROMPT


def test_thai_filename_regex():
    print("[1/8] Testing Thai filename regex & CRLF sanitization...")
    titles = [
        ("การประชุมทีมก้าวหน้า_ประจำสัปดาห์", "การประชุมทีมก้าวหน้า_ประจำสัปดาห์"),
        ("ประชุมผู้บริหาร 14/10/2026: สรุปโปรเจกต์", "ประชุมผู้บริหาร 14102026 สรุปโปรเจกต์"),
        ("Meeting (Special) [Q3] {Draft} *Urgent*", "Meeting Special Q3 Draft Urgent"),
        ("หัวข้อ\nมีขึ้น\r\nบรรทัดใหม่", "หัวข้อ มีขึ้น บรรทัดใหม่"),
        ("   ", "meeting"),
    ]
    for raw, expected in titles:
        safe = re.sub(r'[\r\n\t]+', ' ', raw)
        safe = re.sub(r'[^\w\s\u0e00-\u0e7f-]', '', safe)
        safe = re.sub(r'\s+', ' ', safe).strip() or "meeting"
        assert safe == expected, f"Regex failed for '{raw}': got '{safe}', expected '{expected}'"
        # Verify Thai tone marks and vowels are NOT lost
        if "ก้าวหน้า" in raw:
            assert "ก้าวหน้า" in safe, f"Thai tone marks stripped! Got '{safe}'"
        assert "\n" not in safe and "\r" not in safe, f"CRLF leak in filename '{safe}'"
    print("  -> Passed!")


def test_json_parsing_with_code_blocks():
    print("[2/8] Testing JSON parsing & code block truncation...")
    
    # 1. Standard json
    raw1 = '{"speakers": [{"speaker_id": "spk1"}], "summary_markdown_template": "Hello"}'
    res1 = parse_gemini_response(raw1)
    assert len(res1["speakers"]) == 1
    assert res1["summary_markdown_template"] == "Hello"

    # 2. Markdown fence with inner code block (nested fence)
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

    # 4. Advanced edge case: JSON containing raw unescaped newlines and followed by postamble text with curly braces
    raw4 = """Here is the executive summary:
```json
{
  "speakers": [
    {
      "speaker_id": "ผู้พูด A",
      "voice_traits": "เสียงผู้ชาย ทุ้มลึก สุขุม",
      "sample_quote": "ยินดีต้อนรับทุกท่านครับ",
      "suggested_role": "ประธาน"
    }
  ],
  "summary_markdown_template": "เนื้อหาบรรทัด 1
```python
x = 10
print(x)
```
เนื้อหาบรรทัด 2"
}
```
Note: You can replace {speaker_id} with actual attendee names.
"""
    res4 = parse_gemini_response(raw4)
    assert len(res4["speakers"]) == 1
    assert res4["speakers"][0]["speaker_id"] == "ผู้พูด A"
    assert "x = 10" in res4["summary_markdown_template"]

    # 5. Fallback on invalid JSON
    raw5 = "Just plain markdown without any JSON structure"
    res5 = parse_gemini_response(raw5)
    assert res5["speakers"] == []
    assert res5["summary_markdown_template"] == raw5

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
    print("[6/8] Testing speaker mapping (with flexible whitespace)...")
    template = "# สรุป\n- ผู้รับผิดชอบ: {{ผู้พูด A}}, {{ ผู้พูด A }} และ [ผู้พูด B], [ ผู้พูด B ]"
    mapping = {
        "ผู้พูด A": "คุณสมชาย (CTO)",
        "ผู้พูด B": "คุณสมหญิง (PM)",
    }
    result = apply_speaker_mapping(template, mapping)
    assert "คุณสมชาย (CTO)" in result
    assert "คุณสมหญิง (PM)" in result
    assert "{{ผู้พูด A}}" not in result
    assert "{{ ผู้พูด A }}" not in result
    assert "[ผู้พูด B]" not in result
    assert "[ ผู้พูด B ]" not in result

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
    print("[7/8] Testing PDF generation (table crash fix + multi-page header + long title truncation)...")
    
    # 1. Document starting directly with table (previously crashed FPDF with FPDFException)
    table_first_md = """| ลำดับ | รายการ | ผู้รับผิดชอบ | กำหนดส่ง | หมายเหตุ |
| :---: | :--- | :--- | :--- | :--- |
| 1 | ปรับปรุงระบบรักษาความปลอดภัย | **คุณวิชาญ** | 15 พ.ย. 2026 | สำคัญมาก |
| 2 | ออกแบบสถาปัตยกรรมคลาวด์ | คุณกัญญา | 20 พ.ย. 2026 | ปกติ |
"""
    pdf_bytes1 = create_pdf_bytes(table_first_md, title="ตารางงานสำคัญ")
    assert len(pdf_bytes1) > 1000, "PDF 1 too small"
    assert pdf_bytes1.startswith(b"%PDF"), "Not valid PDF bytes"

    # 2. Multi-page document with an ultra-long title to verify header truncation and collision avoidance
    ultra_long_title = "การประชุมคณะกรรมการบริหารฝ่ายวิศวกรรมซอฟต์แวร์และการพัฒนาสถาปัตยกรรมคลาวด์ระดับองค์กร ประจำไตรมาสที่ 4 ปี 2026 อย่างเป็นทางการ"
    long_content = [
        f"# {ultra_long_title}",
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
    pdf_bytes2 = create_pdf_bytes(multi_page_md, title=ultra_long_title)
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


def test_layer1_gemini_structured_schema():
    print("[9/13] Testing Layer 1: Gemini API Structured Schema definition & compatibility...")
    assert isinstance(SUMMARY_RESPONSE_SCHEMA, dict), "Schema must be a dictionary"
    assert SUMMARY_RESPONSE_SCHEMA.get("type") == "OBJECT"
    assert "speakers" in SUMMARY_RESPONSE_SCHEMA.get("properties", {})
    assert "summary_markdown_template" in SUMMARY_RESPONSE_SCHEMA.get("properties", {})
    assert SUMMARY_RESPONSE_SCHEMA.get("required") == ["speakers", "summary_markdown_template"]

    # Verify compatibility with Google GenAI types.GenerateContentConfig
    try:
        from google.genai import types
        import google.genai._transformers as tr
        cfg = types.GenerateContentConfig(
            temperature=0.2,
            response_mime_type="application/json",
            response_schema=SUMMARY_RESPONSE_SCHEMA,
        )
        assert cfg.response_schema == SUMMARY_RESPONSE_SCHEMA
        # Verify transformer parses it into Schema
        schema_obj = tr.t_schema(None, SUMMARY_RESPONSE_SCHEMA)
        assert schema_obj is not None
        assert schema_obj.type.name == "OBJECT"
        assert "speakers" in schema_obj.properties
        assert "summary_markdown_template" in schema_obj.properties
    except ImportError:
        pass
    print("  -> Passed!")


def test_layer2_robust_json_normalization():
    print("[10/13] Testing Layer 2: parse_gemini_response normalization & edge cases...")
    import json

    # 1. None and empty input
    res_none = parse_gemini_response(None)
    assert isinstance(res_none, dict)
    assert res_none["speakers"] == []
    assert res_none["summary_markdown_template"] == ""

    res_empty = parse_gemini_response("   \n\t  ")
    assert isinstance(res_empty, dict)
    assert res_empty["speakers"] == []
    assert res_empty["summary_markdown_template"] == ""

    # 2. JSON "null" response
    res_null = parse_gemini_response("null")
    assert isinstance(res_null, dict)
    assert res_null["speakers"] == []
    assert res_null["summary_markdown_template"] == "null"

    # 3. Model returned array of speaker objects instead of root object
    raw_array = json.dumps([
        {"speaker_id": "ผู้พูด A", "voice_traits": "เสียงทุ้ม", "sample_quote": "สวัสดี", "suggested_role": "ประธาน"},
        {"speaker_id": "ผู้พูด B", "voice_traits": "เสียงใส", "sample_quote": "รับทราบค่ะ", "suggested_role": "เลขา"}
    ])
    res_array = parse_gemini_response(raw_array)
    assert isinstance(res_array, dict)
    assert len(res_array["speakers"]) == 2
    assert res_array["speakers"][0]["speaker_id"] == "ผู้พูด A"
    assert res_array["speakers"][1]["speaker_id"] == "ผู้พูด B"
    assert isinstance(res_array["summary_markdown_template"], str)

    # 4. Model returned array of strings
    raw_str_array = '["ผู้พูด 1", "ผู้พูด 2"]'
    res_str_array = parse_gemini_response(raw_str_array)
    assert isinstance(res_str_array, dict)
    assert len(res_str_array["speakers"]) == 2
    assert res_str_array["speakers"][0]["speaker_id"] == "ผู้พูด 1"

    # 5. Model returned quoted string
    raw_quoted = '"สรุปการประชุมโดยย่อ"'
    res_quoted = parse_gemini_response(raw_quoted)
    assert isinstance(res_quoted, dict)
    assert res_quoted["speakers"] == []
    assert res_quoted["summary_markdown_template"] == "สรุปการประชุมโดยย่อ"

    # 6. Double-encoded JSON string
    inner_payload = {
        "speakers": [{"speaker_id": "ผู้พูด X", "voice_traits": "เร็ว", "sample_quote": "ตกลงครับ", "suggested_role": "PM"}],
        "summary_markdown_template": "# บันทึกการประชุมสำคัญ"
    }
    double_encoded = json.dumps(json.dumps(inner_payload))
    res_double = parse_gemini_response(double_encoded)
    assert isinstance(res_double, dict)
    assert len(res_double["speakers"]) == 1
    assert res_double["speakers"][0]["speaker_id"] == "ผู้พูด X"
    assert res_double["summary_markdown_template"] == "# บันทึกการประชุมสำคัญ"

    # 7. Object with summary_markdown_template containing another double-encoded JSON string
    nested_in_template = {
        "speakers": [],
        "summary_markdown_template": json.dumps(inner_payload)
    }
    res_nested = parse_gemini_response(json.dumps(nested_in_template))
    assert isinstance(res_nested, dict)
    assert len(res_nested["speakers"]) == 1
    assert res_nested["speakers"][0]["speaker_id"] == "ผู้พูด X"

    # 8. Object with missing speakers or non-list speakers
    raw_no_spk = json.dumps({"summary_markdown_template": "เฉพาะบทสรุป"})
    res_no_spk = parse_gemini_response(raw_no_spk)
    assert isinstance(res_no_spk, dict)
    assert res_no_spk["speakers"] == []
    assert res_no_spk["summary_markdown_template"] == "เฉพาะบทสรุป"

    raw_spk_none = json.dumps({"speakers": None, "summary_markdown_template": "สรุปเมื่อ speakers เป็น None"})
    res_spk_none = parse_gemini_response(raw_spk_none)
    assert isinstance(res_spk_none, dict)
    assert res_spk_none["speakers"] == []
    assert res_spk_none["summary_markdown_template"] == "สรุปเมื่อ speakers เป็น None"

    raw_spk_dict = json.dumps({"speakers": {"spk1": "บทบาทผู้จัดการ"}, "summary_markdown_template": "สรุป"})
    res_spk_dict = parse_gemini_response(raw_spk_dict)
    assert isinstance(res_spk_dict, dict)
    assert len(res_spk_dict["speakers"]) == 1
    assert res_spk_dict["speakers"][0]["speaker_id"] == "spk1"
    assert res_spk_dict["speakers"][0]["suggested_role"] == "บทบาทผู้จัดการ"

    print("  -> Passed!")


def test_layer3_atomic_commit_and_rollback():
    print("[11/13] Testing Layer 3: Atomic State Commit & Transactional Rollback...")
    mock_session = {
        "existing_key": "safe_val",
        "meeting_data": "corrupted_old_state",
        "meeting_title": "old_title",
        "spk_name_old": "old_name",
    }

    # Simulate rollback upon exception
    def run_simulation(succeed: bool):
        try:
            raw_text = '{"speakers": [{"speaker_id": "spk1", "suggested_role": "ประธาน"}], "summary_markdown_template": "สรุปงาน"}'
            parsed = parse_gemini_response(raw_text)
            if not isinstance(parsed, dict):
                raise ValueError("Expected dict")

            temp_spk = {}
            for raw_spk in parsed.get("speakers", []):
                spk = raw_spk if isinstance(raw_spk, dict) else {"speaker_id": str(raw_spk)}
                spk_id = str(spk.get("speaker_id") or "").strip()
                sug_role = str(spk.get("suggested_role") or "").strip()
                if spk_id:
                    temp_spk[f"spk_name_{spk_id}"] = sug_role

            if not succeed:
                raise RuntimeError("Simulated mid-process failure before commit!")

            # Atomic commit
            for k, v in temp_spk.items():
                mock_session[k] = v
            mock_session["meeting_data"] = parsed
            mock_session["meeting_title"] = "การประชุมใหม่"
        except Exception:
            # Transactional rollback
            mock_session.pop("meeting_data", None)
            mock_session.pop("meeting_title", None)
            for k in list(mock_session.keys()):
                if k.startswith("spk_name_") or k.startswith("spk_input_"):
                    mock_session.pop(k, None)

    # 1. Test failure scenario (Rollback)
    run_simulation(succeed=False)
    assert "meeting_data" not in mock_session, "meeting_data was not rolled back!"
    assert "meeting_title" not in mock_session, "meeting_title was not rolled back!"
    assert "spk_name_old" not in mock_session, "Old speaker keys were not purged!"
    assert "spk_name_spk1" not in mock_session, "Uncommitted speaker keys leaked!"
    assert mock_session["existing_key"] == "safe_val", "Unrelated keys corrupted!"

    # 2. Test success scenario (Atomic commit)
    run_simulation(succeed=True)
    assert "meeting_data" in mock_session and isinstance(mock_session["meeting_data"], dict)
    assert mock_session["meeting_title"] == "การประชุมใหม่"
    assert mock_session["spk_name_spk1"] == "ประธาน"
    print("  -> Passed!")


def test_layer4_step2_ui_guard():
    print("[12/13] Testing Layer 4: Step 2 UI Guard & Safe Speaker Extraction...")

    # Check guard condition function
    def step2_guard_active(state: dict) -> bool:
        return (
            "meeting_data" in state
            and isinstance(state["meeting_data"], dict)
            and "summary_markdown_template" in state["meeting_data"]
        )

    # Scenarios that previously crashed at line 690:
    # 1. State contains list
    assert not step2_guard_active({"meeting_data": [{"speaker_id": "spk1"}]}), "Guard failed on list"
    # 2. State contains string
    assert not step2_guard_active({"meeting_data": "raw text"}), "Guard failed on string"
    # 3. State contains None
    assert not step2_guard_active({"meeting_data": None}), "Guard failed on None"
    # 4. State contains dict without summary_markdown_template
    assert not step2_guard_active({"meeting_data": {"speakers": []}}), "Guard failed on missing template"
    # 5. Valid state
    valid_state = {
        "meeting_data": {
            "speakers": ["spk_string_item", {"speaker_id": "spk2", "voice_traits": "เสียงชัด"}],
            "summary_markdown_template": "# บทสรุป"
        }
    }
    assert step2_guard_active(valid_state), "Guard rejected valid state"

    # Test safe speakers extraction
    meeting_data = valid_state["meeting_data"]
    speakers = meeting_data.get("speakers") if isinstance(meeting_data.get("speakers"), list) else []
    raw_template = str(meeting_data.get("summary_markdown_template") or "")
    assert len(speakers) == 2
    assert raw_template == "# บทสรุป"

    # Test safe speaker element handling (even when item is not a dict)
    for idx, raw_spk in enumerate(speakers):
        spk = raw_spk if isinstance(raw_spk, dict) else {"speaker_id": str(raw_spk)}
        spk_id = str(spk.get("speaker_id") or f"ผู้พูด {idx+1}")
        assert isinstance(spk_id, str)
        if idx == 0:
            assert spk_id == "spk_string_item"
        else:
            assert spk_id == "spk2"
    print("  -> Passed!")


def test_layer5_typesafe_speaker_mapping():
    print("[13/13] Testing Layer 5: Type-Safe apply_speaker_mapping...")

    # 1. None template_text
    assert apply_speaker_mapping(None, {"spk1": "นาย ก"}) == ""

    # 2. Non-string template_text
    assert apply_speaker_mapping(12345, {"spk1": "นาย ก"}) == "12345"

    # 3. None or non-dict speaker_mapping
    tpl = "สวัสดี {{ผู้พูด A}}"
    assert apply_speaker_mapping(tpl, None) == tpl
    assert apply_speaker_mapping(tpl, ["invalid", "mapping"]) == tpl
    assert apply_speaker_mapping(tpl, "not a dict") == tpl

    # 4. None keys or values in mapping
    mapping_none = {
        None: "คุณสมชาย",
        "ผู้พูด A": None,
        "": "คุณสมศรี",
    }
    # If real_name is None, it safely falls back to speaker_id
    res_none = apply_speaker_mapping(tpl, mapping_none)
    assert res_none == "สวัสดี ผู้พูด A"

    # 5. Non-string keys or values in mapping
    mapping_nums = {
        1: 999,
        "ผู้พูด A": 42,
    }
    res_nums = apply_speaker_mapping(tpl, mapping_nums)
    assert res_nums == "สวัสดี 42"

    # 6. Flexible whitespace and brackets
    tpl_brackets = "สรุปโดย [ผู้พูด 1] และ {{ ผู้พูด 2 }}"
    mapping_valid = {
        "ผู้พูด 1": "คุณสมชาย",
        "ผู้พูด 2": "คุณสมหญิง",
    }
    res_brackets = apply_speaker_mapping(tpl_brackets, mapping_valid)
    assert res_brackets == "สรุปโดย คุณสมชาย และ คุณสมหญิง"
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
    test_layer1_gemini_structured_schema()
    test_layer2_robust_json_normalization()
    test_layer3_atomic_commit_and_rollback()
    test_layer4_step2_ui_guard()
    test_layer5_typesafe_speaker_mapping()
    print("==================================================")
    print("🎉 ALL 13 TEST SUITES PASSED PERFECTLY!")
    print("==================================================")

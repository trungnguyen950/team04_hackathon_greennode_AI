import sys
import re
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent.resolve()
DEMO_DIR = BASE_DIR / "center subagents demo"
if str(DEMO_DIR) not in sys.path:
    sys.path.insert(0, str(DEMO_DIR))

from shared_langchain_components import call_llm
from agent_8_steps.state import Agent8StepState

def process(state: Agent8StepState) -> dict:
    """
    BƯỚC 3B: SOFTWARE CONTEXT
    Thu thập các thông tin cần thiết dựa trên yêu cầu từ cột Required_Context trong ServiceRequest:
    - Phòng ban công tác (Department).
    - Địa chỉ IP máy in (nếu là yêu cầu cài đặt máy in Ricoh / Brother).
    - Thông tin hệ điều hành / thiết bị của người dùng (Windows 10/11, macOS, v.v.).
    - Xác định những thông tin còn thiếu để bổ sung vào kịch bản phản hồi hoặc xin thông tin thêm.
    """
    user_req = state.get("user_request", {})
    sw_intent = state.get("software_intent", {})
    kb_item = sw_intent.get("kb_item", {})

    sender_email = user_req.get("sender_email", "")
    full_text = user_req.get("full_text", "")
    software_name = sw_intent.get("software_name", "")
    required_context_str = kb_item.get("required_context", "No")

    prompt = f"""
Bạn là Chuyên viên Kỹ thuật Hỗ trợ Ứng dụng IT (IT Application Support Specialist).
Nhiệm vụ: Trích xuất các thông tin ngữ cảnh kỹ thuật cần thiết cho việc cài đặt phần mềm từ nội dung người dùng gửi.

[THÔNG TIN PHẦN MỀM YÊU CẦU]:
- Tên phần mềm: {software_name}
- Yêu cầu ngữ cảnh bắt buộc theo quy định (Required Context): {required_context_str}

[NỘI DUNG EMAIL NGƯỜI DÙNG]:
"{full_text}"
Email người gửi: {sender_email}

Hãy phân tích và trích xuất theo đúng định dạng:
EXTRACTED_USER_ID: <UserID hoặc email của người dùng>
EXTRACTED_DEPARTMENT: <Phòng ban công tác nếu có nhắc tới, ví dụ: Kế toán, Nhân sự, IT, Kinh doanh..., hoặc 'Chưa rõ'>
EXTRACTED_PRINTER_IP: <Địa chỉ IP máy in nếu có dạng số IP ví dụ 192.168.x.x hoặc 10.x.x.x, hoặc 'Chưa rõ'>
EXTRACTED_DEVICE_ENV: <Hệ điều hành Windows 10/11 hay MacOS nếu có, hoặc 'Windows'>
MISSING_INFO: <Nếu Required Context yêu cầu thông tin nào mà người dùng chưa cung cấp (ví dụ thiếu IP máy in), hãy liệt kê rõ; nếu không yêu cầu hoặc đã đủ thì ghi 'Đầy đủ'>
CONTEXT_SUMMARY: <Tóm tắt ngắn gọn ngữ cảnh cài đặt>
"""
    raw_res = call_llm(prompt).strip()

    user_id = sender_email
    department = "Chưa rõ"
    printer_ip = "Chưa rõ"
    device_env = "Windows"
    missing_info = "Đầy đủ"
    context_summary = f"Yêu cầu cài đặt {software_name}"

    for line in raw_res.splitlines():
        line_clean = line.strip()
        if line_clean.upper().startswith("EXTRACTED_USER_ID:"):
            user_id = line_clean.split(":", 1)[1].strip() or sender_email
        elif line_clean.upper().startswith("EXTRACTED_DEPARTMENT:"):
            department = line_clean.split(":", 1)[1].strip()
        elif line_clean.upper().startswith("EXTRACTED_PRINTER_IP:"):
            printer_ip = line_clean.split(":", 1)[1].strip()
        elif line_clean.upper().startswith("EXTRACTED_DEVICE_ENV:"):
            device_env = line_clean.split(":", 1)[1].strip()
        elif line_clean.upper().startswith("MISSING_INFO:"):
            missing_info = line_clean.split(":", 1)[1].strip()
        elif line_clean.upper().startswith("CONTEXT_SUMMARY:"):
            context_summary = line_clean.split(":", 1)[1].strip()

    # Regex trích xuất nhanh IP máy in nếu prompt chưa bắt được
    if printer_ip == "Chưa rõ" and "printer" in software_name.lower():
        ip_match = re.search(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', full_text)
        if ip_match:
            printer_ip = ip_match.group(0)

    # Kế thừa thông tin đã cung cấp từ các email / lượt trao đổi trước đó (nếu có)
    accumulated_context = dict(user_req.get("accumulated_context") or {})
    if accumulated_context:
        if department in ["Chưa rõ", "No", "", "unknown"] and "Phòng ban" in accumulated_context:
            department = accumulated_context["Phòng ban"]
        if printer_ip in ["Chưa rõ", "No", "", "unknown"] and "IP máy in" in accumulated_context:
            printer_ip = accumulated_context["IP máy in"]

    # Thu thập và tích lũy các thông tin mà người dùng ĐÃ cung cấp (cả cũ và mới)
    provided_context = dict(accumulated_context)
    if department and department.strip().lower() not in ["chưa rõ", "no", "none", "", "n/a", "unknown"]:
        provided_context["Phòng ban"] = department
    if printer_ip and printer_ip.strip().lower() not in ["chưa rõ", "no", "none", "", "n/a", "unknown"]:
        provided_context["IP máy in"] = printer_ip

    # Đánh giá lại missing_info dựa trên toàn bộ thông tin đã tích lũy (từ trước đến nay)
    req_lower = required_context_str.lower()
    if req_lower not in ["no", "none", "không", "không có", ""]:
        missing_fields = []
        if any(kw in req_lower for kw in ["phòng ban", "phong ban", "department"]):
            if "Phòng ban" not in provided_context:
                missing_fields.append("Phòng ban")
        if any(kw in req_lower for kw in ["ip", "máy in", "may in", "printer"]):
            if "IP máy in" not in provided_context:
                missing_fields.append("Địa chỉ IP của máy in")
        if not missing_fields:
            missing_info = "Đầy đủ"
        else:
            missing_info = ", ".join(missing_fields)

    print("\n" + "=" * 70)
    print("🔹 [BƯỚC 3B: SOFTWARE CONTEXT] THU THẬP THÔNG TIN CẦN THIẾT")
    print("=" * 70)
    print(f" • Tiêu chuẩn yêu cầu (Required): {required_context_str}")
    print(f" • Mã người dùng / Email        : {user_id}")
    print(f" • Phòng ban                     : {department}")
    print(f" • IP Máy in (nếu có)            : {printer_ip}")
    print(f" • Môi trường máy tính           : {device_env}")
    print(f" • Thông tin còn thiếu           : {missing_info}")
    if provided_context:
        print(f" • Thông tin ngữ cảnh cung cấp  : {provided_context}")
    print(f" • Tóm lược ngữ cảnh             : {context_summary}")

    return {
        "software_context": {
            "required_fields_standard": required_context_str,
            "user_id": user_id,
            "department": department,
            "printer_ip": printer_ip,
            "device_env": device_env,
            "missing_info": missing_info,
            "provided_context": provided_context,
            "context_summary": context_summary,
        }
    }


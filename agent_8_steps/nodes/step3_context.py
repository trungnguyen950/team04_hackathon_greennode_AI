import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent.resolve()
DEMO_DIR = BASE_DIR / "center subagents demo"
if str(DEMO_DIR) not in sys.path:
    sys.path.insert(0, str(DEMO_DIR))

from shared_langchain_components import call_llm
from agent_8_steps.state import Agent8StepState
from agent_8_steps import kb_engine

def process(state: Agent8StepState) -> dict:
    """
    BƯỚC 3: CONTEXT
    Thu thập thông tin cần thiết dựa trên yêu cầu từ cột Required_Context trong Excel:
    - Trích xuất các thực thể đã có trong nội dung (UserID, Loại mạng, IP, Ứng dụng, Lỗi).
    - Nhận diện các thông tin còn thiếu để bổ sung vào kịch bản phản hồi.
    """
    user_req = state.get("user_request", {})
    intent_data = state.get("intent", {})
    
    sender_email = user_req.get("sender_email", "")
    is_issue_resolved = intent_data.get("is_issue_resolved", False)

    if is_issue_resolved:
        print("\n" + "=" * 70)
        print("🔹 [BƯỚC 3: CONTEXT] THU THẬP THÔNG TIN CẦN THIẾT")
        print("=" * 70)
        print(" • Vấn đề đã được người dùng xác nhận giải quyết thành công.")
        return {
            "context": {
                "required_fields_standard": "N/A",
                "user_id": sender_email,
                "device_env": "N/A",
                "status_error": "Đã giải quyết",
                "missing_info": "Đầy đủ",
                "context_summary": "Người dùng xác nhận vấn đề đã được giải quyết",
            }
        }

    full_text = user_req.get("full_text", "")
    intent_name = intent_data.get("intent_name", "")
    category = intent_data.get("category", "")

    # Tìm bản ghi KB sơ bộ để lấy danh sách Required_Context chuẩn
    matched_kb = kb_engine.find_best_match(full_text, intent_name=intent_name, category=category)
    required_context_str = matched_kb.get("required_context", "") if matched_kb else "UserID, Device, Issue Details"

    prompt = f"""
Bạn là Chuyên viên Phân tích Kỹ thuật IT Service Desk.
Nhiệm vụ: Trích xuất các thông tin ngữ cảnh kỹ thuật từ nội dung người dùng gửi.

Yêu cầu người dùng:
"{full_text}"
Email người gửi: {sender_email}

Các trường thông tin cần thu thập theo tiêu chuẩn hệ thống (Required Context):
{required_context_str}

Hãy phân tích và trả về định dạng:
EXTRACTED_USER_ID: <UserID hoặc tên người dùng trích xuất được hoặc email>
EXTRACTED_DEVICE_ENV: <Wifi hay LAN, hệ điều hành hoặc thiết bị nếu có, hoặc 'Chưa rõ'>
EXTRACTED_STATUS_ERROR: <Trạng thái lỗi, mã lỗi, hoặc triệu chứng chi tiết>
MISSING_INFO: <Danh sách các trường quan trọng còn thiếu trong Required Context mà người dùng chưa cung cấp, hoặc 'Đầy đủ'>
CONTEXT_SUMMARY: <Tóm tắt ngắn gọn ngữ cảnh kỹ thuật hiện tại>
"""
    raw_res = call_llm(prompt).strip()

    user_id = sender_email
    device_env = "Chưa rõ"
    status_error = "Lỗi kết nối / dịch vụ"
    missing_info = "Không có"
    context_summary = "Ngữ cảnh sự cố người dùng"

    for line in raw_res.splitlines():
        line_clean = line.strip()
        if line_clean.upper().startswith("EXTRACTED_USER_ID:"):
            user_id = line_clean.split(":", 1)[1].strip() or sender_email
        elif line_clean.upper().startswith("EXTRACTED_DEVICE_ENV:"):
            device_env = line_clean.split(":", 1)[1].strip()
        elif line_clean.upper().startswith("EXTRACTED_STATUS_ERROR:"):
            status_error = line_clean.split(":", 1)[1].strip()
        elif line_clean.upper().startswith("MISSING_INFO:"):
            missing_info = line_clean.split(":", 1)[1].strip()
        elif line_clean.upper().startswith("CONTEXT_SUMMARY:"):
            context_summary = line_clean.split(":", 1)[1].strip()

    # Kế thừa ngữ cảnh đã thu thập từ các lượt trước (nếu có)
    accumulated_context = dict(user_req.get("accumulated_context") or {})
    if device_env in ["Chưa rõ", "Unknown", ""] and ("Môi trường / Thiết bị" in accumulated_context or "device_env" in accumulated_context):
        device_env = accumulated_context.get("Môi trường / Thiết bị") or accumulated_context.get("device_env")
    if status_error in ["Lỗi kết nối / dịch vụ", "Chưa rõ", ""] and ("Trạng thái lỗi" in accumulated_context or "status_error" in accumulated_context):
        status_error = accumulated_context.get("Trạng thái lỗi") or accumulated_context.get("status_error")

    print("\n" + "=" * 70)
    print("🔹 [BƯỚC 3: CONTEXT] THU THẬP THÔNG TIN CẦN THIẾT")
    print("=" * 70)
    print(f" • Tiêu chuẩn yêu cầu (Required) : {required_context_str}")
    print(f" • Mã người dùng (UserID)        : {user_id}")
    print(f" • Môi trường / Thiết bị         : {device_env}")
    print(f" • Trạng thái / Mã lỗi           : {status_error}")
    print(f" • Thông tin còn thiếu           : {missing_info}")
    print(f" • Tóm lược ngữ cảnh             : {context_summary}")

    return {
        "context": {
            "required_fields_standard": required_context_str,
            "user_id": user_id,
            "device_env": device_env,
            "status_error": status_error,
            "missing_info": missing_info,
            "context_summary": context_summary,
        }
    }


import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent.resolve()
DEMO_DIR = BASE_DIR / "center subagents demo"
if str(DEMO_DIR) not in sys.path:
    sys.path.insert(0, str(DEMO_DIR))

from shared_langchain_components import call_llm
from agent_8_steps.state import Agent8StepState

def process(state: Agent8StepState) -> dict:
    """
    BƯỚC 5: DIAGNOSTIC
    Phân tích triệu chứng và suy luận nguyên nhân có khả năng dựa trên
    quy tắc Diagnostic_Condition (IF) và Root_Cause (THEN) từ cơ sở tri thức Excel.
    """
    user_req = state.get("user_request", {})
    context_data = state.get("context", {})
    kb_data = state.get("knowledge", {})
    intent_data = state.get("intent", {})

    if intent_data.get("is_issue_resolved"):
        print("\n" + "=" * 70)
        print("🔹 [BƯỚC 5: DIAGNOSTIC] PHÂN TÍCH TRIỆU CHỨNG & NGUYÊN NHÂN")
        print("=" * 70)
        print(" • Vấn đề đã được người dùng xác nhận giải quyết thành công.")
        return {
            "diagnostic": {
                "condition_check": "Khớp xác nhận hoàn tất",
                "root_cause": "Sự cố đã được xử lý thành công",
                "can_auto_resolve": True,
                "diagnostic_summary": "Sự cố đã được giải quyết thành công bởi người dùng.",
            }
        }

    full_text = user_req.get("full_text", "")
    kb_if = kb_data.get("diagnostic_condition", "")
    kb_then = kb_data.get("root_cause", "")
    kb_action = kb_data.get("resolution_action", "")

    prompt = f"""
Bạn là Chuyên gia Chẩn đoán Sự cố Hệ thống (IT Diagnostic Specialist).
Hãy phân tích tình trạng của người dùng dựa trên quy tắc chuyên môn từ Knowledge Base sau:

[THÔNG TIN SỰ CỐ TỪ NGƯỜI DÙNG]:
"{full_text}"
Ngữ cảnh thu thập: Môi trường: {context_data.get('device_env')} | Lỗi: {context_data.get('status_error')}

[QUY TẮC CHẨN ĐOÁN CHUẨN TỪ KNOWLEDGE BASE]:
- Điều kiện IF: {kb_if}
- Nguyên nhân THEN: {kb_then}
- Hướng xử lý dự kiến: {kb_action}

Hãy đưa ra kết luận chẩn đoán:
1. Đánh giá xem triệu chứng của người dùng có khớp với điều kiện IF hay không?
2. Xác định nguyên nhân gốc rễ cụ thể nhất cho trường hợp này.
3. Đánh giá: Có thể hướng dẫn người dùng tự khắc phục (AUTO_RESOLVE = YES) hay bắt buộc Kỹ sư IT phải can thiệp trực tiếp / cấp quyền admin (AUTO_RESOLVE = NO)?

Trả về định dạng 4 dòng:
CONDITION_CHECK: <Đạt hay Không đạt và giải thích ngắn gọn>
ROOT_CAUSE: <Nguyên nhân gốc rễ ngắn gọn và chuẩn xác>
AUTO_RESOLVE: <YES | NO>
DIAGNOSTIC_SUMMARY: <Tóm tắt chẩn đoán dễ hiểu cho người dùng>
"""
    raw_res = call_llm(prompt).strip()

    condition_check = "Khớp với điều kiện chẩn đoán trong KB"
    root_cause = kb_then or "Sự cố xác thực hệ thống"
    can_auto_resolve = True
    diagnostic_summary = f"Hệ thống xác định nguyên nhân: {root_cause}"

    for line in raw_res.splitlines():
        line_clean = line.strip()
        if line_clean.upper().startswith("CONDITION_CHECK:"):
            condition_check = line_clean.split(":", 1)[1].strip()
        elif line_clean.upper().startswith("ROOT_CAUSE:"):
            root_cause = line_clean.split(":", 1)[1].strip()
        elif line_clean.upper().startswith("AUTO_RESOLVE:"):
            val = line_clean.split(":", 1)[1].strip().upper()
            can_auto_resolve = (val == "YES")
        elif line_clean.upper().startswith("DIAGNOSTIC_SUMMARY:"):
            diagnostic_summary = line_clean.split(":", 1)[1].strip()

    print("\n" + "=" * 70)
    print("🔹 [BƯỚC 5: DIAGNOSTIC] PHÂN TÍCH TRIỆU CHỨNG & NGUYÊN NHÂN")
    print("=" * 70)
    print(f" • Kiểm tra điều kiện (IF)  : {condition_check}")
    print(f" • Nguyên nhân cốt lõi (THEN): {root_cause}")
    print(f" • Khả năng tự xử lý (Self) : {'Có thể tự khắc phục (Self-service)' if can_auto_resolve else 'Cần IT can thiệp trực tiếp (Escalation)'}")
    print(f" • Tóm lược chẩn đoán       : {diagnostic_summary}")

    return {
        "diagnostic": {
            "condition_check": condition_check,
            "root_cause": root_cause,
            "can_auto_resolve": can_auto_resolve,
            "diagnostic_summary": diagnostic_summary,
        }
    }


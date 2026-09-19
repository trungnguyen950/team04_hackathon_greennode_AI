import sys
import re
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
    BƯỚC 2: INTENT
    Xác định loại vấn đề (Category & Intent Name), mức độ ưu tiên (Priority),
    và kiểm tra xem người dùng có đang xác nhận VẤN ĐỀ ĐÃ ĐƯỢC GIẢI QUYẾT hay không.
    """
    user_req = state.get("user_request", {})
    full_text = user_req.get("full_text", "")
    clean_body = user_req.get("clean_body", "")
    existing_ticket_id = user_req.get("existing_ticket_id")
    is_reply = user_req.get("is_reply", False)
    
    # 1. Kiểm tra nhanh bằng từ khóa xác nhận giải quyết
    resolved_keywords = [
        "đã giải quyết", "đã vào được", "làm được rồi", "được rồi nhé",
        "được rồi cảm ơn", "kết nối thành công", "đã xử lý xong", "ok rồi",
        "ổn rồi", "hoạt động bình thường rồi", "fixed", "resolved", "works now"
    ]
    body_lower = clean_body.lower()
    quick_resolved = any(kw in body_lower for kw in resolved_keywords) and len(clean_body) < 300

    categories = kb_engine.get_all_categories()
    intents = kb_engine.get_all_intents()

    prompt = f"""
Bạn là Chuyên viên Phân loại Yêu cầu Dịch vụ IT (IT Service Desk Dispatcher).
Hãy phân tích email người dùng gửi đến:

Yêu cầu người dùng:
"{full_text}"

Thông tin bổ sung:
- Email này có phải là reply/tiếp nối ticket cũ không: {is_reply} (Mã ticket cũ: {existing_ticket_id or 'Không có'})

Nhiệm vụ:
1. Đánh giá xem người dùng có đang thông báo VẤN ĐỀ ĐÃ ĐƯỢC GIẢI QUYẾT / CẢM ƠN VÌ ĐÃ XONG (IS_RESOLVED: YES) hay người dùng vẫn đang gặp sự cố cần hỗ trợ (IS_RESOLVED: NO)?
2. Xác định Category & Intent Name theo danh mục:
Danh mục Category: {', '.join(categories)}
Danh mục Intent Name: {', '.join(intents)}
3. Xác định mức độ ưu tiên: CRITICAL | HIGH | MEDIUM | LOW

Hãy trả về chính xác định dạng 5 dòng:
IS_RESOLVED: <YES | NO>
CATEGORY: <Tên Category khớp nhất hoặc 'Issue Resolution' nếu đã giải quyết xong>
INTENT: <Tên Intent Name khớp nhất hoặc 'Issue Resolved Confirmation'>
PRIORITY: <CRITICAL | HIGH | MEDIUM | LOW>
SUMMARY: <Tóm tắt ngắn gọn 1 câu>
"""
    raw_res = call_llm(prompt).strip()

    is_issue_resolved = quick_resolved
    category = "Network / NAC"
    intent_name = "NAC Authentication Issue"
    priority = "MEDIUM"
    summary = "Sự cố kỹ thuật"

    for line in raw_res.splitlines():
        line_clean = line.strip()
        if line_clean.upper().startswith("IS_RESOLVED:"):
            val = line_clean.split(":", 1)[1].strip().upper()
            is_issue_resolved = (val == "YES") or quick_resolved
        elif line_clean.upper().startswith("CATEGORY:"):
            category = line_clean.split(":", 1)[1].strip()
        elif line_clean.upper().startswith("INTENT:"):
            intent_name = line_clean.split(":", 1)[1].strip()
        elif line_clean.upper().startswith("PRIORITY:"):
            p_val = line_clean.split(":", 1)[1].strip().upper()
            if p_val in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
                priority = p_val
        elif line_clean.upper().startswith("SUMMARY:"):
            summary = line_clean.split(":", 1)[1].strip()

    # Nếu đã giải quyết xong, ưu tiên đặt LOW
    if is_issue_resolved:
        priority = "LOW"
        category = "Issue Resolution"
        intent_name = "Issue Resolved Confirmation"

    print("\n" + "=" * 70)
    print("🔹 [BƯỚC 2: INTENT] XÁC ĐỊNH LOẠI VẤN ĐỀ & TRẠNG THÁI GIẢI QUYẾT")
    print("=" * 70)
    print(f" • Trạng thái giải quyết: {'✅ VẤN ĐỀ ĐÃ ĐƯỢC GIẢI QUYẾT (RESOLVED)' if is_issue_resolved else '🔄 VẪN CẦN HỖ TRỢ (IN PROGRESS)'}")
    print(f" • Nhóm (Category)      : {category}")
    print(f" • Ý định (Intent)      : {intent_name}")
    print(f" • Mức ưu tiên          : {priority}")
    print(f" • Tóm tắt vấn đề       : {summary}")

    return {
        "intent": {
            "is_issue_resolved": is_issue_resolved,
            "category": category,
            "intent_name": intent_name,
            "priority": priority,
            "summary": summary,
        }
    }

from agent_8_steps.state import Agent8StepState
from agent_8_steps import kb_engine
from agent_8_steps import ticket_system

def process(state: Agent8StepState) -> dict:
    """
    BƯỚC 4: KNOWLEDGE
    Tìm kiếm KB / SOP chuẩn từ tệp Excel và tra cứu Ticket tương tự trong quá khứ.
    """
    user_req = state.get("user_request", {})
    intent_data = state.get("intent", {})
    context_data = state.get("context", {})

    is_issue_resolved = intent_data.get("is_issue_resolved", False)
    if is_issue_resolved:
        print("\n" + "=" * 70)
        print("🔹 [BƯỚC 4: KNOWLEDGE] TÌM KIẾM KB / SOP & TICKET TƯƠNG TỰ")
        print("=" * 70)
        print(" • Vấn đề đã được người dùng xác nhận giải quyết thành công.")
        return {
            "knowledge": {
                "kb_item": {},
                "kb_id": "KB-RESOLVED",
                "diagnostic_condition": "Đã giải quyết",
                "root_cause": "Sự cố đã được xử lý thành công",
                "resolution_action": "Đóng phiếu hỗ trợ và lưu lịch sử tri thức",
                "assigned_team": "IT Service Desk",
                "sample_scenario": "Đóng phiếu khi nhận được xác nhận từ người dùng.",
                "similar_tickets": []
            }
        }

    full_text = user_req.get("full_text", "")
    intent_name = intent_data.get("intent_name", "")
    category = intent_data.get("category", "")

    # 1. Truy vấn Knowledge Base từ Excel (nạp qua excel_utils)
    matched_kb = kb_engine.find_best_match(
        query=f"{full_text} {context_data.get('status_error', '')}",
        intent_name=intent_name,
        category=category
    )

    if not matched_kb:
        matched_kb = {
            "kb_id": "KB-GEN-01",
            "category": category or "General Support",
            "intent_name": intent_name or "General Request",
            "user_utterances": full_text,
            "required_context": "UserID, Issue Details",
            "diagnostic_condition": "Người dùng gửi yêu cầu chung",
            "root_cause": "General Service Request",
            "resolution_action": "Cung cấp hướng dẫn giải quyết theo quy trình chuẩn",
            "assigned_team": "IT Service Desk",
            "sample_scenario": "Hỗ trợ người dùng xử lý sự cố."
        }

    # 2. Tìm kiếm các Ticket tương tự đã từng giải quyết trong quá khứ
    similar_tickets = ticket_system.find_similar_tickets(
        query=f"{intent_name} {user_req.get('clean_subject', '')}",
        category=category,
        top_n=2
    )

    print("\n" + "=" * 70)
    print("🔹 [BƯỚC 4: KNOWLEDGE] TÌM KIẾM KB / SOP & TICKET TƯƠNG TỰ")
    print("=" * 70)
    print(f" • Mã tri thức (KB_ID)     : {matched_kb.get('kb_id')}")
    print(f" • Quy trình / Phân loại   : {matched_kb.get('category')} -> {matched_kb.get('intent_name')}")
    print(f" • Điều kiện chuẩn (IF)    : {matched_kb.get('diagnostic_condition')}")
    print(f" • Nguyên nhân gốc (THEN)  : {matched_kb.get('root_cause')}")
    print(f" • Hướng xử lý chuẩn (SOP) : {matched_kb.get('resolution_action')}")
    print(f" • Đội ngũ phụ trách       : {matched_kb.get('assigned_team')}")
    if similar_tickets:
        print(f" • Tìm thấy {len(similar_tickets)} Ticket tương tự trong quá khứ:")
        for t in similar_tickets:
            print(f"   - [{t.get('ticket_id')}] {t.get('subject')} -> {t.get('status')}")
    else:
        print(" • Không có Ticket tương tự trong quá khứ (Đây là trường hợp mới).")

    return {
        "knowledge": {
            "kb_item": matched_kb,
            "kb_id": matched_kb.get("kb_id"),
            "diagnostic_condition": matched_kb.get("diagnostic_condition"),
            "root_cause": matched_kb.get("root_cause"),
            "resolution_action": matched_kb.get("resolution_action"),
            "assigned_team": matched_kb.get("assigned_team"),
            "sample_scenario": matched_kb.get("sample_scenario"),
            "similar_tickets": similar_tickets
        }
    }


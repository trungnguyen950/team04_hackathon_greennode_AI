from agent_8_steps.state import Agent8StepState
from agent_8_steps import ticket_system

def process(state: Agent8StepState) -> dict:
    """
    BƯỚC 7: TICKET
    Tạo hoặc Cập nhật Ticket trên hệ thống Service Desk:
    - Sinh mã Ticket chuẩn hóa (INC-YYYYMMDD-XXXX).
    - Gán cho Đội ngũ phụ trách chuyên trách (Assigned_Team từ Excel: Network Team, Messaging Team...).
    - Thiết lập mức độ ưu tiên (Priority) và Trạng thái xử lý (RESOLVED_BY_AI hoặc ESCALATED_TIER_2).
    - Ghi nhận vào cơ sở dữ liệu Ticket data/tickets_db.json.
    """
    user_req = state.get("user_request", {})
    intent_data = state.get("intent", {})
    kb_data = state.get("knowledge", {})
    diag_data = state.get("diagnostic", {})
    rec_data = state.get("recommendation", {})

    sender_email = user_req.get("sender_email", "")
    subject = user_req.get("clean_subject", "Sự cố IT")
    category = intent_data.get("category", "IT Support")
    intent_name = intent_data.get("intent_name", "General Issue")
    priority = intent_data.get("priority", "MEDIUM")
    assigned_team = kb_data.get("assigned_team", "IT Service Desk")
    root_cause = diag_data.get("root_cause", "")
    can_auto_resolve = diag_data.get("can_auto_resolve", True)
    is_issue_resolved = intent_data.get("is_issue_resolved", False)
    existing_ticket_id = user_req.get("existing_ticket_id")
    existing_svd_id = user_req.get("existing_svd_id")
    clean_body = user_req.get("clean_body", "")

    # Xác định trạng thái Ticket
    if is_issue_resolved:
        status = "CLOSED"
    elif can_auto_resolve:
        status = "RESOLVED_BY_AI"
    else:
        status = "ESCALATED_TIER_2"

    ai_guidance = rec_data.get("steps_guidance", "") or rec_data.get("action_title", "")
    context_data = state.get("context", {})
    provided_context = {
        "User ID": context_data.get("user_id"),
        "Môi trường / Thiết bị": context_data.get("device_env"),
        "Trạng thái lỗi": context_data.get("status_error"),
    }

    ticket_record = ticket_system.handle_ticket_lifecycle(
        requester_email=sender_email,
        subject=subject,
        category=category,
        intent_name=intent_name,
        assigned_team=assigned_team,
        priority=priority,
        diagnostic_cause=root_cause,
        status=status,
        resolution_notes=ai_guidance,
        is_issue_resolved=is_issue_resolved,
        existing_ticket_id=existing_ticket_id,
        existing_svd_id=existing_svd_id,
        user_message=clean_body,
        ai_guidance=ai_guidance,
        provided_context=provided_context
    )

    print("\n" + "=" * 70)
    print("🔹 [BƯỚC 7: TICKET] XỬ LÝ VÒNG ĐỜI TICKET HỖ TRỢ IT")
    print("=" * 70)
    print(f" • Hành động thực hiện   : {ticket_record.get('action_taken')}")
    print(f" • Mã Ticket (TicketID)  : {ticket_record.get('ticket_id') or 'N/A'}")
    print(f" • ServiceDesk ID        : #{ticket_record.get('svd_request_id') or 'N/A'}")
    print(f" • Đội ngũ phụ trách     : {ticket_record.get('assigned_team')}")
    print(f" • Mức ưu tiên           : {ticket_record.get('priority')}")
    print(f" • Trạng thái Ticket     : {ticket_record.get('status')}")
    if ticket_record.get('svd_url'):
        print(f" • Link ServiceDesk      : {ticket_record['svd_url']}")
    print(f" • Cơ sở dữ liệu Ticket  : data/tickets_db.json")

    return {"ticket": ticket_record}


from datetime import datetime
from agent_8_steps.state import Agent8StepState
from agent_8_steps import ticket_system

def process(state: Agent8StepState) -> dict:
    """
    BƯỚC 5B: SOFTWARE TICKET
    Tạo hoặc Cập nhật Ticket Yêu cầu Dịch vụ (Service Request Ticket) trên hệ thống:
    - Gán cho Đội ngũ IT phụ trách (IT Desktop Support / Application Admin).
    - Phân định trạng thái:
      * APPROVED_FOR_INSTALLATION: Đã đủ điều kiện và phê duyệt cài đặt.
      * WAITING_USER_INFO: Cần người dùng bổ sung thêm thông tin (như IP máy in).
      * PENDING_LICENSE_APPROVAL: Cần cấp phép bản quyền trước khi triển khai.
    - Đồng bộ lên ServiceDesk Plus và lưu vào cơ sở dữ liệu nội bộ data/tickets_db.json.
    """
    user_req = state.get("user_request", {})
    sw_intent = state.get("software_intent", {})
    sw_context = state.get("software_context", {})
    sw_prereq = state.get("software_prerequisites", {})

    sender_email = user_req.get("sender_email", "")
    subject = user_req.get("clean_subject", "Yêu cầu cài đặt phần mềm")
    software_name = sw_intent.get("software_name", "Phần mềm")
    category = sw_intent.get("category", "Install / Office Software")
    priority = sw_intent.get("priority", "LOW")
    existing_ticket_id = user_req.get("existing_ticket_id")
    existing_svd_id = user_req.get("existing_svd_id")
    clean_body = user_req.get("clean_body", "")

    is_in_catalog = sw_intent.get("is_in_catalog", True)
    is_eligible = sw_prereq.get("is_eligible", True)
    missing_info = sw_context.get("missing_info", "Đầy đủ")
    kb_item = sw_intent.get("kb_item", {})
    assigned_team = sw_intent.get("assigned_team") or kb_item.get("assigned_team") or "IT Support Team"

    # Phân loại trạng thái Service Request
    if not is_in_catalog:
        status = "PENDING_IT_EVALUATION"
    elif not is_eligible:
        status = "PENDING_LICENSE_APPROVAL"
    elif missing_info != "Đầy đủ":
        status = "WAITING_USER_INFO"
    else:
        status = "APPROVED_FOR_INSTALLATION"

    provided_context = dict(sw_context.get("provided_context") or {})
    department = sw_context.get("department", "")
    printer_ip = sw_context.get("printer_ip", "")
    if not provided_context:
        if department and department.strip().lower() not in ["chưa rõ", "no", "none", "", "n/a", "unknown"]:
            provided_context["Phòng ban"] = department
        if printer_ip and printer_ip.strip().lower() not in ["chưa rõ", "no", "none", "", "n/a", "unknown"]:
            provided_context["IP máy in"] = printer_ip

    ticket_record = ticket_system.handle_service_request_lifecycle(
        requester_email=sender_email,
        subject=subject,
        software_name=software_name,
        category=category,
        assigned_team=assigned_team,
        priority=priority,
        status=status,
        existing_ticket_id=existing_ticket_id,
        existing_svd_id=existing_svd_id,
        user_message=clean_body,
        provided_context=provided_context,
        is_in_catalog=is_in_catalog,
        is_issue_resolved=False
    )

    print("\n" + "=" * 70)
    print("🔹 [BƯỚC 5B: TICKET] TẠO / CẬP NHẬT SERVICE REQUEST TICKET")
    print("=" * 70)
    print(f" • Hành động thực hiện   : {ticket_record.get('action_taken')}")
    print(f" • Mã Ticket (TicketID)  : {ticket_record.get('ticket_id') or 'N/A'}")
    print(f" • ServiceDesk ID        : #{ticket_record.get('svd_request_id') or 'N/A'}")
    print(f" • Đội ngũ phụ trách     : {assigned_team}")
    print(f" • Mức ưu tiên           : {priority}")
    print(f" • Trạng thái Ticket     : {status}")
    if ticket_record.get("svd_url"):
        print(f" • Link ServiceDesk      : {ticket_record['svd_url']}")
    print(f" • Cơ sở dữ liệu Ticket  : data/tickets_db.json")

    return {"ticket": ticket_record}


import re
from datetime import datetime
from agent_8_steps.state import Agent8StepState
from agent_8_steps import ticket_system
from utils.string_utils import extract_reply_and_history, clean_gmail_ui_artifacts

def process(state: Agent8StepState) -> dict:
    """
    BƯỚC 1: USER REQUEST
    Tiếp nhận yêu cầu của người dùng bằng ngôn ngữ tự nhiên từ email.
    Làm sạch dữ liệu văn bản, trích xuất thông tin cơ bản.
    Tách cả phản hồi mới nhất (actual_body) và lịch sử email trao đổi trước đó (email_history)
    để đảm bảo không bị mất thông tin khi người dùng reply nhiều lần.
    """
    user_req = state.get("user_request", {})
    sender = user_req.get("sender", "")
    sender_email = user_req.get("sender_email", "")
    subject = user_req.get("subject", "").strip()
    body = user_req.get("body", "").strip()
    attachments = user_req.get("attachments", [])

    # Tách chính xác phản hồi mới của user VÀ giữ lại toàn bộ lịch sử trích dẫn phía dưới
    actual_body, email_history = extract_reply_and_history(body)

    # Làm sạch văn bản phản hồi mới
    clean_body = re.sub(r'\r\n', '\n', actual_body)
    clean_body = clean_gmail_ui_artifacts(clean_body)
    clean_body = re.sub(r'\n{3,}', '\n\n', clean_body).strip()

    print("\n" + "=" * 70)
    print("🔹 [BƯỚC 1: USER REQUEST] TIẾP NHẬN YÊU CẦU NGÔN NGỮ TỰ NHIÊN")
    print("=" * 70)
    print(f" • Người gửi   : {sender} <{sender_email}>")
    print(f" • Tiêu đề     : {subject}")
    print(f" • Nội dung gốc: {body[:100]}..." if len(body) > 100 else f" • Nội dung gốc: {body}")
    if clean_body != body:
        print(f" • Nội dung bóc tách (User Reply): {clean_body}")

    # 1. Phát hiện mã Ticket cũ trong tiêu đề hoặc nội dung email (ví dụ: [SVD-8], SVD #8, Ticket #88, Phiếu #88, [INC-20260913-8328])
    existing_ticket_id = None
    existing_svd_id = None

    # Tìm dạng SVD-xxx, SVD #xxx, Ticket #xxx, Phiếu #xxx trong tiêu đề
    svd_match = re.search(r'(?:SVD|Ticket|Phiếu)\s*[-#]?\s*(\d+)', subject, re.IGNORECASE)
    if not svd_match:
        # Thử tìm trong nội dung nếu tiêu đề không có
        svd_match = re.search(r'(?:SVD|Ticket|Phiếu)\s*[-#]?\s*(\d+)', clean_body, re.IGNORECASE)

    if svd_match:
        existing_svd_id = svd_match.group(1)
        existing_ticket_id = f"SVD-{existing_svd_id}"
    else:
        # Tìm dạng [INC-xxxx] hoặc INC-2026xxxx-xxxx trong tiêu đề hoặc nội dung
        inc_match = re.search(r'\[(INC-[\w-]+)\]', subject, re.IGNORECASE) or re.search(r'\b(INC-\d{8}-\d+)\b', subject, re.IGNORECASE)
        if not inc_match:
            inc_match = re.search(r'\b(INC-\d{8}-\d+)\b', clean_body, re.IGNORECASE)
        if inc_match:
            existing_ticket_id = inc_match.group(1)

    # 2. Kiểm tra cờ Reply
    is_reply = subject.strip().lower().startswith("re:") or bool(existing_ticket_id)

    # 3. Nếu là reply mà chưa có mã Ticket, thử tìm Ticket gần nhất của người dùng này trong database
    if is_reply and not existing_ticket_id:
        all_tickets = ticket_system.get_all_tickets()
        clean_subj_words = set(re.sub(r'^(re:\s*)+', '', subject.lower()).split())
        # Duyệt từ ticket mới nhất trở về trước
        for t in reversed(all_tickets):
            if t.get("requester_email", "").lower() == sender_email.lower():
                t_subj_words = set(t.get("subject", "").lower().split())
                if clean_subj_words.intersection(t_subj_words):
                    existing_ticket_id = t.get("ticket_id")
                    existing_svd_id = t.get("svd_request_id")
                    break
        # Nếu vẫn chưa thấy mà là reply của sender này, tìm ticket mở gần nhất chưa đóng
        if not existing_ticket_id:
            for t in reversed(all_tickets):
                if t.get("requester_email", "").lower() == sender_email.lower() and t.get("status") not in ["CLOSED", "RESOLVED_NO_TICKET_NEEDED"]:
                    existing_ticket_id = t.get("ticket_id")
                    existing_svd_id = t.get("svd_request_id")
                    break

    accumulated_context = {}
    db_history_messages = []
    if existing_ticket_id or existing_svd_id:
        all_tickets = ticket_system.get_all_tickets()
        for t in reversed(all_tickets):
            if (
                t.get("ticket_id") == existing_ticket_id
                or (existing_svd_id and str(t.get("svd_request_id")) == str(existing_svd_id))
                or (existing_ticket_id and t.get("svd_request_id") and str(t.get("svd_request_id")) in str(existing_ticket_id))
            ):
                if t.get("provided_context"):
                    accumulated_context = dict(t.get("provided_context"))
                if t.get("user_email_content"):
                    db_history_messages.append(f"Yêu cầu ban đầu: {t.get('user_email_content')}")
                if t.get("notes"):
                    for n in t.get("notes"):
                        c = (n.get("content") or "").strip()
                        if c and c != t.get("user_email_content"):
                            db_history_messages.append(f"Phản hồi cũ ({n.get('timestamp', '')}): {c}")
                break

    # Xây dựng full_text chứa cả phản hồi mới và toàn bộ lịch sử trao đổi trước đó
    history_blocks = []
    if db_history_messages:
        history_blocks.append("\n".join(db_history_messages))
    if email_history:
        history_blocks.append(email_history)

    if history_blocks:
        combined_history = "\n---\n".join(history_blocks)
        full_text = f"Tiêu đề: {subject}\n\n[NỘI DUNG PHẢN HỒI MỚI NHẤT CỦA NGƯỜI DÙNG]:\n{clean_body}\n\n[LỊCH SỬ TRAO ĐỔI VÀ THÔNG TIN ĐÃ CUNG CẤP TRƯỚC ĐÓ]:\n{combined_history}"
    else:
        full_text = f"Tiêu đề: {subject}\nNội dung: {clean_body}"

    if existing_ticket_id:
        print(f"📌 [PHÁT HIỆN TICKET CŨ]: {existing_ticket_id} (ServiceDesk ID: #{existing_svd_id or 'N/A'})")
        print("   -> Email này là phản hồi/tiếp nối chuỗi yêu cầu trước đó.")
        if accumulated_context:
            print(f"   -> Ngữ cảnh đã tích lũy từ trước: {accumulated_context}")
    elif is_reply:
        print("ℹ️ [EMAIL DẠNG REPLY]: Nhận diện thư phản hồi.")
    if email_history:
        print(f" • Đã bóc tách lịch sử email trích dẫn: {len(email_history)} ký tự.")

    updated_req = {
        **user_req,
        "clean_subject": subject,
        "clean_body": clean_body,
        "email_history": email_history,
        "accumulated_context": accumulated_context,
        "full_text": full_text,
        "is_reply": is_reply,
        "existing_ticket_id": existing_ticket_id,
        "existing_svd_id": existing_svd_id,
        "received_at": user_req.get("received_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    }

    return {"user_request": updated_req}

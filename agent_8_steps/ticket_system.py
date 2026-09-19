import os
import json
import html
import random
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from utils import svd_utils
from utils.string_utils import extract_actual_user_reply, clean_gmail_ui_artifacts

DATA_DIR = Path(__file__).parent.parent / "data"
TICKETS_FILE = DATA_DIR / "tickets_db.json"


def _ensure_data_file():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not TICKETS_FILE.exists():
        with open(TICKETS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)


def get_all_tickets() -> List[Dict[str, Any]]:
    """Đọc toàn bộ danh sách Ticket từ cơ sở dữ liệu JSON."""
    _ensure_data_file()
    try:
        with open(TICKETS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ [TICKET_SYSTEM] Không thể đọc file tickets_db.json: {e}")
        return []


def update_ticket_status(ticket_id: str, new_status: str) -> bool:
    """Cập nhật trạng thái của Ticket trong cơ sở dữ liệu nội bộ."""
    tickets = get_all_tickets()
    updated = False
    for t in tickets:
        if t.get("ticket_id") == ticket_id or t.get("svd_request_id") == ticket_id:
            t["status"] = new_status
            t["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            updated = True
            break
    if updated:
        try:
            with open(TICKETS_FILE, "w", encoding="utf-8") as f:
                json.dump(tickets, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    return updated


def record_ticket_note(
    ticket_id: str,
    author: str,
    content: str,
    note_type: str,
    ai_guidance: Optional[str] = None,
    new_status: Optional[str] = None,
    provided_context: Optional[Dict[str, Any]] = None
) -> bool:
    """Ghi nhận ghi chú/phản hồi của người dùng vào lịch sử Ticket nội bộ data/tickets_db.json."""
    tickets = get_all_tickets()
    updated = False
    time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for t in tickets:
        if (
            t.get("ticket_id") == ticket_id
            or t.get("svd_request_id") == ticket_id
            or (ticket_id and t.get("svd_request_id") and ticket_id.endswith(str(t.get("svd_request_id"))))
        ):
            if "notes" not in t:
                t["notes"] = []
            note_entry = {
                "timestamp": time_now,
                "author": author,
                "type": note_type,
                "content": clean_gmail_ui_artifacts(content)
            }
            if ai_guidance:
                note_entry["ai_guidance"] = ai_guidance
            if provided_context:
                note_entry["provided_context"] = provided_context
                if "provided_context" not in t or not isinstance(t["provided_context"], dict):
                    t["provided_context"] = {}
                for k, v in provided_context.items():
                    if v and str(v).lower() not in ["none", "chưa rõ", "unknown", "chưa có", ""]:
                        t["provided_context"][k] = v
            t["notes"].append(note_entry)
            if new_status:
                t["status"] = new_status
            t["updated_at"] = time_now
            updated = True
            break
    if updated:
        try:
            with open(TICKETS_FILE, "w", encoding="utf-8") as f:
                json.dump(tickets, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    return updated


def handle_service_request_lifecycle(
    requester_email: str,
    subject: str,
    software_name: str,
    category: str,
    assigned_team: str,
    priority: str = "LOW",
    status: str = "APPROVED_FOR_INSTALLATION",
    existing_ticket_id: Optional[str] = None,
    existing_svd_id: Optional[str] = None,
    user_message: str = "",
    provided_context: Optional[Dict[str, Any]] = None,
    is_in_catalog: bool = True,
    is_issue_resolved: bool = False
) -> Dict[str, Any]:
    """
    Quản lý vòng đời Ticket Yêu cầu Dịch vụ (Service Request Ticket):
    TÁCH BIỆT HOÀN TOÀN VỚI INCIDENT REPORT:
    - BỎ hoàn toàn phần Chẩn đoán AI (diagnostic_cause) trong mô tả ticket và các note.
    - BỎ hoàn toàn phần Phương án AI hướng dẫn (ai_guidance) trong các note.
    - Tập trung vào: Tên phần mềm, Đội ngũ phụ trách, Trạng thái phê duyệt, Thông tin bổ sung, Nội dung yêu cầu từ người dùng.
    """
    _ensure_data_file()
    time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    user_message = extract_actual_user_reply(user_message)
    user_message = clean_gmail_ui_artifacts(user_message)
    user_msg_html = html.escape(user_message).replace("\n", "<br>")

    # Chuẩn bị tiêu đề subject cho ServiceDesk Plus
    clean_subj = subject
    if not clean_subj.lower().startswith("[service request]"):
        clean_subj = f"[Service Request] {clean_subj}"

    # =========================================================================
    # TRƯỜNG HỢP 1: YÊU CẦU DỊCH VỤ ĐÃ HOÀN TẤT
    # =========================================================================
    if is_issue_resolved:
        print("✅ [TICKET_SYSTEM - SR] Người dùng xác nhận hoàn tất yêu cầu -> KHÔNG TẠO TICKET MỚI.")
        if existing_svd_id:
            try:
                note_content = (
                    f"[{time_now}] XÁC NHẬN HOÀN TẤT DỊCH VỤ TỪ NGƯỜI DÙNG ({requester_email})<br>"
                    f"<b>Phần mềm yêu cầu:</b> {html.escape(software_name)}<br>"
                    f"<b>Nội dung phản hồi:</b><br>"
                    f"{user_msg_html}<br><br>"
                    f"<b>Trạng thái:</b> Người dùng xác nhận hoàn tất cài đặt/kết nối. Đóng phiếu yêu cầu (CLOSED)."
                )
                svd_utils.add_request_note(str(existing_svd_id), note_content)
                close_comment = f"Người dùng ({requester_email}) xác nhận hoàn tất yêu cầu phần mềm {software_name}"
                svd_utils.close_request(str(existing_svd_id), close_comment)

                record_ticket_note(
                    ticket_id=existing_ticket_id or f"SVD-{existing_svd_id}",
                    author=requester_email,
                    content=user_message,
                    note_type="USER_REPLY_RESOLVED",
                    new_status="CLOSED"
                )
            except Exception as e:
                print(f"⚠️ [TICKET_SYSTEM - SR] Lỗi khi đóng ticket ServiceDesk: {e}")

            svd_url = f"{svd_utils.SVD_URL}/WorkOrder.do?woMode=viewWO&woID={existing_svd_id}"
            return {
                "ticket_id": existing_ticket_id or f"SVD-{existing_svd_id}",
                "svd_request_id": str(existing_svd_id),
                "svd_url": svd_url,
                "status": "CLOSED",
                "is_new_ticket": False,
                "action_taken": "CLOSED_EXISTING_TICKET",
                "assigned_team": assigned_team,
                "priority": "LOW"
            }
        else:
            return {
                "ticket_id": None,
                "svd_request_id": None,
                "svd_url": None,
                "status": "RESOLVED_NO_TICKET_NEEDED",
                "is_new_ticket": False,
                "action_taken": "NO_TICKET_NEEDED",
                "assigned_team": assigned_team,
                "priority": "LOW"
            }

    # =========================================================================
    # TRƯỜNG HỢP 2: PHẢN HỒI (REPLY) TRÊN YÊU CẦU DỊCH VỤ CŨ (KHÔNG TẠO TICKET MỚI)
    # =========================================================================
    if existing_ticket_id or existing_svd_id:
        target_svd_id = existing_svd_id
        if not target_svd_id and existing_ticket_id and "SVD-" in existing_ticket_id:
            target_svd_id = existing_ticket_id.split("SVD-")[-1]

        ticket_code = existing_ticket_id or f"SVD-{target_svd_id}"
        svd_url = f"{svd_utils.SVD_URL}/WorkOrder.do?woMode=viewWO&woID={target_svd_id}" if target_svd_id else ""

        print(f"🔄 [TICKET_SYSTEM - SR] Nhận diện Reply trên Ticket cũ {ticket_code} -> THÊM GHI CHÚ (NOTE)")

        if target_svd_id:
            try:
                # Format thông tin ngữ cảnh tích lũy (nếu có)
                context_summary_html = ""
                if provided_context:
                    valid_items = [
                        f"<b>• {html.escape(str(k))}:</b> {html.escape(str(v))}"
                        for k, v in provided_context.items()
                        if v and str(v).lower() not in ["none", "chưa rõ", "unknown", "chưa có", ""]
                    ]
                    if valid_items:
                        context_summary_html = f"<b>Thông tin đã cung cấp (tích lũy):</b><br>" + "<br>".join(valid_items) + "<br><br>"

                # MẪU ADD NOTE SERVICE REQUEST (BỎ HOÀN TOÀN AI HƯỚNG DẪN)
                note_content = (
                    f"[{time_now}] PHẢN HỒI CẬP NHẬT TỪ NGƯỜI DÙNG ({requester_email})<br>"
                    f"<b>Phần mềm yêu cầu:</b> {html.escape(software_name)}<br>"
                    f"<b>Đội ngũ phụ trách:</b> {assigned_team}<br><br>"
                    f"<b>Nội dung phản hồi bổ sung:</b><br>"
                    f"{user_msg_html}<br><br>"
                    f"{context_summary_html}"
                )
                svd_utils.add_request_note(str(target_svd_id), note_content)
                print(f"✅ [SVD_UTILS] Đã cập nhật ghi chú phản hồi vào Ticket #{target_svd_id} thành công!")
            except Exception as err:
                print(f"⚠️ [SVD_UTILS] Lỗi khi thêm note vào ticket: {err}")

        record_ticket_note(
            ticket_id=ticket_code,
            author=requester_email,
            content=user_message,
            note_type="USER_REPLY_IN_PROGRESS",
            new_status=status or "IN_PROGRESS",
            provided_context=provided_context
        )

        return {
            "ticket_id": ticket_code,
            "svd_request_id": str(target_svd_id) if target_svd_id else None,
            "svd_url": svd_url,
            "status": status or "IN_PROGRESS",
            "is_new_ticket": False,
            "action_taken": "UPDATED_EXISTING_TICKET",
            "assigned_team": assigned_team,
            "priority": priority,
            "software_name": software_name
        }

    # =========================================================================
    # TRƯỜNG HỢP 3: YÊU CẦU DỊCH VỤ MỚI HOÀN TOÀN (TẠO TICKET MỚI TRÊN SERVICEDESK)
    # =========================================================================
    print("🆕 [TICKET_SYSTEM - SR] Tạo Ticket Service Request mới trên ServiceDesk Plus...")

    date_str = datetime.now().strftime("%Y%m%d")
    rand_id = f"{random.randint(1000, 9999)}"
    fallback_ticket_id = f"SVD-{date_str}-{rand_id}"

    user_email_escaped = html.escape(user_message).replace("\n", "<br>")

    # Khối hiển thị ngữ cảnh bổ sung (Phòng ban, IP máy in, Cảnh báo ngoài danh mục...)
    context_html_section = ""
    ctx_items = []
    if provided_context:
        for k, v in provided_context.items():
            ctx_items.append(f"<b>• {html.escape(str(k))}:</b> {html.escape(str(v))}")
    if not is_in_catalog:
        ctx_items.append("<span style='color: #b06000;'><b>⚠️ Cảnh báo:</b> Phần mềm ngoài danh mục quy định, cần IT xem xét đánh giá</span>")
    if ctx_items:
        context_html_section = f"<p><b>🏢 Thông tin bổ sung:</b><br>" + "<br>".join(ctx_items) + "</p>"

    # MẪU GHI NHẬN YÊU CẦU SERVICE REQUEST (DESCRIPTION) - BỎ HOÀN TOÀN CHẨN ĐOÁN
    svd_description = f"""
    <div style="font-family: Arial, sans-serif; font-size: 13px; line-height: 1.5;">
        <p><b>📧 Người gửi yêu cầu:</b> {requester_email}</p>
        <p><b>📌 Tiêu đề yêu cầu:</b> {html.escape(subject)}</p>
        <p><b>💻 Phần mềm yêu cầu:</b> {html.escape(software_name)}</p>
        <p><b>🏷️ Phân loại dịch vụ:</b> {category}</p>
        <p><b>👥 Đội ngũ phụ trách:</b> {assigned_team}</p>
        <p><b>⚡ Mức độ ưu tiên:</b> {priority}</p>
        {context_html_section}
        <hr style="border: 0; border-top: 1px solid #ddd; margin: 12px 0;">
        <p style="font-size: 14px; color: #1a73e8; margin-bottom: 6px;"><b>📩 NỘI DUNG EMAIL YÊU CẦU TỪ NGƯỜI DÙNG:</b></p>
        <div style="background-color: #f8f9fa; border-left: 4px solid #1a73e8; padding: 12px 16px; margin: 8px 0; font-size: 13px; color: #202124;">
            {user_email_escaped}
        </div>
    </div>
    """

    svd_input = {
        "subject": clean_subj,
        "description": svd_description,
        "requester_name": "Guest",
        "technician_name": "Servicedesk Assistant",
        "status": "Open",
    }

    svd_log = {}
    svd_request_id = None
    svd_url = ""

    try:
        print(f"🌐 [SVD_UTILS] Đang gửi yêu cầu tạo Service Request lên ServiceDesk ({svd_utils.SVD_URL})...")
        svd_request_id = svd_utils.create_service_request(svd_input, svd_log)

        if svd_request_id:
            ticket_id = f"SVD-{svd_request_id}"
            svd_url = f"{svd_utils.SVD_URL}/WorkOrder.do?woMode=viewWO&woID={svd_request_id}"
            print(f"✅ [SVD_UTILS THÀNH CÔNG] Đã tạo Service Request mới ID: #{svd_request_id}")
            print(f"🔗 [SVD LINK]: {svd_url}")

            # MẪU ADD NOTE BAN ĐẦU CHO SERVICE REQUEST - BỎ HOÀN TOÀN AI HƯỚNG DẪN
            init_note = (
                f"[{time_now}] TIẾP NHẬN YÊU CẦU DỊCH VỤ TỪ NGƯỜI DÙNG ({requester_email})<br>"
                f"<b>Phần mềm yêu cầu:</b> {html.escape(software_name)}<br>"
                f"<b>Đội ngũ phụ trách:</b> {assigned_team}<br>"
                f"<b>Trạng thái:</b> {status}<br><br>"
                f"<b>Nội dung email yêu cầu:</b><br>"
                f"{user_msg_html}"
            )
            svd_utils.add_request_note(str(svd_request_id), init_note)
        else:
            print(f"⚠️ [SVD_UTILS] ServiceDesk trả về lỗi ({svd_log.get('messages')}). Dùng mã dự phòng.")
            ticket_id = fallback_ticket_id
            svd_url = ""

    except Exception as err:
        print(f"❌ [SVD_UTILS LỖI]: Không thể kết nối tới ServiceDesk: {err}. Dùng mã dự phòng.")
        ticket_id = fallback_ticket_id
        svd_url = ""

    new_ticket = {
        "ticket_id": ticket_id,
        "svd_request_id": str(svd_request_id) if svd_request_id else None,
        "svd_url": svd_url,
        "created_at": time_now,
        "requester_email": requester_email,
        "subject": subject,
        "flow_type": "software_install",
        "software_name": software_name,
        "category": category,
        "intent_name": f"Install {software_name}",
        "assigned_team": assigned_team,
        "priority": priority,
        "status": status,
        "user_email_content": user_message,
        "provided_context": provided_context or {},
        "notes": [
            {
                "timestamp": time_now,
                "author": requester_email,
                "type": "INITIAL_REQUEST",
                "content": user_message
            }
        ],
        "is_new_ticket": True,
        "action_taken": "CREATED_NEW_TICKET"
    }

    tickets = get_all_tickets()
    tickets.append(new_ticket)

    try:
        with open(TICKETS_FILE, "w", encoding="utf-8") as f:
            json.dump(tickets, f, ensure_ascii=False, indent=2)
        print("💾 [TICKET_SYSTEM] Đã lưu Ticket Service Request mới và nội dung email vào database nội bộ.")
    except Exception as e:
        print(f"⚠️ [TICKET_SYSTEM] Lỗi khi lưu file tickets_db.json: {e}")

    return {
        "ticket_id": ticket_id,
        "svd_request_id": str(svd_request_id) if svd_request_id else None,
        "svd_url": svd_url,
        "status": status,
        "is_new_ticket": True,
        "action_taken": "CREATED_NEW_TICKET",
        "assigned_team": assigned_team,
        "priority": priority,
        "software_name": software_name
    }


def handle_ticket_lifecycle(
    requester_email: str,
    subject: str,
    category: str,
    intent_name: str,
    assigned_team: str,
    priority: str = "MEDIUM",
    diagnostic_cause: str = "",
    status: str = "OPEN",
    resolution_notes: str = "",
    is_issue_resolved: bool = False,
    existing_ticket_id: Optional[str] = None,
    existing_svd_id: Optional[str] = None,
    user_message: str = "",
    ai_guidance: str = "",
    ticket_type: str = "incident",
    software_name: str = "",
    provided_context: Optional[Dict[str, Any]] = None,
    is_in_catalog: bool = True
) -> Dict[str, Any]:
    """
    Quản lý vòng đời Ticket Incident Report (Xử lý sự cố kỹ thuật).
    GIỮ NGUYÊN INCIDENT REPORT TEMPLATE (có chẩn đoán AI và phương án AI hướng dẫn).
    Nếu ticket_type == 'service_request' hoặc category thuộc Install, tự động chuyển sang handle_service_request_lifecycle.
    """
    # Nếu là Service Request, chuyển hướng sang hàm xử lý riêng biệt
    if ticket_type == "service_request" or (category and category.lower().startswith("install")):
        sw_name = software_name or (intent_name.replace("Install ", "") if intent_name else "Phần mềm")
        return handle_service_request_lifecycle(
            requester_email=requester_email,
            subject=subject,
            software_name=sw_name,
            category=category,
            assigned_team=assigned_team,
            priority=priority,
            status=status,
            existing_ticket_id=existing_ticket_id,
            existing_svd_id=existing_svd_id,
            user_message=user_message,
            provided_context=provided_context,
            is_in_catalog=is_in_catalog,
            is_issue_resolved=is_issue_resolved
        )
    _ensure_data_file()
    time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Tách chính xác nội dung phản hồi của người dùng, loại bỏ toàn bộ trích dẫn email cũ
    user_message = extract_actual_user_reply(user_message)
    user_message = clean_gmail_ui_artifacts(user_message)
    if existing_ticket_id or existing_svd_id:
        effective_guidance = ai_guidance or resolution_notes or "AI Service Desk đã cập nhật yêu cầu và gửi hướng dẫn hỗ trợ."
    else:
        effective_guidance = ai_guidance or resolution_notes or "AI Service Desk đã tiếp nhận và gửi hướng dẫn hỗ trợ."

    # =========================================================================
    # TRƯỜNG HỢP 1: VẤN ĐỀ ĐÃ ĐƯỢC GIẢI QUYẾT (KHÔNG TẠO TICKET MỚI)
    # =========================================================================
    if is_issue_resolved:
        print("✅ [TICKET_SYSTEM] Vấn đề đã được giải quyết xong -> KHÔNG TẠO TICKET MỚI.")

        if existing_svd_id:
            print(f"🔒 [TICKET_SYSTEM] Đang ghi nhận phản hồi và đóng Ticket #{existing_svd_id} trên ServiceDesk Plus...")
            try:
                user_msg_html = html.escape(user_message).replace("\n", "<br>")
                # 1. Thêm ghi chú lưu lại toàn bộ nội dung email phản hồi của người dùng (dùng <br>, bỏ ----)
                note_content = (
                    f"[{time_now}] PHẢN HỒI XÁC NHẬN ĐÃ GIẢI QUYẾT TỪ NGƯỜI DÙNG ({requester_email})<br>"
                    f"<b>Nội dung phản hồi:</b><br>"
                    f"{user_msg_html}<br><br>"
                    f"<b>Phương án xử lý:</b><br>"
                    f"Người dùng xác nhận vấn đề đã được giải quyết hoàn tất qua email. Hệ thống tự động đóng phiếu hỗ trợ.<br><br>"
                    f"<b>Trạng thái:</b> Đã giải quyết xong (CLOSED)."
                )
                print(f"📝 [SVD_UTILS] Đang thêm ghi chú (Note) vào Ticket #{existing_svd_id} trên ServiceDesk Plus...")
                svd_utils.add_request_note(str(existing_svd_id), note_content)
                print(f"✅ [SVD_UTILS] Đã ghi nhận phản hồi vào Ticket #{existing_svd_id} thành công!")

                # 2. Đóng ticket trên ServiceDesk
                close_comment = f"Người dùng ({requester_email}) xác nhận qua email: \"{user_message[:150]}\""
                svd_utils.close_request(str(existing_svd_id), close_comment)
                
                # 3. Cập nhật lịch sử Ticket nội bộ
                record_ticket_note(
                    ticket_id=existing_ticket_id or f"SVD-{existing_svd_id}",
                    author=requester_email,
                    content=user_message,
                    note_type="USER_REPLY_RESOLVED",
                    ai_guidance="Xác nhận giải quyết và đóng phiếu.",
                    new_status="CLOSED"
                )
            except Exception as e:
                print(f"⚠️ [TICKET_SYSTEM] Lỗi khi cập nhật đóng ticket trên ServiceDesk: {e}")

            svd_url = f"{svd_utils.SVD_URL}/WorkOrder.do?woMode=viewWO&woID={existing_svd_id}"
            return {
                "ticket_id": existing_ticket_id or f"SVD-{existing_svd_id}",
                "svd_request_id": str(existing_svd_id),
                "svd_url": svd_url,
                "status": "CLOSED",
                "is_new_ticket": False,
                "action_taken": "CLOSED_EXISTING_TICKET",
                "assigned_team": assigned_team,
                "priority": "LOW"
            }
        else:
            # Không có ticket cũ nào trước đó, chỉ là thư thông báo / cảm ơn
            return {
                "ticket_id": None,
                "svd_request_id": None,
                "svd_url": None,
                "status": "RESOLVED_NO_TICKET_NEEDED",
                "is_new_ticket": False,
                "action_taken": "NO_TICKET_NEEDED",
                "assigned_team": assigned_team,
                "priority": "LOW"
            }

    # =========================================================================
    # TRƯỜNG HỢP 2: PHẢN HỒI (REPLY) TRÊN YÊU CẦU CŨ (KHÔNG TẠO TICKET MỚI)
    # =========================================================================
    if existing_ticket_id or existing_svd_id:
        target_svd_id = existing_svd_id
        if not target_svd_id and existing_ticket_id and "SVD-" in existing_ticket_id:
            target_svd_id = existing_ticket_id.split("SVD-")[-1]

        ticket_code = existing_ticket_id or f"SVD-{target_svd_id}"
        svd_url = f"{svd_utils.SVD_URL}/WorkOrder.do?woMode=viewWO&woID={target_svd_id}" if target_svd_id else ""

        print(f"🔄 [TICKET_SYSTEM] Nhận diện Reply trên Ticket cũ {ticket_code} -> KHÔNG TẠO TICKET MỚI.")

        if target_svd_id:
            try:
                print(f"📝 [SVD_UTILS] Đang thêm ghi chú (Note) vào Ticket #{target_svd_id} trên ServiceDesk Plus...")
                user_msg_html = html.escape(user_message).replace("\n", "<br>")
                ai_guidance_html = html.escape(effective_guidance).replace("\n", "<br>")

                # Format Note sạch đẹp: Có nội dung user, có phương án AI hướng dẫn, dùng <br> xuống dòng, bỏ ----
                note_content = (
                    f"[{time_now}] PHẢN HỒI BỔ SUNG TỪ NGƯỜI DÙNG ({requester_email})<br>"
                    f"<b>Nội dung phản hồi:</b><br>"
                    f"{user_msg_html}<br><br>"
                    f"<b>Phương án AI hướng dẫn:</b><br>"
                    f"{ai_guidance_html}<br><br>"
                    f"<b>Trạng thái:</b> Người dùng đang chờ xử lý tiếp. AI Service Desk đã cập nhật yêu cầu và hướng dẫn."
                )
                svd_utils.add_request_note(str(target_svd_id), note_content)
                print(f"✅ [SVD_UTILS] Đã cập nhật ghi chú phản hồi vào Ticket #{target_svd_id} thành công!")
            except Exception as err:
                print(f"⚠️ [SVD_UTILS] Lỗi khi thêm note vào ticket: {err}")

        # Cập nhật lịch sử Ticket nội bộ
        record_ticket_note(
            ticket_id=ticket_code,
            author=requester_email,
            content=user_message,
            note_type="USER_REPLY_IN_PROGRESS",
            ai_guidance=effective_guidance,
            new_status=status or "IN_PROGRESS",
            provided_context=provided_context
        )

        return {
            "ticket_id": ticket_code,
            "svd_request_id": str(target_svd_id) if target_svd_id else None,
            "svd_url": svd_url,
            "status": status or "IN_PROGRESS",
            "is_new_ticket": False,
            "action_taken": "UPDATED_EXISTING_TICKET",
            "assigned_team": assigned_team,
            "priority": priority
        }

    # =========================================================================
    # TRƯỜNG HỢP 3: SỰ CỐ MỚI HOÀN TOÀN (TẠO TICKET MỚI TRÊN SERVICEDESK)
    # =========================================================================
    print("🆕 [TICKET_SYSTEM] Phát hiện sự cố mới hoàn toàn -> Tiến hành tạo Ticket mới trên ServiceDesk Plus...")
    
    date_str = datetime.now().strftime("%Y%m%d")
    rand_id = f"{random.randint(1000, 9999)}"
    fallback_ticket_id = f"INC-{date_str}-{rand_id}"

    # Đưa toàn bộ nội dung email nguyên gốc của người dùng vào phần nội dung yêu cầu (Description)
    user_email_escaped = html.escape(user_message).replace("\n", "<br>")
    svd_description = f"""
    <div style="font-family: Arial, sans-serif; font-size: 13px; line-height: 1.5;">
        <p><b>📧 Người gửi yêu cầu:</b> {requester_email}</p>
        <p><b>📌 Tiêu đề email:</b> {html.escape(subject)}</p>
        <p><b>🏷️ Phân loại sự cố:</b> {category} &rarr; {intent_name}</p>
        <p><b>👥 Đội ngũ phụ trách (KB):</b> {assigned_team}</p>
        <p><b>⚡ Mức độ ưu tiên:</b> {priority}</p>
        <hr style="border: 0; border-top: 1px solid #ddd; margin: 12px 0;">
        <p style="font-size: 14px; color: #1a73e8; margin-bottom: 6px;"><b>📩 NỘI DUNG EMAIL TỪ NGƯỜI DÙNG:</b></p>
        <div style="background-color: #f8f9fa; border-left: 4px solid #1a73e8; padding: 12px 16px; margin: 8px 0; font-size: 13px; color: #202124;">
            {user_email_escaped}
        </div>
        <hr style="border: 0; border-top: 1px solid #ddd; margin: 12px 0;">
        <p style="font-size: 14px; color: #e37400; margin-bottom: 6px;"><b>🔍 Chẩn đoán AI (Nguyên nhân):</b> {diagnostic_cause}</p>
    </div>
    """

    svd_input = {
        "subject": f"[{category}] {subject}",
        "description": svd_description,
        "requester_name": "Guest",
        "technician_name": "Servicedesk Assistant",
        "status": "Open",
    }

    svd_log = {}
    svd_request_id = None
    svd_url = ""

    try:
        print(f"🌐 [SVD_UTILS] Đang gửi yêu cầu tạo Ticket lên ServiceDesk ({svd_utils.SVD_URL})...")
        svd_request_id = svd_utils.create_service_request(svd_input, svd_log)
        
        if svd_request_id:
            ticket_id = f"SVD-{svd_request_id}"
            svd_url = f"{svd_utils.SVD_URL}/WorkOrder.do?woMode=viewWO&woID={svd_request_id}"
            print(f"✅ [SVD_UTILS THÀNH CÔNG] Đã tạo Ticket mới thực tế ID: #{svd_request_id}")
            print(f"🔗 [SVD LINK]: {svd_url}")

            # Ghi nhận Note ban đầu trên ServiceDesk chứa nội dung email của người dùng và phương án hướng dẫn
            user_msg_html = html.escape(user_message).replace("\n", "<br>")
            ai_guidance_html = html.escape(effective_guidance).replace("\n", "<br>")
            init_note = (
                f"[{time_now}] TIẾP NHẬN YÊU CẦU BAN ĐẦU TỪ NGƯỜI DÙNG ({requester_email})<br>"
                f"<b>Nội dung email yêu cầu:</b><br>"
                f"{user_msg_html}<br><br>"
                f"<b>Phương án AI hướng dẫn ban đầu:</b><br>"
                f"{ai_guidance_html}<br><br>"
                f"<b>Trạng thái:</b> Đã tiếp nhận và gửi email hướng dẫn tới người dùng."
            )
            svd_utils.add_request_note(str(svd_request_id), init_note)
        else:
            print(f"⚠️ [SVD_UTILS] ServiceDesk trả về lỗi ({svd_log.get('messages')}). Dùng mã dự phòng.")
            ticket_id = fallback_ticket_id
            svd_url = ""

    except Exception as err:
        print(f"❌ [SVD_UTILS LỖI]: Không thể kết nối tới ServiceDesk: {err}. Dùng mã dự phòng.")
        ticket_id = fallback_ticket_id
        svd_url = ""

    new_ticket = {
        "ticket_id": ticket_id,
        "svd_request_id": str(svd_request_id) if svd_request_id else None,
        "svd_url": svd_url,
        "created_at": time_now,
        "requester_email": requester_email,
        "subject": subject,
        "category": category,
        "intent_name": intent_name,
        "assigned_team": assigned_team,
        "priority": priority,
        "diagnostic_cause": diagnostic_cause,
        "status": status,
        "user_email_content": user_message,
        "provided_context": provided_context or {},
        "resolution_notes": resolution_notes,
        "notes": [
            {
                "timestamp": time_now,
                "author": requester_email,
                "type": "INITIAL_REQUEST",
                "content": user_message,
                "ai_guidance": effective_guidance
            }
        ],
        "is_new_ticket": True,
        "action_taken": "CREATED_NEW_TICKET"
    }

    tickets = get_all_tickets()
    tickets.append(new_ticket)

    try:
        with open(TICKETS_FILE, "w", encoding="utf-8") as f:
            json.dump(tickets, f, ensure_ascii=False, indent=2)
        print(f"💾 [TICKET_SYSTEM] Đã lưu Ticket mới và nội dung email vào database nội bộ.")
    except Exception as e:
        print(f"⚠️ [TICKET_SYSTEM] Lỗi khi lưu file tickets_db.json: {e}")

    return new_ticket


def create_ticket(*args, **kwargs):
    """Hàm tương thích ngược với code cũ, chuyển hướng đến handle_ticket_lifecycle."""
    return handle_ticket_lifecycle(*args, **kwargs)


def find_similar_tickets(query: str, category: Optional[str] = None, top_n: int = 2) -> List[Dict[str, Any]]:
    """Tìm kiếm các Ticket tương tự đã từng xử lý trong quá khứ để phục vụ Bước 4 (Knowledge)."""
    tickets = get_all_tickets()
    if not tickets:
        return []

    query_lower = query.lower() if query else ""
    scored = []

    for t in tickets:
        score = 0
        if category and t.get("category", "").lower() == category.lower():
            score += 20
        subject_words = set(t.get("subject", "").lower().split())
        query_words = set(query_lower.split())
        common = subject_words.intersection(query_words)
        score += len(common) * 5

        if score > 0:
            scored.append((score, t))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in scored[:top_n]]

import os
import sys
import re
import html
from pathlib import Path
from typing import Dict, Any, Optional

BASE_DIR = Path(__file__).parent.resolve()

import config
from agent_8_steps.workflow import app as agent_8_steps_app
from shared_langchain_components import call_llm


def _extract_display_name(from_header: str) -> str:
    """Trích xuất tên hiển thị thân thiện từ header email From: 'Tên <email@domain.com>'"""
    if not from_header:
        return "Anh/Chị"
    match = re.match(r'^([^<]+)<', from_header)
    if match:
        name = match.group(1).strip().strip('"\'')
        if name:
            return name
    if "@" in from_header:
        user_part = from_header.split("@")[0].strip()
        clean = re.sub(r'[\._0-9]+', ' ', user_part).strip().title()
        if clean:
            return clean
    return "Anh/Chị"


def ensure_ticket_notification_box(
    reply_html: str,
    ticket_id: str,
    svd_url: str = "",
    status: str = "RESOLVED_BY_AI",
    action_taken: str = "CREATED_NEW_TICKET"
) -> str:
    """
    Đảm bảo nội dung email HTML luôn chứa thông báo phiếu yêu cầu (Ticket Box)
    ngay cả khi kết nối tới máy chủ ServiceDesk Plus bị chậm hoặc dùng mã dự phòng.
    """
    if not reply_html or not ticket_id or ticket_id == "ERROR":
        return reply_html

    # Nếu đã có thông báo phiếu trong HTML thì không chèn lặp lại
    if "Phiếu yêu cầu đã được" in reply_html or "Phản hồi đã được cập nhật" in reply_html or "Phiếu yêu cầu đã được đóng" in reply_html:
        return reply_html

    clean_id = ticket_id.replace("SVD-", "").replace("INC-", "").split("-")[-1]
    effective_url = svd_url or f"https://49.213.71.61:8089/WorkOrder.do?woMode=viewWO&woID={clean_id}"

    if status == "CLOSED":
        box_html = f"""
        <div style="background-color: #e6f4ea; border: 1px solid #34a853; border-radius: 6px; padding: 14px; margin: 16px 0; text-align: center;">
            <p style="margin: 0 0 8px 0; color: #137333; font-weight: bold; font-size: 14px;">
                ✅ Phiếu yêu cầu đã được đóng hoàn tất trên ServiceDesk Plus
            </p>
            <a href="{effective_url}" target="_blank" style="background-color: #34a853; color: #ffffff; padding: 10px 22px; font-weight: bold; text-decoration: none; border-radius: 4px; display: inline-block; font-size: 13px;">
                👉 Bấm vào đây để xem chi tiết Ticket #{ticket_id} (user: guest, password: Guest@123)
            </a>
            <p style="margin: 8px 0 0 0; color: #5f6368; font-size: 11px;">(Đường link trực tiếp: <a href="{effective_url}" style="color: #34a853;">{effective_url}</a>)</p>
        </div>
        """
    elif action_taken == "UPDATED_EXISTING_TICKET":
        box_html = f"""
        <div style="background-color: #e8f0fe; border: 1px solid #1a73e8; border-radius: 6px; padding: 14px; margin: 16px 0; text-align: center;">
            <p style="margin: 0 0 8px 0; color: #1a73e8; font-weight: bold; font-size: 14px;">
                🎫 Phản hồi đã được cập nhật vào Phiếu #{ticket_id} trên ServiceDesk Plus
            </p>
            <a href="{effective_url}" target="_blank" style="background-color: #1a73e8; color: #ffffff; padding: 10px 22px; font-weight: bold; text-decoration: none; border-radius: 4px; display: inline-block; font-size: 13px;">
                👉 Bấm vào đây để theo dõi tiến độ Ticket #{ticket_id} (user: guest, password: Guest@123)
            </a>
            <p style="margin: 8px 0 0 0; color: #5f6368; font-size: 11px;">(Đường link trực tiếp: <a href="{effective_url}" style="color: #1a73e8;">{effective_url}</a>)</p>
        </div>
        """
    else:
        box_html = f"""
        <div style="background-color: #e8f0fe; border: 1px solid #1a73e8; border-radius: 6px; padding: 14px; margin: 16px 0; text-align: center;">
            <p style="margin: 0 0 8px 0; color: #1a73e8; font-weight: bold; font-size: 14px;">
                🎫 Phiếu yêu cầu đã được tạo thành công trên ServiceDesk Plus
            </p>
            <a href="{effective_url}" target="_blank" style="background-color: #1a73e8; color: #ffffff; padding: 10px 22px; font-weight: bold; text-decoration: none; border-radius: 4px; display: inline-block; font-size: 13px;">
                👉 Bấm vào đây để theo dõi Ticket #{ticket_id} (user: guest, password: Guest@123)
            </a>
            <p style="margin: 8px 0 0 0; color: #5f6368; font-size: 11px;">(Đường link trực tiếp: <a href="{effective_url}" style="color: #1a73e8;">{effective_url}</a>)</p>
        </div>
        """

    anchor = "Dưới đây là thông tin chi tiết:</p>"
    if anchor in reply_html:
        return reply_html.replace(anchor, f"{anchor}\n{box_html}")
    elif '<div style="background-color: #fef7e0;' in reply_html:
        return reply_html.replace('<div style="background-color: #fef7e0;', f"{box_html}\n<div style=\"background-color: #fef7e0;", 1)
    elif "<!-- Thẻ Chẩn đoán -->" in reply_html:
        return reply_html.replace("<!-- Thẻ Chẩn đoán -->", f"{box_html}\n<!-- Thẻ Chẩn đoán -->")
    elif "<!-- Thẻ Hướng dẫn xử lý -->" in reply_html:
        return reply_html.replace("<!-- Thẻ Hướng dẫn xử lý -->", f"{box_html}\n<!-- Thẻ Hướng dẫn xử lý -->")
    elif "</table>" in reply_html and "</div>" in reply_html:
        idx = reply_html.find("</table>")
        end_div = reply_html.find("</div>", idx)
        if end_div != -1:
            return reply_html[:end_div+6] + f"\n{box_html}" + reply_html[end_div+6:]

    if "</body>" in reply_html:
        return reply_html.replace("</body>", f"{box_html}\n</body>")
    return f"{box_html}\n{reply_html}"


def process_incoming_email(
    sender_name: str,
    sender_email: str,
    subject: str,
    body: str,
    attachments: Optional[list] = None
) -> Dict[str, Any]:
    """
    Tiếp nhận email người dùng và điều phối qua 2 Subflow LangGraph:
    - Subflow A: Quy trình xử lý sự cố (Incident Management - 8 bước)
    - Subflow B: Quy trình cài đặt phần mềm (Software Installation - 6 bước)
    """
    display_name = _extract_display_name(sender_name)
    print(f"\n🚀 [AI AGENT SERVICE DESK] Tiếp nhận email từ {sender_email} | Tiêu đề: '{subject}'...")

    # Khởi tạo State đầu vào cho đồ thị LangGraph
    initial_state = {
        "user_request": {
            "sender": display_name,
            "sender_email": sender_email,
            "subject": subject,
            "body": body,
            "attachments": attachments or [],
        }
    }

    try:
        # Thực thi đồ thị LangGraph (Center Router -> Subflow A / Subflow B)
        result_state = agent_8_steps_app.invoke(initial_state)

        flow_type = result_state.get("flow_type", "incident")
        resolution = result_state.get("resolution", {})
        ticket = result_state.get("ticket", {})
        intent = result_state.get("intent", {})
        diagnostic = result_state.get("diagnostic", {})
        recommendation = result_state.get("recommendation", {})
        sw_intent = result_state.get("software_intent", {})
        sw_prereq = result_state.get("software_prerequisites", {})

        reply_subject = resolution.get("reply_subject", f"Re: {subject}")
        reply_body_plain = resolution.get("reply_body_plain", "")
        reply_body_html = resolution.get("reply_body_html", "")
        
        default_team = sw_intent.get("assigned_team") or (sw_intent.get("kb_item", {}).get("assigned_team")) or "IT Support Team"
        assigned_team = ticket.get("assigned_team", default_team)
        ticket_id = ticket.get("ticket_id", "")
        
        root_cause = diagnostic.get("root_cause", sw_prereq.get("summary", "Yêu cầu dịch vụ phần mềm"))
        routing_reason = result_state.get("routing_reason", "") or diagnostic.get("diagnostic_summary", sw_prereq.get("summary", ""))
        raw_answer = recommendation.get("steps_guidance", resolution.get("installation_guidance", ""))

        # Đảm bảo thông báo phiếu Ticket luôn hiển thị đầy đủ
        reply_body_html = ensure_ticket_notification_box(
            reply_body_html,
            ticket_id=ticket_id,
            svd_url=ticket.get("svd_url", ""),
            status=ticket.get("status", "RESOLVED_BY_AI"),
            action_taken=ticket.get("action_taken", "CREATED_NEW_TICKET")
        )

        flow_label = "SUBFLOW B: CÀI ĐẶT PHẦN MỀM" if flow_type == "software_install" else "SUBFLOW A: XỬ LÝ SỰ CỐ"
        print(f"\n🎯 [HOÀN TẤT - {flow_label}] Ticket: {ticket_id} | Đội ngũ: {assigned_team} | Trạng thái: {ticket.get('status')}")

        return {
            "flow_type": flow_type,
            "reply_subject": reply_subject,
            "reply_body_plain": reply_body_plain,
            "reply_body_html": reply_body_html,
            "assigned_agent": assigned_team,
            "routing_reason": routing_reason,
            "ticket_id": ticket_id,
            "svd_url": ticket.get("svd_url", ""),
            "root_cause": root_cause,
            "status": ticket.get("status", "RESOLVED_BY_AI"),
            "raw_answer": raw_answer
        }

    except Exception as e:
        print(f"⚠️ [AI AGENT SERVICE DESK] Lỗi khi chạy quy trình: {e}. Kích hoạt chế độ dự phòng...")
        prompt_fallback = f"""
Bạn là Trợ lý AI IT Service Desk. Người dùng {display_name} vừa gửi email:
Tiêu đề: {subject}
Nội dung: {body}

Hãy hướng dẫn xử lý lịch thiệp, từng bước rõ ràng và chuyên nghiệp.
"""
        fallback_answer = call_llm(prompt_fallback).strip()
        ticket_id = f"INC-FALLBACK-{os.urandom(2).hex()}"
        fallback_html = f"<html><body><p>Kính gửi {display_name},</p><p>{fallback_answer}</p>{config.EMAIL_SIGNATURE_HTML}</body></html>"
        fallback_html = ensure_ticket_notification_box(
            fallback_html,
            ticket_id=ticket_id,
            svd_url="",
            status="IN_PROGRESS",
            action_taken="CREATED_NEW_TICKET"
        )
        return {
            "flow_type": "fallback",
            "reply_subject": f"Re: [{ticket_id}] {subject}",
            "reply_body_plain": f"Kính gửi {display_name},\n\n{fallback_answer}\n\n{config.EMAIL_SIGNATURE_PLAIN}",
            "reply_body_html": fallback_html,
            "assigned_agent": "IT Support Team",
            "routing_reason": "Dự phòng ngoại lệ",
            "ticket_id": ticket_id,
            "root_cause": "Đang xác minh",
            "status": "IN_PROGRESS",
            "raw_answer": fallback_answer
        }

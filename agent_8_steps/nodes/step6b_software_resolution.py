import os
import sys
import json
import html
import re
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent.resolve()
DEMO_DIR = BASE_DIR / "center subagents demo"
if str(DEMO_DIR) not in sys.path:
    sys.path.insert(0, str(DEMO_DIR))

from shared_langchain_components import call_llm
from agent_8_steps.state import Agent8StepState
from utils.string_utils import clean_gmail_ui_artifacts
import config

DATA_DIR = Path(__file__).parent.parent.parent / "data"
RESOLUTIONS_FILE = DATA_DIR / "resolutions_history.json"


def _save_resolution_to_history(record: dict):
    """Lưu kết quả xử lý yêu cầu phần mềm vào kho tri thức kinh nghiệm."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    history = []
    if RESOLUTIONS_FILE.exists():
        try:
            with open(RESOLUTIONS_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = []

    history.append(record)
    try:
        with open(RESOLUTIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        print("💾 [KNOWLEDGE FEEDBACK] Đã cập nhật kết quả yêu cầu cài đặt phần mềm vào kho tri thức 'data/resolutions_history.json'.")
    except Exception as e:
        print(f"⚠️ [KNOWLEDGE FEEDBACK] Lỗi lưu tri thức: {e}")


def _markdown_to_html(text: str) -> str:
    """Chuyển đổi Markdown sang HTML hiển thị đẹp trong email."""
    if not text:
        return ""
    escaped = html.escape(text)
    escaped = re.sub(r'```(.*?)```', r'<pre style="background:#f4f4f4; padding:10px; border-radius:4px; font-family:monospace;">\1</pre>', escaped, flags=re.DOTALL)
    escaped = re.sub(r'`([^`]+)`', r'<code style="background:#f4f4f4; padding:2px 4px; border-radius:3px; font-family:monospace; color:#c7254e;">\1</code>', escaped)
    escaped = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', escaped)
    escaped = re.sub(r'\*(.*?)\*', r'<em>\1</em>', escaped)

    lines = escaped.splitlines()
    html_lines = []
    in_list = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith(("- ", "* ", "• ")):
            if not in_list:
                html_lines.append('<ul style="margin: 8px 0; padding-left: 20px;">')
                in_list = True
            item_text = stripped[2:].strip()
            html_lines.append(f'<li style="margin-bottom: 4px;">{item_text}</li>')
        elif re.match(r'^\d+\.\s+', stripped):
            if not in_list:
                html_lines.append('<ol style="margin: 8px 0; padding-left: 20px;">')
                in_list = True
            item_text = re.sub(r'^\d+\.\s+', '', stripped)
            html_lines.append(f'<li style="margin-bottom: 4px;">{item_text}</li>')
        else:
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            if stripped:
                html_lines.append(f'<p style="margin: 8px 0; line-height: 1.6;">{stripped}</p>')
            else:
                html_lines.append('<br>')

    if in_list:
        html_lines.append('</ul>')

    return "\n".join(html_lines)


def process(state: Agent8StepState) -> dict:
    """
    BƯỚC 6B: SOFTWARE RESOLUTION
    - Sinh hướng dẫn cài đặt phần mềm chi tiết, dễ thao tác.
    - Lưu kết quả vào cơ sở tri thức resolutions_history.json.
    - Đóng gói nội dung email phản hồi hoàn chỉnh, trang trọng (HTML & Plain text).
    """
    user_req = state.get("user_request", {})
    sw_intent = state.get("software_intent", {})
    sw_context = state.get("software_context", {})
    sw_prereq = state.get("software_prerequisites", {})
    ticket_data = state.get("ticket", {})

    sender_name = user_req.get("sender", "Anh/Chị")
    clean_subject = user_req.get("clean_subject", "Yêu cầu cài đặt phần mềm")
    software_name = sw_intent.get("software_name", "Phần mềm văn phòng")
    work_purpose = sw_intent.get("work_purpose", "")
    kb_id = sw_intent.get("kb_id", "SOF-01")
    is_eligible = sw_prereq.get("is_eligible", True)
    prereq_summary = sw_prereq.get("summary", "")
    missing_info = sw_context.get("missing_info", "Đầy đủ")
    printer_ip = sw_context.get("printer_ip", "")
    department = sw_context.get("department", "")

    ticket_id = ticket_data.get("ticket_id", "")
    kb_item = sw_intent.get("kb_item", {})
    assigned_team = (
        ticket_data.get("assigned_team")
        or sw_intent.get("assigned_team")
        or kb_item.get("assigned_team")
        or "IT Support Team"
    )
    status = ticket_data.get("status", "APPROVED_FOR_INSTALLATION")
    svd_url = ticket_data.get("svd_url", "")

    has_prerequisites = sw_prereq.get("has_prerequisites")
    if has_prerequisites is None:
        prereq_rule = sw_prereq.get("prerequisite_rule", "")
        has_prerequisites = bool(prereq_rule and prereq_rule.strip().lower() not in ["no", "none", "không", "không có", ""])

    # Lấy thông tin Required Context mà người dùng đã cung cấp
    provided_context = dict(sw_context.get("provided_context") or {})
    accumulated_context = user_req.get("accumulated_context") or {}
    for k, v in accumulated_context.items():
        if k not in provided_context and v and str(v).lower() not in ["none", "chưa rõ", "unknown", "chưa có", ""]:
            provided_context[k] = v

    required_standard = sw_context.get("required_fields_standard") or ""
    req_lower = required_standard.lower()

    if not provided_context and req_lower not in ["no", "none", "không", "không có", ""]:
        if any(kw in req_lower for kw in ["phòng ban", "phong ban", "department"]):
            if department and department.strip().lower() not in ["chưa rõ", "no", "none", "", "n/a", "unknown"]:
                provided_context["Phòng ban"] = department
        if any(kw in req_lower for kw in ["ip", "máy in", "may in", "printer"]):
            if printer_ip and printer_ip.strip().lower() not in ["chưa rõ", "no", "none", "", "n/a", "unknown"]:
                provided_context["IP máy in"] = printer_ip

    # Nhận diện xem đây là cập nhật ticket đã có hay tiếp nhận yêu cầu mới
    is_ticket_update = bool(
        user_req.get("existing_ticket_id")
        or user_req.get("existing_svd_id")
        or ticket_data.get("action_taken") == "UPDATED_EXISTING_TICKET"
        or ticket_data.get("is_new_ticket") is False
    )

    ticket_id = ticket_data.get("ticket_id") or user_req.get("existing_ticket_id") or ""
    svd_request_id = ticket_data.get("svd_request_id") or user_req.get("existing_svd_id") or ""
    ticket_num = svd_request_id or (ticket_id.replace("SVD-", "") if ticket_id.startswith("SVD-") else ticket_id)
    ticket_display = f"#{ticket_num}" if ticket_num else (f"#{ticket_id}" if ticket_id else "")

    if is_ticket_update:
        installation_guidance = f"Yêu cầu cài đặt phần mềm {software_name} đã được cập nhật vào phiếu {ticket_display} và chuyển đến đội ngũ {assigned_team}."
    else:
        installation_guidance = f"Yêu cầu cài đặt phần mềm {software_name} đã được tiếp nhận và chuyển đến đội ngũ {assigned_team}."

    # 1. Lưu bản ghi vào kho tri thức lịch sử
    history_record = {
        "ticket_id": ticket_id or "N/A",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "requester": user_req.get("sender_email"),
        "subject": clean_subject,
        "flow_type": "software_install",
        "software_name": software_name,
        "kb_id": kb_id,
        "prerequisite_status": sw_prereq.get("status"),
        "prerequisite_summary": prereq_summary,
        "missing_info": missing_info,
        "provided_context": provided_context,
        "status": status,
        "assigned_team": assigned_team,
    }
    _save_resolution_to_history(history_record)

    # 2. Xây dựng tiêu đề email phản hồi
    if clean_subject.lower().startswith("re:"):
        reply_subject = clean_subject
    elif ticket_id:
        reply_subject = f"Re: [{ticket_id}] {clean_subject}"
    else:
        reply_subject = f"Re: [Yêu cầu cài đặt] {clean_subject}"

    is_in_catalog = sw_intent.get("is_in_catalog", True)

    # 3. Tạo nội dung email Plain Text
    missing_info_plain = f"\n⚠️ Lưu ý thông tin cần bổ sung: {missing_info}. Vui lòng phản hồi email này để cung cấp thêm thông tin giúp IT triển khai nhanh chóng.\n" if missing_info != "Đầy đủ" else ""
    prereq_plain = f"• Điều kiện tiên quyết : {prereq_summary}\n" if has_prerequisites else ""
    context_plain = "".join([f"• {k:<18}: {v}\n" for k, v in provided_context.items()])

    if is_ticket_update:
        ack_text_plain = f"Trung tâm Hỗ trợ Kỹ thuật IT Service Desk đã cập nhật yêu cầu cài đặt phần mềm của Anh/Chị vào phiếu hỗ trợ {ticket_display}."
        table_title_plain = "THÔNG TIN CẬP NHẬT YÊU CẦU DỊCH VỤ (SERVICE REQUEST UPDATE)"
        non_catalog_record_plain = f"Yêu cầu của Anh/Chị đã được hệ thống cập nhật vào phiếu {ticket_display}."
        non_catalog_record_html = f"Yêu cầu của Anh/Chị đã được hệ thống cập nhật vào phiếu <strong>{ticket_display}</strong>."
    else:
        ack_text_plain = "Trung tâm Hỗ trợ Kỹ thuật IT Service Desk đã tiếp nhận yêu cầu cài đặt phần mềm của Anh/Chị."
        table_title_plain = "THÔNG TIN YÊU CẦU DỊCH VỤ (SERVICE REQUEST)"
        non_catalog_record_plain = "Yêu cầu của Anh/Chị đã được hệ thống ghi nhận."
        non_catalog_record_html = "Yêu cầu của Anh/Chị đã được hệ thống ghi nhận."

    non_catalog_warning_plain = f"""
⚠️ CẢNH BÁO / LƯU Ý QUAN TRỌNG:
Phần mềm '{software_name}' hiện không nằm trong danh mục phần mềm tiêu chuẩn theo quy định của công ty.
{non_catalog_record_plain} Đội ngũ {assigned_team} sẽ xem xét, đánh giá về tính tương thích, bảo mật và chính sách cấp phép để quyết định có hỗ trợ cài đặt hay không.
""" if not is_in_catalog else ""

    closing_note_plain = (
        f"Đội ngũ {assigned_team} sẽ sớm liên hệ và hỗ trợ cài đặt ứng dụng cho Anh/Chị."
        if is_in_catalog
        else f"Đội ngũ {assigned_team} sẽ tiến hành xem xét, đánh giá và phản hồi lại Anh/Chị."
    )

    reply_body_plain = f"""Kính gửi {sender_name},

{ack_text_plain}

======================================================================
{table_title_plain}
• Phần mềm yêu cầu  : {software_name}
• Đội ngũ phụ trách : {assigned_team}
{context_plain}{prereq_plain}======================================================================
{non_catalog_warning_plain}{missing_info_plain}
{closing_note_plain}

Kính chúc Anh/Chị một ngày làm việc thuận lợi và hiệu quả!

Trân trọng,
{config.EMAIL_SIGNATURE_PLAIN}
"""

    # 4. Tạo nội dung email HTML chuyên nghiệp
    svd_box_title = (
        f"🎫 Phiếu yêu cầu đã được cập nhật thành công trên ServiceDesk Plus"
        if is_ticket_update
        else "🎫 Phiếu yêu cầu đã được tạo thành công trên ServiceDesk Plus"
    )
    svd_link_html = f"""
    <div style="background-color: #e8f0fe; border: 1px solid #1a73e8; border-radius: 6px; padding: 14px; margin: 16px 0; text-align: center;">
        <p style="margin: 0 0 8px 0; color: #1a73e8; font-weight: bold; font-size: 14px;">
            {svd_box_title}
        </p>
        <a href="{svd_url}" target="_blank" style="background-color: #1a73e8; color: #ffffff; padding: 10px 22px; font-weight: bold; text-decoration: none; border-radius: 4px; display: inline-block; font-size: 13px;">
            👉 Bấm vào đây để theo dõi Ticket {ticket_display} (user: guest, password: Guest@123)
        </a>
        <p style="margin: 8px 0 0 0; color: #5f6368; font-size: 11px;">(Đường link trực tiếp: <a href="{svd_url}" style="color: #1a73e8;">{svd_url}</a>)</p>
    </div>
    """ if svd_url else ""

    missing_info_box = f"""
    <div style="background-color: #fef7e0; border-left: 4px solid #f9ab00; padding: 10px 14px; margin: 12px 0; font-size: 13px; color: #b06000;">
        <b>⚠️ Thông tin cần bổ sung:</b> {missing_info}. Vui lòng phản hồi email này để cung cấp thêm thông tin giúp IT triển khai nhanh chóng.
    </div>
    """ if missing_info != "Đầy đủ" else ""

    non_catalog_warning_html = f"""
        <div style="background-color: #fef7e0; border-left: 4px solid #f9ab00; padding: 14px 16px; margin: 16px 0; border-radius: 4px;">
            <p style="margin: 0 0 6px 0; font-weight: bold; color: #b06000; font-size: 14px;">
                ⚠️ CẢNH BÁO: PHẦN MỀM NGOÀI DANH MỤC QUY ĐỊNH
            </p>
            <p style="margin: 0; color: #5f6368; font-size: 13px; line-height: 1.5;">
                Phần mềm <strong>{software_name}</strong> hiện <strong>không nằm trong danh mục phần mềm tiêu chuẩn</strong> theo quy định của công ty.<br>
                {non_catalog_record_html} Đội ngũ <strong>{assigned_team}</strong> sẽ xem xét, đánh giá có hỗ trợ hay không và phản hồi lại Anh/Chị.
            </p>
        </div>
""" if not is_in_catalog else ""

    context_html_rows = "".join([
        f"""                <tr>
                    <td style="padding: 4px 0; color: #555555; width: 35%;"><b>{html.escape(k)}:</b></td>
                    <td style="padding: 4px 0; color: #202124;">{html.escape(str(v))}</td>
                </tr>\n"""
        for k, v in provided_context.items()
    ])

    prereq_html_row = f"""                <tr>
                    <td style="padding: 4px 0; color: #555555;"><b>Điều kiện tiên quyết:</b></td>
                    <td style="padding: 4px 0; color: {'#137333' if is_eligible else '#c5221f'}; font-weight: 500;">{prereq_summary}</td>
                </tr>
""" if has_prerequisites else ""

    closing_note_html = (
        f"Đội ngũ <b>{assigned_team}</b> sẽ sớm liên hệ và hỗ trợ cài đặt ứng dụng cho Anh/Chị."
        if is_in_catalog
        else f"Đội ngũ <b>{assigned_team}</b> sẽ tiến hành xem xét, đánh giá và phản hồi lại Anh/Chị."
    )

    if is_ticket_update:
        html_header_title = f"💻 CẬP NHẬT YÊU CẦU CÀI ĐẶT PHẦN MỀM: {software_name}"
        html_header_subtitle = f"Hệ thống Quản lý Yêu cầu Dịch vụ IT Service Desk - Cập nhật Phiếu {ticket_display}"
        html_greeting_text = f"Bộ phận IT Service Desk đã cập nhật yêu cầu cài đặt và hỗ trợ ứng dụng của Anh/Chị vào phiếu hỗ trợ <strong>{ticket_display}</strong>."
    else:
        html_header_title = f"💻 TIẾP NHẬN YÊU CẦU CÀI ĐẶT PHẦN MỀM: {software_name}"
        html_header_subtitle = "Hệ thống Quản lý Yêu cầu Dịch vụ IT Service Desk tự động"
        html_greeting_text = "Bộ phận IT Service Desk đã tiếp nhận yêu cầu cài đặt và hỗ trợ ứng dụng của Anh/Chị."

    reply_body_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
</head>
<body style="font-family: Arial, 'Segoe UI', Tahoma, sans-serif; font-size: 14px; line-height: 1.6; color: #333333; margin: 0; padding: 16px; background-color: #f9f9f9;">
    <div style="max-width: 680px; margin: 0 auto; background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 24px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
        
        <div style="border-bottom: 2px solid #1a73e8; padding-bottom: 12px; margin-bottom: 20px;">
            <h2 style="margin: 0; color: #1a73e8; font-size: 18px;">
                {html_header_title}
            </h2>
            <p style="margin: 4px 0 0 0; font-size: 12px; color: #666666;">
                {html_header_subtitle}
            </p>
        </div>

        <p>Kính gửi <b>{sender_name}</b>,</p>
        <p>{html_greeting_text}</p>

        <div style="background-color: #f8f9fa; border: 1px solid #e9ecef; border-radius: 6px; padding: 14px; margin: 16px 0;">
            <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                <tr>
                    <td style="padding: 4px 0; color: #555555; width: 35%;"><b>Phần mềm yêu cầu:</b></td>
                    <td style="padding: 4px 0; font-weight: bold; color: #202124;">{software_name}</td>
                </tr>
                <tr>
                    <td style="padding: 4px 0; color: #555555;"><b>Đội ngũ phụ trách:</b></td>
                    <td style="padding: 4px 0; font-weight: bold; color: #1a73e8;">{assigned_team}</td>
                </tr>
{context_html_rows}{prereq_html_row}            </table>
        </div>

        {non_catalog_warning_html}
        {missing_info_box}
        {svd_link_html}

        <div style="background-color: #f1f3f4; border-radius: 6px; padding: 12px; margin-top: 20px; font-size: 12px; color: #555555;">
            {closing_note_html}
        </div>

        {config.EMAIL_SIGNATURE_HTML}
    </div>
</body>
</html>
"""

    # Loại bỏ triệt để mọi thẻ UI Gmail nếu còn sót
    reply_body_plain = clean_gmail_ui_artifacts(reply_body_plain)
    patterns = [
        r'<div[^>]*?(?:class=[\'"][^\'"]*?\bajR\b[^\'"]*?[\'"]|aria-label=[\'"][^\'"]*?(?:Ẩn nội dung|Hiển thị nội dung|Show trimmed content|Hide expanded content)[^\'"]*?[\'"])[^>]*?>.*?</div>',
        r'&lt;div[^>]*?(?:class=[\'"][^\'"]*?\bajR\b[^\'"]*?[\'"]|aria-label=[\'"][^\'"]*?(?:Ẩn nội dung|Hiển thị nội dung|Show trimmed content|Hide expanded content)[^\'"]*?[\'"])[^>]*?&gt;.*?&lt;/div&gt;',
        r'<img[^>]*?(?:class=[\'"][^\'"]*?\bajT\b[^\'"]*?[\'"]|src=[\'"][^\'"]*?cleardot\.gif[^\'"]*?[\'"])[^>]*?>',
        r'&lt;img[^>]*?(?:class=[\'"][^\'"]*?\bajT\b[^\'"]*?[\'"]|src=[\'"][^\'"]*?cleardot\.gif[^\'"]*?[\'"])[^>]*?&gt;',
    ]
    for p in patterns:
        reply_body_html = re.sub(p, '', reply_body_html, flags=re.DOTALL | re.IGNORECASE)

    print("\n" + "=" * 70)
    print("🔹 [BƯỚC 6B: SOFTWARE RESOLUTION] ĐÓNG GÓI EMAIL PHẢN HỒI & LƯU TRI THỨC")
    print("=" * 70)
    print(f" • Tiêu đề email phản hồi: {reply_subject}")
    print(f" • Đội ngũ phụ trách     : {assigned_team}")
    print(" • Cập nhật lịch sử       : data/resolutions_history.json")
    print(" • Email phản hồi (HTML & Plain Text) đã sẵn sàng để gửi.")

    return {
        "resolution": {
            "reply_subject": reply_subject,
            "reply_body_plain": reply_body_plain,
            "reply_body_html": reply_body_html,
            "installation_guidance": installation_guidance,
            "status": status,
            "is_eligible": is_eligible,
        }
    }


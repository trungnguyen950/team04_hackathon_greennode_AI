import json
import html
import re
from datetime import datetime
from pathlib import Path

from agent_8_steps.state import Agent8StepState
from utils.string_utils import clean_gmail_ui_artifacts
import config

DATA_DIR = Path(__file__).parent.parent.parent / "data"
RESOLUTIONS_FILE = DATA_DIR / "resolutions_history.json"


def _save_resolution_to_history(record: dict):
    """Lưu kết quả xử lý thành công vào kho tri thức kinh nghiệm."""
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
        print("💾 [KNOWLEDGE FEEDBACK] Đã cập nhật kết quả xử lý vào kho dữ liệu tri thức 'data/resolutions_history.json'.")
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
    BƯỚC 8: RESOLUTION
    Lưu trữ kết quả xử lý vào cơ sở dữ liệu phục vụ Knowledge Base trong tương lai
    và đóng gói nội dung email phản hồi hoàn chỉnh, trang trọng cho người dùng.
    """
    user_req = state.get("user_request", {})
    intent_data = state.get("intent", {})
    kb_data = state.get("knowledge", {})
    diag_data = state.get("diagnostic", {})
    rec_data = state.get("recommendation", {})
    ticket_data = state.get("ticket", {})

    sender_name = user_req.get("sender", "Anh/Chị")
    clean_subject = user_req.get("clean_subject", "Sự cố kỹ thuật")
    ticket_id = ticket_data.get("ticket_id", "")
    assigned_team = ticket_data.get("assigned_team", "IT Support")
    status = ticket_data.get("status", "RESOLVED_BY_AI")
    priority = ticket_data.get("priority", "MEDIUM")
    action_taken = ticket_data.get("action_taken", "CREATED_NEW_TICKET")
    is_issue_resolved = intent_data.get("is_issue_resolved", False)

    root_cause = diag_data.get("root_cause", "Sự cố dịch vụ")
    steps_guidance = rec_data.get("steps_guidance", "Đang xử lý...")
    kb_id = kb_data.get("kb_id", "KB-SOP")

    # 1. Lưu bản ghi Resolution vào kho lịch sử tri thức
    history_record = {
        "ticket_id": ticket_id or "N/A",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "requester": user_req.get("sender_email"),
        "subject": clean_subject,
        "intent_name": intent_data.get("intent_name"),
        "category": intent_data.get("category"),
        "kb_id": kb_id,
        "root_cause": root_cause,
        "resolution_summary": rec_data.get("action_title"),
        "status": status,
        "action_taken": action_taken,
        "assigned_team": assigned_team,
    }
    _save_resolution_to_history(history_record)

    # 2. Tạo tiêu đề phản hồi (Re: ...)
    if clean_subject.lower().startswith("re:"):
        reply_subject = clean_subject
    elif ticket_id:
        reply_subject = f"Re: [{ticket_id}] {clean_subject}"
    else:
        reply_subject = f"Re: {clean_subject}"

    svd_url = ticket_data.get("svd_url", "")
    svd_link_plain = f"• Link ServiceDesk : {svd_url}\n" if svd_url else ""

    # =========================================================================
    # TRƯỜNG HỢP 1: VẤN ĐỀ ĐÃ ĐƯỢC GIẢI QUYẾT XONG (RESOLVED / CLOSED)
    # =========================================================================
    if is_issue_resolved:
        ticket_label = f"#{ticket_id}" if ticket_id else "của Anh/Chị"
        reply_body_plain = f"""Kính gửi {sender_name},

Trung tâm Dịch vụ Hỗ trợ IT Service Desk xin chân thành cảm ơn phản hồi của Anh/Chị.

Hệ thống đã ghi nhận sự cố của Anh/Chị đã được giải quyết thành công:
======================================================================
THÔNG TIN PHIẾU HỖ TRỢ (SERVICE DESK TICKET)
• Mã Ticket        : {ticket_id or 'N/A'}
{svd_link_plain}• Nhóm sự cố       : {intent_data.get('category')}
• Trạng thái       : ĐÃ GIẢI QUYẾT XONG (CLOSED)
======================================================================

Phiếu hỗ trợ {ticket_label} trên hệ thống ServiceDesk Plus hiện đã được đóng hoàn tất (Status: CLOSED).
Nếu có bất kỳ vấn đề nào khác cần hỗ trợ trong tương lai, Anh/Chị vui lòng gửi yêu cầu mới để IT Service Desk kịp thời hỗ trợ.

Chúc Anh/Chị một ngày làm việc hiệu quả và thành công!

{config.EMAIL_SIGNATURE_PLAIN}
"""

        svd_link_html = f"""
        <div style="background-color: #e6f4ea; border: 1px solid #34a853; border-radius: 6px; padding: 14px; margin: 16px 0; text-align: center;">
            <p style="margin: 0 0 8px 0; color: #137333; font-weight: bold; font-size: 14px;">
                ✅ Phiếu yêu cầu đã được đóng hoàn tất trên ServiceDesk Plus
            </p>
            <a href="{svd_url}" target="_blank" style="background-color: #34a853; color: #ffffff; padding: 10px 22px; font-weight: bold; text-decoration: none; border-radius: 4px; display: inline-block; font-size: 13px;">
                👉 Bấm vào đây để xem chi tiết Ticket {ticket_label} (user: guest, password: Guest@123)
            </a>
            <p style="margin: 8px 0 0 0; color: #5f6368; font-size: 11px;">(Đường link trực tiếp: <a href="{svd_url}" style="color: #34a853;">{svd_url}</a>)</p>
        </div>
        """ if svd_url else ""

        reply_body_html = f"""
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: 'Segoe UI', Arial, sans-serif; color: #202124; line-height: 1.6; font-size: 14px; background-color: #f8f9fa; margin: 0; padding: 20px;">
    <div style="max-width: 700px; margin: 0 auto; background: #ffffff; border: 1px solid #dadce0; border-radius: 8px; padding: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
        
        <!-- Header -->
        <div style="border-bottom: 2px solid #34a853; padding-bottom: 12px; margin-bottom: 20px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="background-color: #e6f4ea; color: #137333; font-size: 12px; font-weight: bold; padding: 4px 12px; border-radius: 12px; text-transform: uppercase;">
                    {assigned_team}
                </span>
                <span style="background-color: #34a853; color: #ffffff; font-size: 11px; font-weight: bold; padding: 4px 10px; border-radius: 12px;">
                    CLOSED
                </span>
            </div>
            <h2 style="color: #202124; margin: 12px 0 4px 0; font-size: 18px;">Phiếu Hỗ Trợ Đã Giải Quyết Xong {ticket_label}</h2>
            <p style="margin: 0; color: #5f6368; font-size: 12px;">Tiêu đề: {html.escape(clean_subject)}</p>
        </div>

        <!-- Lời chào -->
        <p>Kính gửi <strong>{html.escape(sender_name)}</strong>,</p>
        <p>Trung tâm Dịch vụ Hỗ trợ IT Service Desk xin cảm ơn phản hồi của Anh/Chị. Chúng tôi rất vui mừng ghi nhận sự cố của Anh/Chị đã được giải quyết thành công.</p>

        <div style="background-color: #e6f4ea; border-left: 4px solid #34a853; padding: 14px 18px; border-radius: 4px; margin: 16px 0;">
            <strong style="color: #137333; font-size: 14px;">✅ XÁC NHẬN ĐÓNG PHIẾU HỖ TRỢ:</strong>
            <p style="margin: 6px 0 0 0; color: #3c4043;">
                Phiếu hỗ trợ <strong>{ticket_label}</strong> đã được cập nhật trạng thái <strong>CLOSED</strong> trên hệ thống ServiceDesk Plus.
            </p>
        </div>

        {svd_link_html}

        <p style="color: #5f6368; font-size: 13px; margin-top: 20px;">
            Nếu Anh/Chị cần hỗ trợ thêm bất kỳ vấn đề nào trong tương lai, xin vui lòng gửi yêu cầu mới để IT Service Desk kịp thời phục vụ.
        </p>

        <!-- Chữ ký -->
        {config.EMAIL_SIGNATURE_HTML}
    </div>
</body>
</html>
"""

    # =========================================================================
    # TRƯỜNG HỢP 2: PHẢN HỒI BỔ SUNG TRÊN TICKET CŨ (UPDATED_EXISTING_TICKET)
    # =========================================================================
    elif action_taken == "UPDATED_EXISTING_TICKET":
        status_label = "Đang xử lý (Cập nhật phản hồi từ người dùng)"
        steps_guidance_html = _markdown_to_html(steps_guidance)

        svd_link_html = f"""
        <div style="background-color: #e8f0fe; border: 1px solid #1a73e8; border-radius: 6px; padding: 14px; margin: 16px 0; text-align: center;">
            <p style="margin: 0 0 8px 0; color: #1a73e8; font-weight: bold; font-size: 14px;">
                🎫 Phản hồi đã được cập nhật vào Phiếu #{ticket_id} trên ServiceDesk Plus
            </p>
            <a href="{svd_url}" target="_blank" style="background-color: #1a73e8; color: #ffffff; padding: 10px 22px; font-weight: bold; text-decoration: none; border-radius: 4px; display: inline-block; font-size: 13px;">
                👉 Bấm vào đây để theo dõi tiến độ Ticket #{ticket_id} (user: guest, password: Guest@123)
            </a>
            <p style="margin: 8px 0 0 0; color: #5f6368; font-size: 11px;">(Đường link trực tiếp: <a href="{svd_url}" style="color: #1a73e8;">{svd_url}</a>)</p>
        </div>
        """ if svd_url else ""

        reply_body_plain = f"""Kính gửi {sender_name},

Cảm ơn Anh/Chị đã phản hồi. IT Service Desk đã cập nhật thông tin yêu cầu của Anh/Chị vào Phiếu hỗ trợ #{ticket_id} trên hệ thống ServiceDesk Plus:

======================================================================
THÔNG TIN PHIẾU HỖ TRỢ (SERVICE DESK TICKET)
• Mã Ticket        : {ticket_id}
{svd_link_plain}• Nhóm sự cố       : {intent_data.get('category')} -> {intent_data.get('intent_name')}
• Mức độ ưu tiên   : {priority}
• Đội ngũ phụ trách: {assigned_team}
• Trạng thái       : {status_label}
======================================================================

1. KẾT QUẢ CHẨN ĐOÁN TIẾP THEO (DIAGNOSTIC):
- {root_cause}

2. HƯỚNG DẪN XỬ LÝ (RECOMMENDED ACTION):
{steps_guidance}

Nếu sự cố vẫn chưa được giải quyết sau khi thực hiện các bước trên, vui lòng tiếp tục phản hồi email này để đội ngũ {assigned_team} tiếp tục hỗ trợ.

{config.EMAIL_SIGNATURE_PLAIN}
"""

        reply_body_html = f"""
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: 'Segoe UI', Arial, sans-serif; color: #202124; line-height: 1.6; font-size: 14px; background-color: #f8f9fa; margin: 0; padding: 20px;">
    <div style="max-width: 700px; margin: 0 auto; background: #ffffff; border: 1px solid #dadce0; border-radius: 8px; padding: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
        
        <!-- Header -->
        <div style="border-bottom: 2px solid #1a73e8; padding-bottom: 12px; margin-bottom: 20px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="background-color: #e8f0fe; color: #1a73e8; font-size: 12px; font-weight: bold; padding: 4px 12px; border-radius: 12px; text-transform: uppercase;">
                    {assigned_team}
                </span>
                <span style="background-color: #1a73e8; color: #ffffff; font-size: 11px; font-weight: bold; padding: 4px 10px; border-radius: 12px;">
                    IN PROGRESS
                </span>
            </div>
            <h2 style="color: #202124; margin: 12px 0 4px 0; font-size: 18px;">Cập Nhật Phiếu Hỗ Trợ #{ticket_id}</h2>
            <p style="margin: 0; color: #5f6368; font-size: 12px;">Tiêu đề: {html.escape(clean_subject)} | SOP: {kb_id}</p>
        </div>

        <!-- Lời chào -->
        <p>Kính gửi <strong>{html.escape(sender_name)}</strong>,</p>
        <p>Hệ thống IT Service Desk đã cập nhật yêu cầu của Anh/Chị vào phiếu hỗ trợ <strong>#{ticket_id}</strong> trên ServiceDesk Plus. Dưới đây là thông tin chi tiết:</p>

        {svd_link_html}

        <!-- Thẻ Chẩn đoán -->
        <div style="background-color: #fef7e0; border-left: 4px solid #f9ab00; padding: 12px 16px; border-radius: 4px; margin: 16px 0;">
            <strong style="color: #b06000; font-size: 13px;">🔍 KẾT QUẢ CHẨN ĐOÁN (DIAGNOSTIC):</strong>
            <p style="margin: 6px 0 0 0; color: #3c4043;">{html.escape(root_cause)}</p>
        </div>

        <!-- Thẻ Hướng dẫn xử lý -->
        <div style="background-color: #f8f9fa; border-left: 4px solid #1a73e8; padding: 16px; border-radius: 4px; margin: 18px 0;">
            <strong style="color: #1a73e8; font-size: 13px;">🛠️ HƯỚNG DẪN XỬ LÝ (RECOMMENDATION):</strong>
            <div style="margin-top: 8px;">
                {steps_guidance_html}
            </div>
        </div>

        <div style="background-color: #f1f3f4; padding: 12px; border-radius: 6px; font-size: 12px; color: #5f6368; margin-top: 20px;">
            ℹ️ Nếu sự cố vẫn tiếp diễn sau khi thực hiện hướng dẫn, Anh/Chị vui lòng tiếp tục trả lời email này để <strong>{assigned_team}</strong> tiếp nhận xử lý cấp độ cao hơn.
        </div>

        <!-- Chữ ký -->
        {config.EMAIL_SIGNATURE_HTML}
    </div>
</body>
</html>
"""

    # =========================================================================
    # TRƯỜNG HỢP 3: TẠO TICKET MỚI (CREATED_NEW_TICKET)
    # =========================================================================
    else:
        status_label = "Đã xử lý & Hướng dẫn tự động (Self-Service)" if status == "RESOLVED_BY_AI" else "Đã chuyển cấp Kỹ sư chuyên trách (Escalated)"
        steps_guidance_html = _markdown_to_html(steps_guidance)
        status_badge_color = "#34a853" if status == "RESOLVED_BY_AI" else "#ea4335"

        svd_link_html = f"""
        <div style="background-color: #e8f0fe; border: 1px solid #1a73e8; border-radius: 6px; padding: 14px; margin: 16px 0; text-align: center;">
            <p style="margin: 0 0 8px 0; color: #1a73e8; font-weight: bold; font-size: 14px;">
                🎫 Phiếu yêu cầu đã được tạo thành công trên ServiceDesk Plus
            </p>
            <a href="{svd_url}" target="_blank" style="background-color: #1a73e8; color: #ffffff; padding: 10px 22px; font-weight: bold; text-decoration: none; border-radius: 4px; display: inline-block; font-size: 13px;">
                👉 Bấm vào đây để theo dõi Ticket #{ticket_id} (user: guest, password: Guest@123)
            </a>
            <p style="margin: 8px 0 0 0; color: #5f6368; font-size: 11px;">(Đường link trực tiếp: <a href="{svd_url}" style="color: #1a73e8;">{svd_url}</a>)</p>
        </div>
        """ if svd_url else ""

        reply_body_plain = f"""Kính gửi {sender_name},

Cảm ơn Anh/Chị đã liên hệ Trung tâm Dịch vụ Hỗ trợ IT Service Desk.
Yêu cầu của Anh/Chị đã được tạo trên hệ thống ServiceDesk và xử lý theo quy trình chuẩn (SOP ID: {kb_id}):

======================================================================
THÔNG TIN PHIẾU HỖ TRỢ (SERVICE DESK TICKET)
• Mã Ticket        : {ticket_id}
{svd_link_plain}• Nhóm sự cố       : {intent_data.get('category')} -> {intent_data.get('intent_name')}
• Mức độ ưu tiên   : {priority}
• Đội ngũ phụ trách: {assigned_team}
• Trạng thái       : {status_label}
======================================================================

1. KẾT QUẢ CHẨN ĐOÁN (DIAGNOSTIC):
- Nguyên nhân cốt lõi: {root_cause}

2. HƯỚNG DẪN XỬ LÝ (RECOMMENDED ACTION):
{steps_guidance}

Nếu Anh/Chị đã thực hiện theo các bước trên nhưng sự cố vẫn chưa được giải quyết, vui lòng phản hồi lại email này. Đội ngũ {assigned_team} sẽ liên hệ và hỗ trợ trực tiếp.

{config.EMAIL_SIGNATURE_PLAIN}
"""

        reply_body_html = f"""
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: 'Segoe UI', Arial, sans-serif; color: #202124; line-height: 1.6; font-size: 14px; background-color: #f8f9fa; margin: 0; padding: 20px;">
    <div style="max-width: 700px; margin: 0 auto; background: #ffffff; border: 1px solid #dadce0; border-radius: 8px; padding: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
        
        <!-- Header Phiếu Hỗ trợ -->
        <div style="border-bottom: 2px solid #1a73e8; padding-bottom: 12px; margin-bottom: 20px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="background-color: #e8f0fe; color: #1a73e8; font-size: 12px; font-weight: bold; padding: 4px 12px; border-radius: 12px; text-transform: uppercase;">
                    {assigned_team}
                </span>
                <span style="background-color: {status_badge_color}; color: #ffffff; font-size: 11px; font-weight: bold; padding: 4px 10px; border-radius: 12px;">
                    {status}
                </span>
            </div>
            <h2 style="color: #202124; margin: 12px 0 4px 0; font-size: 18px;">Phiếu Hỗ Trợ Kỹ Thuật #{ticket_id}</h2>
            <p style="margin: 0; color: #5f6368; font-size: 12px;">Tiêu đề: {html.escape(clean_subject)} | SOP: {kb_id}</p>
        </div>

        <!-- Lời chào -->
        <p>Kính gửi <strong>{html.escape(sender_name)}</strong>,</p>
        <p>Hệ thống IT Service Desk đã tiếp nhận yêu cầu, tạo phiếu xử lý và đối chiếu với Cơ sở Tri thức Kỹ thuật (SOP). Dưới đây là thông tin chi tiết:</p>

        {svd_link_html}

        <!-- Thẻ Chẩn đoán -->
        <div style="background-color: #fef7e0; border-left: 4px solid #f9ab00; padding: 12px 16px; border-radius: 4px; margin: 16px 0;">
            <strong style="color: #b06000; font-size: 13px;">🔍 KẾT QUẢ CHẨN ĐOÁN (DIAGNOSTIC):</strong>
            <p style="margin: 6px 0 0 0; color: #3c4043;">{html.escape(root_cause)}</p>
        </div>

        <!-- Thẻ Hướng dẫn xử lý -->
        <div style="background-color: #f8f9fa; border-left: 4px solid #1a73e8; padding: 16px; border-radius: 4px; margin: 18px 0;">
            <strong style="color: #1a73e8; font-size: 13px;">🛠️ HƯỚNG DẪN XỬ LÝ (RECOMMENDATION):</strong>
            <div style="margin-top: 8px;">
                {steps_guidance_html}
            </div>
        </div>

        <!-- Thông tin liên hệ hỗ trợ thêm -->
        <div style="background-color: #f1f3f4; padding: 12px; border-radius: 6px; font-size: 12px; color: #5f6368; margin-top: 20px;">
            ℹ️ Nếu sự cố vẫn tiếp diễn sau khi thực hiện hướng dẫn, Anh/Chị vui lòng trả lời trực tiếp email này để <strong>{assigned_team}</strong> tiếp nhận xử lý cấp độ cao hơn.
        </div>

        <!-- Chữ ký -->
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
    print("🔹 [BƯỚC 8: RESOLUTION] LƯU TRI THỨC & ĐÓNG GÓI EMAIL PHẢN HỒI")
    print("=" * 70)
    print(f" • Mã Ticket         : {ticket_id}")
    print(f" • Tiêu đề phản hồi  : {reply_subject}")
    print(f" • Cập nhật lịch sử  : data/resolutions_history.json")
    print(" • Email phản hồi (HTML & Plain Text) đã sẵn sàng để gửi.")

    return {
        "resolution": {
            "ticket_id": ticket_id,
            "reply_subject": reply_subject,
            "reply_body_plain": reply_body_plain,
            "reply_body_html": reply_body_html,
            "saved_to_history": True,
        }
    }


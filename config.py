import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

# =====================================================================
# 1. CẤU HÌNH TÀI KHOẢN EMAIL (GMAIL SMTP / IMAP)
# =====================================================================
EMAIL_ACCOUNT = os.environ.get("GMAIL_EMAIL", "")
EMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")

IMAP_SERVER = "imap.gmail.com"
IMAP_PORT = 993

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# =====================================================================
# 2. CẤU HÌNH CHU KỲ QUÉT HÒM THƯ (POLLING)
# =====================================================================
# Khoảng thời gian nghỉ giữa mỗi lần kiểm tra hộp thư (tính bằng giây)
POLL_INTERVAL_SECONDS = int(os.environ.get("POLL_INTERVAL_SECONDS", 15))

# Thư mục hòm thư cần theo dõi
MAIL_FOLDER = "INBOX"

# Số lượng thư chưa đọc tối đa lấy ra mỗi lần quét
TOP_UNREAD_LIMIT = 5

# Tự động đánh dấu thư là đã đọc sau khi phản hồi thành công
AUTO_MARK_AS_READ = True

# =====================================================================
# 3. DANH SÁCH ĐỊA CHỈ EMAIL CẦN BỎ QUA (TRÁNH LẶP VÔ HẠN / SPAM)
# =====================================================================
# Các email không cần phản hồi tự động:
# - Chính tài khoản bot
# - Các địa chỉ no-reply, thông báo bảo mật hệ thống, daemon trả thư
IGNORE_SENDERS = [
    EMAIL_ACCOUNT.lower(),
    "no-reply@accounts.google.com",
    "mailer-daemon@googlemail.com",
    "mailer-daemon@gmail.com",
    "notifications@github.com",
]

# =====================================================================
# 4. CẤU HÌNH AI & LANGCHAIN / GREENNODE
# =====================================================================
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

# =====================================================================
# 5. CHỮ KÝ EMAIL TỰ ĐỘNG CỦA HỆ THỐNG
# =====================================================================
EMAIL_SIGNATURE_PLAIN = f"""
--
Trân trọng,
Hệ Thống Trợ Lý AI Tự Động - MSB Service Desk
Email hỗ trợ: {EMAIL_ACCOUNT}
----------------------------------------------------------------------
*Lưu ý: Email này được phản hồi tự động bởi hệ thống AI Multi-Agent. Nếu cần làm rõ hoặc hỗ trợ thêm, bạn chỉ cần trả lời trực tiếp email này.*
"""

EMAIL_SIGNATURE_HTML = f"""
<br><hr style="border: none; border-top: 1px solid #e0e0e0; margin: 20px 0;">
<div style="font-family: Arial, sans-serif; font-size: 13px; color: #555; line-height: 1.6;">
    <p style="margin: 0; font-weight: bold; color: #1a73e8;">MSB Service Desk - AI Multi-Agent Assistant</p>
    <p style="margin: 2px 0 0 0; color: #666;">📧 Email: <a href="mailto:{EMAIL_ACCOUNT}" style="color: #1a73e8; text-decoration: none;">{EMAIL_ACCOUNT}</a></p>
    <p style="margin: 8px 0 0 0; font-size: 11px; color: #888; font-style: italic;">
        *Thư này được tạo và phản hồi tự động. Quý khách/Anh/Chị có thể trả lời trực tiếp email này nếu cần hỗ trợ thêm.*
    </p>
</div>
"""


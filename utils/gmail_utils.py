#update date: 11/9/2026
import base64
from datetime import datetime
import email.utils
from email.message import EmailMessage
import mimetypes
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import smtplib
import imaplib
import email as email_pkg
import email.header as email_header_pkg
import email.utils as email_utils_pkg

_parseaddr = email_utils_pkg.parseaddr
_parsedate_to_datetime = email_utils_pkg.parsedate_to_datetime
_getaddresses = email_utils_pkg.getaddresses
_message_from_bytes = email_pkg.message_from_bytes
_decode_header = email_header_pkg.decode_header

from utils.string_utils import remove_html_tags, clean_gmail_ui_artifacts

MODE = "smtp/imap" #hay "google_api"

# CẤU HÌNH CỦA GMAIL API
TOKEN_FILE = Path(__file__).parent / "gmail_token.json"
CREDENTIALS_FILE = Path(__file__).parent / "gmail_credentials.json"

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
]

# CẤU HÌNH CỦA GMAIL SMTP/IMAP
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
IMAP_SERVER = "imap.gmail.com"
IMAP_PORT = 993
USE_TLS = True

# Biến toàn cục lưu Gmail Service để tái sử dụng
_GMAIL_SERVICE = None

def load_configs(input):
    global MODE
    if "mode" in input:
        MODE = input["mode"]

def __get_gmail_service(log = None):
    """
    Xác thực và khởi tạo Gmail API Service.
    Nếu chưa đăng nhập: Mở trình duyệt để người dùng đăng nhập tài khoản Google.
    Sau khi đăng nhập: Lưu thông tin phiên vào token.json để tái sử dụng.
    """
    creds = None
    logs = []

    # 1. Kiểm tra xem đã có token.json đã lưu từ trước chưa
    if TOKEN_FILE.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        except Exception as e:
            logs.append(f"[Cảnh báo] Lỗi đọc {TOKEN_FILE.name}: {e}. Đang tiến hành đăng nhập lại...")
            creds = None

    # 2. Nếu chưa có token hoặc token không còn hợp lệ
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                logs.append("Đang tự động làm mới mã xác thực (refresh token)...")
                creds.refresh(Request())
            except Exception as e:
                logs.append(f"Không thể làm mới token: {e}. Cần đăng nhập lại.")
                creds = None

        if not creds:
            # Kiểm tra xem người dùng đã tải file credentials.json vào thư mục chưa
            if not CREDENTIALS_FILE.exists():
                error_msg = (
                    f"\n[!] LỖI: Không tìm thấy file '{CREDENTIALS_FILE.name}'!\n"
                    f"Bạn cần tạo và tải file credentials từ Google Cloud Console:\n"
                    f"1. Truy cập: https://console.cloud.google.com/\n"
                    f"2. Bật Gmail API\n"
                    f"3. Tạo 'OAuth Client ID' (chọn loại Desktop app / Ứng dụng dành cho máy tính)\n"
                    f"4. Tải file JSON về và đổi tên thành 'credentials.json', đặt tại: {CREDENTIALS_FILE.parent}\n"
                    f"Xem hướng dẫn chi tiết trong file README.md.\n"
                )
                raise FileNotFoundError(error_msg)

            logs.append("\nĐang mở trình duyệt để bạn xác thực tài khoản Google...")
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE), SCOPES
            )
            creds = flow.run_local_server(port=0)

        # Lưu lại token cho các lần chạy tiếp theo
        with open(TOKEN_FILE, "w", encoding="utf-8") as token:
            token.write(creds.to_json())
        logs.append(f"[Thành công] Đã lưu thông tin xác thực vào {TOKEN_FILE.name}\n")

    service = build("gmail", "v1", credentials=creds)

    if log is not None:
        log["logs"] = logs
    return service

def _get_service(log = None):
    """Lấy hoặc khởi tạo Gmail Service (singleton)."""
    global _GMAIL_SERVICE
    if _GMAIL_SERVICE is None:
        _GMAIL_SERVICE = __get_gmail_service(log)
    return _GMAIL_SERVICE


def _decode_mime_words(header_val: Optional[str]) -> str:
    """Giải mã MIME encoded-word (RFC 2047) sang chuỗi Unicode tiếng Việt sạch."""
    if not header_val:
        return ""
    try:
        decoded_fragments = _decode_header(header_val)
        pieces = []
        for fragment, encoding in decoded_fragments:
            if isinstance(fragment, bytes):
                enc = encoding or "utf-8"
                try:
                    pieces.append(fragment.decode(enc, errors="replace"))
                except LookupError:
                    pieces.append(fragment.decode("utf-8", errors="replace"))
            else:
                pieces.append(str(fragment))
        return "".join(pieces)
    except Exception:
        return str(header_val)

def _parse_email_addresses(header_val: Optional[str]) -> List[str]:
    """Phân tách chuỗi header chứa danh sách email thành danh sách địa chỉ email sạch."""
    if not header_val:
        return []
    addresses = _getaddresses([header_val])
    parsed = []
    for _, addr in addresses:
        clean_addr = addr.strip().lower()
        if clean_addr:
            parsed.append(clean_addr)
    return parsed


# =========================================================================
# 1. TIỆN ÍCH CHUYỂN ĐỔI BẢNG HTML (Giống outlook_utils)
# =========================================================================
def convert_to_html_table(matrix: List[List[Any]], header: bool = True) -> str:
    """Chuyển ma trận dữ liệu (list of list) thành bảng HTML có border và padding.
    
    Args:
        matrix (list of list): Ma trận dữ liệu.
        header (bool): Hàng đầu tiên có phải là tiêu đề (<th>) không.

    Returns:
        str: Chuỗi HTML table.
    """
    html = ['<table border="1" cellspacing="0" cellpadding="6" style="border-collapse: collapse; font-family: Arial, sans-serif; font-size: 14px;">']
    
    for i, row in enumerate(matrix):
        if i == 0 and header:
            html.append('<tr style="background-color: #f2f2f2;">' + ''.join(f'<th style="border: 1px solid #ddd; padding: 8px; text-align: left;">{cell}</th>' for cell in row) + '</tr>')
        else:
            bg = '#fafafa' if i % 2 == 0 else '#ffffff'
            html.append(f'<tr style="background-color: {bg};">' + ''.join(f'<td style="border: 1px solid #ddd; padding: 8px;">{cell}</td>' for cell in row) + '</tr>')
    
    html.append('</table>')
    return '\n'.join(html)


# =========================================================================
# 2. LẤY THÔNG TIN PROFILE TÀI KHOẢN
# =========================================================================
def get_my_profile(**Args):
    if MODE == "smtp":
        get_my_profile_smtp(**Args)
    else:
        get_my_profile_google_api(**Args)        

def get_my_profile_google_api() -> Dict[str, Any]:
    """Lấy thông tin tài khoản Gmail hiện tại đã đăng nhập."""
    service = _get_service()
    profile = service.users().getProfile(userId="me").execute()
    return {
        "email": profile.get("emailAddress"),
        "messages_total": profile.get("messagesTotal"),
        "threads_total": profile.get("threadsTotal"),
        "history_id": profile.get("historyId"),
    }


def get_my_profile_smtp(email, app_password) -> Dict[str, Any]:
    """
    Lấy thông tin tài khoản Gmail hiện tại và kiểm tra kết nối SMTP.
    Tương đương get_my_profile() trong gmail_utils.py nhưng kiểm tra qua kết nối SMTP.
    
    Returns:
        Dict chứa email, máy chủ, cổng và trạng thái xác thực.
    """

    # Thử kết nối và login vào máy chủ SMTP để kiểm tra độ chính xác
    try:
        if SMTP_PORT == 465:
            with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=15) as smtp:
                smtp.login(email, app_password)
        else:
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=15) as smtp:
                if USE_TLS:
                    smtp.starttls()
                smtp.login(email, app_password)

        return {
            "email": email,
            "smtp_server": SMTP_SERVER,
            "smtp_port": SMTP_PORT,
            "status": "connected",
            "authenticated": True,
            "provider": "Gmail SMTP (smtplib)",
        }
    except smtplib.SMTPAuthenticationError as auth_err:
        raise PermissionError(
            f"Xác thực thất bại với email '{email}': {auth_err}."
            f"\nLưu ý: Gmail bắt buộc dùng Google App Password 16 ký tự."
        ) from auth_err
    except Exception as e:
        raise ConnectionError(f"Không thể kết nối tới máy chủ SMTP {SMTP_SERVER}:{SMTP_PORT} - {e}") from e


# =========================================================================
# 3. HÀM GỬI EMAIL (Hỗ trợ text, html, attachments, inline images)
# =========================================================================
def send_email(**Args):
    if "smtp" in MODE:
        return send_email_smtp(**Args)
    else:
        return send_email_google_api(**Args)    
        
def send_email_google_api(
    subject: str,
    body: str,
    to_emails: Union[str, List[str]],
    cc_emails: Optional[Union[str, List[str]]] = None,
    bcc_emails: Optional[Union[str, List[str]]] = None,
    attachments: Optional[List[str]] = None,
    inline_images: Optional[Dict[str, str]] = None,
    log: Optional[Dict[str, Any]] = None
) -> bool:
    """Gửi email qua Gmail API.
    
    Tương tự như send_email trong outlook_utils, hỗ trợ nội dung plain text / HTML,
    ảnh nội dòng (inline images với cid) và file đính kèm.
    
    Args:
        subject (str): Tiêu đề email.
        body (str): Nội dung email (Plain text hoặc chứa các thẻ HTML như <html>, <table>, <b>).
        to_emails (str hoặc list): Danh sách địa chỉ email người nhận (To).
        cc_emails (str hoặc list, optional): Danh sách địa chỉ CC.
        bcc_emails (str hoặc list, optional): Danh sách địa chỉ BCC.
        attachments (list of str, optional): Danh sách đường dẫn tệp tin đính kèm.
        inline_images (dict, optional): Dict dạng {'cid_name': 'path/to/image.png'}.
        
    Returns:
        bool: True nếu gửi thành công.
    """
    logs = []

    service = _get_service()

    from_email = "me"
    # Chuẩn hóa danh sách email
    if isinstance(to_emails, str):
        to_emails = [e.strip() for e in to_emails.split(",") if e.strip()]
    if isinstance(cc_emails, str):
        cc_emails = [e.strip() for e in cc_emails.split(",") if e.strip()]
    elif cc_emails is None:
        cc_emails = []
    if isinstance(bcc_emails, str):
        bcc_emails = [e.strip() for e in bcc_emails.split(",") if e.strip()]
    elif bcc_emails is None:
        bcc_emails = []

    attachments = attachments or []
    inline_images = inline_images or {}

    # Khởi tạo EmailMessage chuẩn
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["To"] = ", ".join(to_emails)
    if cc_emails:
        msg["Cc"] = ", ".join(cc_emails)
    if bcc_emails:
        msg["Bcc"] = ", ".join(bcc_emails)

    # Kiểm tra xem body có phải định dạng HTML không
    is_html = any(tag in body.lower() for tag in ["<html>", "<table", "<div", "<p>", "<br>", "<b>", "<span>"])

    if is_html:
        # Tạo bản text fallback đơn giản
        msg.set_content("Email này được định dạng bằng HTML. Vui lòng sử dụng ứng dụng xem thư hỗ trợ HTML.")
        msg.add_alternative(body, subtype="html")
        
        # Gắn ảnh nội dòng (inline images) vào phần HTML alternative
        for cid_name, img_path in inline_images.items():
            if not os.path.isfile(img_path):
                logs.append(f"⚠️ Ảnh không tồn tại: {img_path}")
                continue
            with open(img_path, "rb") as img_file:
                mime_type, _ = mimetypes.guess_type(img_path)
                mime_type = mime_type or "image/png"
                maintype, subtype = mime_type.split("/", 1)
                msg.get_payload()[-1].add_related(
                    img_file.read(),
                    maintype=maintype,
                    subtype=subtype,
                    cid=f"<{cid_name}>",
                )
    else:
        msg.set_content(body)

    # Gắn tệp đính kèm thông thường
    for filepath in attachments:
        if not os.path.isfile(filepath):
            logs.append(f"⚠️ File đính kèm không tồn tại: {filepath}")
            continue

        mime_type, _ = mimetypes.guess_type(filepath)
        mime_type = mime_type or "application/octet-stream"
        maintype, subtype = mime_type.split("/", 1)

        with open(filepath, "rb") as f:
            msg.add_attachment(
                f.read(),
                maintype=maintype,
                subtype=subtype,
                filename=os.path.basename(filepath),
            )

    # Mã hóa Base64 URL-safe cho Gmail API
    raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")

    sent_msg = (
        service.users()
        .messages()
        .send(userId=from_email, body={"raw": raw_message})
        .execute()
    )

    logs.append(f"✅ Email '{subject}' đã được gửi thành công! (ID: {sent_msg.get('id')})")
    if log is not None:
        log["logs"] = logs
    return True

def send_email_smtp(
    subject: Optional[str] = None,
    body: Optional[str] = None,
    to_emails: Optional[Union[str, List[str]]] = [],
    cc_emails: Optional[Union[str, List[str]]] = [],
    bcc_emails: Optional[Union[str, List[str]]] = [],
    attachments: Optional[List[str]] = None,
    inline_images: Optional[Dict[str, str]] = None,
    log: Optional[Dict[str, Any]] = None,
    # Thông tin xác thực email dùng phương thức smtp
    email: Optional[str] = None,
    app_password: Optional[str] = None,
    in_reply_to: Optional[str] = None,
    references: Optional[str] = None
) -> bool:
    """
    Gửi email qua giao thức Gmail SMTP.
    
    Hàm này được thiết kế tương thích hoàn toàn với:
    1. send_email(...) trong gmail_utils.py (thứ tự tham số: subject, body, to_emails, cc_emails, ...)
    2. send_email(...) trong gmail_service.py (các keyword: to, subject, body_text, body_html, cc, bcc)
    
    Args:
        subject (str): Tiêu đề thư.
        body (str, optional): Nội dung thư (Plain text hoặc HTML).
        to_emails / to (str hoặc list): Danh sách địa chỉ người nhận chính (To).
        cc_emails / cc (str hoặc list, optional): Danh sách địa chỉ CC.
        bcc_emails / bcc (str hoặc list, optional): Danh sách địa chỉ BCC.
        attachments (list of str, optional): Danh sách đường dẫn tệp đính kèm.
        inline_images (dict, optional): Dict ảnh nội dòng dạng {'cid_name': 'path/to/image.png'}.
        log (dict, optional): Dict để lưu trữ log chi tiết quá trình gửi.
        body_text (str, optional): Nội dung văn bản thuần (nếu truyền riêng biệt với body_html).
        body_html (str, optional): Nội dung HTML (nếu truyền riêng biệt).
        from_email (str, optional): Địa chỉ người gửi (ghi đè cấu hình mặc định).
        password (str, optional): Mật khẩu ứng dụng (ghi đè cấu hình mặc định).
        smtp_server (str, optional): Server SMTP (mặc định: smtp.gmail.com).
        smtp_port (int, optional): Cổng kết nối (587 hoặc 465).
        use_tls (bool, optional): Sử dụng STARTTLS (mặc định: True cho port 587).

    Returns:
        bool: True nếu gửi thành công.
    """
    logs = []

    sender_email = email
    attachments = attachments or []
    inline_images = inline_images or {}

    # 5. Khởi tạo đối tượng EmailMessage chuẩn
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = ", ".join(to_emails)
    if cc_emails:
        msg["Cc"] = ", ".join(cc_emails)
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
    if references:
        msg["References"] = references
    # Ghi chú: Header Bcc không đưa vào msg["Bcc"] để tránh lộ địa chỉ trong email headers,
    # nhưng bcc_list vẫn được đưa vào danh sách phong bì gửi (all_envelope_recipients).

    # 6. Gắn nội dung Body & Inline Images
    if "<html>" in body:
        msg.add_alternative(body, subtype="html")

        # Gắn ảnh nội dòng (inline images với Content-ID)
        for cid_name, img_path in inline_images.items():
            path_obj = Path(img_path)
            if not path_obj.is_file():
                logs.append(f"⚠️ Ảnh nội dòng không tồn tại: {img_path}")
                continue

            ctype, _ = mimetypes.guess_type(str(path_obj))
            ctype = ctype or "image/png"
            maintype, subtype = ctype.split("/", 1)

            with open(path_obj, "rb") as img_file:
                # Gắn vào payload HTML alternative (payload cuối)
                msg.get_payload()[-1].add_related(
                    img_file.read(),
                    maintype=maintype,
                    subtype=subtype,
                    cid=f"<{cid_name.strip('<>')}>",
                )
    else:
        msg.set_content(body)

    # 7. Gắn tệp đính kèm (Attachments)
    for filepath in attachments:
        path_obj = Path(filepath)
        if not path_obj.is_file():
            logs.append(f"⚠️ Tệp đính kèm không tồn tại: {filepath}")
            continue

        ctype, encoding = mimetypes.guess_type(str(path_obj))
        if ctype is None or encoding is not None:
            ctype = "application/octet-stream"
        maintype, subtype = ctype.split("/", 1)

        with open(path_obj, "rb") as f:
            msg.add_attachment(
                f.read(),
                maintype=maintype,
                subtype=subtype,
                filename=path_obj.name,
            )

    # 8. Tập hợp tất cả địa chỉ nhận thư thực tế cho phong bì SMTP (To + CC + BCC)
    all_envelope_recipients = list(dict.fromkeys(to_emails + cc_emails + bcc_emails))

    # 9. Thực hiện kết nối và gửi qua SMTP
    logs.append(f"Đang kết nối SMTP {SMTP_SERVER}:{SMTP_PORT}...")

    if SMTP_PORT == 465:
        # Chế độ bảo mật SSL trực tiếp
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=30) as smtp:
            smtp.login(sender_email, app_password)
            smtp.send_message(msg, from_addr=sender_email, to_addrs=all_envelope_recipients)
    else:
        # Chế độ chuẩn STARTTLS (cổng 587)
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30) as smtp:
            if USE_TLS:
                smtp.starttls()
            smtp.login(sender_email, app_password)
            smtp.send_message(msg, from_addr=sender_email, to_addrs=all_envelope_recipients)

    success_msg = f"✅ Email '{subject}' đã được gửi thành công qua SMTP tới: {', '.join(to_emails)}"
    logs.append(success_msg)

    if log is not None:
        log["logs"] = logs

    return True


# =========================================================================
# 4. HÀM ĐỌC EMAIL (Tương tự read_outlook_mails trong outlook_utils)
# =========================================================================
def read_mails(
    folder: str = "INBOX",
    filters: Optional[Dict[str, Any]] = None,
    download_attachments: bool = False,
    save_path: str = ".",
    accepted_attachment_extensions: Optional[List[str]] = None,
    download_image: bool = False,
) -> List[Dict[str, Any]]:
    """Đọc danh sách email từ Gmail với bộ lọc và tùy chọn tải tệp đính kèm.
    
    Args:
        folder (str): Tên nhãn thư mục (Mặc định: 'INBOX', có thể là 'SENT', 'SPAM', 'TRASH', hoặc label bất kỳ).
        filters (dict, optional): Bộ lọc giống như outlook_utils:
            - 'top': Số lượng thư tối đa cần đọc (mặc định 5).
            - 'unread': Lọc trạng thái (True: chỉ chưa đọc, False: chỉ đã đọc).
            - 'senders': List[str] các email người gửi cần lọc (chứa substring).
            - 'subject': str từ khóa cần xuất hiện trong tiêu đề.
            - 'receivers': List[str] email người nhận (To, CC, BCC).
            - 'q': Cú pháp truy vấn Gmail trực tiếp (nếu có).
        download_attachments (bool): Tải tệp đính kèm về máy nếu True.
        save_path (str): Thư mục lưu tệp đính kèm.
        accepted_attachment_extensions (list of str): Ví dụ ['.pdf', '.xlsx'].
        download_image (bool): Mặc định False (không tải ảnh đuôi .png, .jpg, .gif để tránh ảnh chữ ký).

    Returns:
        list of dict: Danh sách thư thỏa mãn điều kiện lọc.
    """
    logs = []
    service = _get_service()
    filters = filters or {}
    top_n = filters.get("top", 5)

    # Xây dựng câu truy vấn query Gmail API để tối ưu tốc độ mạng
    query_parts = []
    if folder:
        query_parts.append(f"label:{folder}")
    if filters.get("unread") is True:
        query_parts.append("is:unread")
    elif filters.get("unread") is False:
        query_parts.append("is:read")
    if "subject" in filters:
        query_parts.append(f'subject:"{filters["subject"]}"')
    if "q" in filters:
        query_parts.append(filters["q"])

    gmail_query = " ".join(query_parts)

    # Lấy danh sách ID thư từ Gmail API
    response = (
        service.users()
        .messages()
        .list(userId="me", q=gmail_query, maxResults=min(top_n * 3, 50))
        .execute()
    )
    message_items = response.get("messages", [])

    outputs = []
    count = 0

    for item in message_items:
        msg_id = item["id"]
        try:
            full_msg = (
                service.users()
                .messages()
                .get(userId="me", id=msg_id, format="full")
                .execute()
            )
        except Exception as e:
            logs.append(f"⚠️ Không thể đọc message ID {msg_id}: {e}")
            continue

        payload = full_msg.get("payload", {})
        headers = {h["name"].lower(): h["value"] for h in payload.get("headers", [])}
        labels = full_msg.get("labelIds", [])
        is_unread = "UNREAD" in labels

        # Người gửi
        from_header = headers.get("from", "")
        # Phân tích email người gửi từ định dạng "Name <email@domain.com>"
        sender_email = email.utils.parseaddr(from_header)[1].lower() if from_header else ""

        # Người nhận
        def parse_email_list(header_val):
            if not header_val:
                return []
            return [email.utils.parseaddr(addr.strip())[1].lower() for addr in header_val.split(",") if addr.strip()]

        to_emails = parse_email_list(headers.get("to", ""))
        cc_emails = parse_email_list(headers.get("cc", ""))
        bcc_emails = parse_email_list(headers.get("bcc", ""))
        all_receivers = to_emails + cc_emails + bcc_emails

        subject = headers.get("subject", "")

        # Thời gian nhận thư
        internal_date_ms = full_msg.get("internalDate")
        if internal_date_ms:
            received_time = datetime.fromtimestamp(int(internal_date_ms) / 1000)
        else:
            received_time = datetime.now()

        # Bóc tách nội dung Body và Attachments
        body_plain = ""
        body_html = ""
        attachments_meta = []

        def extract_parts(parts):
            nonlocal body_plain, body_html, attachments_meta
            for part in parts:
                mime_type = part.get("mimeType", "")
                filename = part.get("filename", "")
                body_info = part.get("body", {})
                data = body_info.get("data")
                att_id = body_info.get("attachmentId")

                if filename:
                    attachments_meta.append({
                        "filename": filename,
                        "mimeType": mime_type,
                        "size": body_info.get("size", 0),
                        "attachmentId": att_id,
                    })
                elif mime_type == "text/plain" and data:
                    text = base64.urlsafe_b64decode(data.encode("utf-8")).decode("utf-8", errors="replace")
                    body_plain += text
                elif mime_type == "text/html" and data:
                    html_text = base64.urlsafe_b64decode(data.encode("utf-8")).decode("utf-8", errors="replace")
                    body_html += html_text

                if "parts" in part:
                    extract_parts(part["parts"])

        if "parts" in payload:
            extract_parts(payload["parts"])
        else:
            single_data = payload.get("body", {}).get("data")
            single_mime = payload.get("mimeType", "")
            if single_data:
                decoded = base64.urlsafe_b64decode(single_data.encode("utf-8")).decode("utf-8", errors="replace")
                if single_mime == "text/html":
                    body_html = decoded
                else:
                    body_plain = decoded

        # Áp dụng bộ lọc in-memory (đảm bảo khớp chính xác như outlook_utils)
        if "unread" in filters and is_unread != filters["unread"]:
            continue

        if "senders" in filters:
            senders_filter = [s.lower() for s in filters["senders"]]
            if not any(s in sender_email or s in from_header.lower() for s in senders_filter):
                continue

        if "subject" in filters:
            if filters["subject"].lower() not in subject.lower():
                continue

        if "receivers" in filters:
            receivers_filter = [r.lower() for r in filters["receivers"]]
            if not any(any(r in rec for rec in all_receivers) for r in receivers_filter):
                continue

        # Tải tệp đính kèm nếu download_attachments = True
        downloaded_files = []
        if download_attachments and attachments_meta:
            os.makedirs(save_path, exist_ok=True)
            for att in attachments_meta:
                fname = att["filename"]
                ext = Path(fname).suffix.lower()

                # Kiểm tra lọc extension
                if accepted_attachment_extensions:
                    if ext not in [e.lower() for e in accepted_attachment_extensions]:
                        continue

                # Kiểm tra lọc ảnh
                if not download_image and ext in [".png", ".gif", ".jpg", ".jpeg"]:
                    continue

                if att["attachmentId"]:
                    try:
                        att_res = (
                            service.users()
                            .messages()
                            .attachments()
                            .get(userId="me", messageId=msg_id, id=att["attachmentId"])
                            .execute()
                        )
                        att_data = base64.urlsafe_b64decode(att_res["data"].encode("utf-8"))
                        target_file = Path(save_path) / fname
                        
                        # Xử lý trùng tên file: thêm số vào sau
                        file_counter = 1
                        while target_file.exists():
                            target_file = Path(save_path) / f"{target_file.stem}_{file_counter}{target_file.suffix}"
                            file_counter += 1

                        with open(target_file, "wb") as f_out:
                            f_out.write(att_data)
                        downloaded_files.append(str(target_file.resolve()))
                    except Exception as err:
                        logs.append(f"⚠️ Lỗi tải file đính kèm {fname}: {err}")

        # Chuẩn hóa cấu trúc kết quả trả về tương tự outlook_utils
        effective_body = body_plain if body_plain else remove_html_tags(body_html)
        effective_body = clean_gmail_ui_artifacts(effective_body)
        outputs.append({
            "id": msg_id,
            "subject": subject,
            "from": from_header,
            "sender_email": sender_email,
            "to": to_emails,
            "cc": cc_emails,
            "bcc": bcc_emails,
            "unread": is_unread,
            "body": effective_body,
            "html_body": body_html,
            "received_time": received_time,
            "attachments": [a["filename"] for a in attachments_meta],
            "downloaded_files": downloaded_files,
        })

        count += 1
        if count >= top_n:
            break

    return outputs

def read_mails_imap(
    folder_path: str = "INBOX",
    filters: Optional[Dict[str, Any]] = None,
    download_attachments: bool = False,
    save_path: str = ".",
    accepted_attachment_extensions: Optional[List[str]] = None,
    download_image: bool = False,
    # Tùy chọn override thông tin xác thực
    # Thông tin xác thực email dùng phương thức smtp
    email: Optional[str] = None,
    app_password: Optional[str] = None,
    log: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Đọc danh sách email từ Gmail với bộ lọc và tùy chọn tải tệp đính kèm.
    Sử dụng giao thức IMAP với cùng thông tin tài khoản Email + App Password của SMTP.
    
    Tương thích 100% với giao diện và kết quả trả về của read_gmail_mails trong gmail_utils.py.
    
    Args:
        folder (str): Tên thư mục hoặc nhãn (Mặc định: 'INBOX', có thể là '[Gmail]/Sent Mail', '[Gmail]/Spam', ...).
        filters (dict, optional): Bộ lọc thư:
            - 'top': Số lượng thư tối đa cần lấy (mặc định: 5, lấy từ thư mới nhất).
            - 'unread': Lọc trạng thái (True: chỉ thư chưa đọc, False: chỉ thư đã đọc).
            - 'senders': List[str] các email người gửi cần lọc (chứa substring).
            - 'subject': str từ khóa cần xuất hiện trong tiêu đề.
            - 'receivers': List[str] email người nhận (To, CC, BCC).
            - 'q': Từ khóa tìm kiếm phụ trong tiêu đề hoặc nội dung.
        download_attachments (bool): Tải tệp đính kèm về máy nếu True (mặc định: False).
        save_path (str): Thư mục lưu tệp đính kèm tải về.
        accepted_attachment_extensions (list of str, optional): Lọc đuôi tệp chấp nhận (ví dụ: ['.pdf', '.xlsx']).
        download_image (bool): Tải ảnh đính kèm nếu True (mặc định False để tránh tải icon chữ ký).
        email (str, optional): Địa chỉ Gmail (ghi đè cấu hình mặc định).
        app_password (str, optional): Mật khẩu ứng dụng (ghi đè cấu hình mặc định).
        imap_server (str, optional): Máy chủ IMAP (mặc định: imap.gmail.com).
        imap_port (int, optional): Cổng IMAP (mặc định: 993).
        log (dict, optional): Dict để lưu log chi tiết quá trình đọc.

    Returns:
        List[Dict[str, Any]]: Danh sách các thư thỏa mãn bộ lọc.
    """
    logs = []
    filters = filters or {}
    top_n = filters.get("top", 5)

    logs.append(f"Đang kết nối IMAP {IMAP_SERVER}:{IMAP_PORT} cho tài khoản {email}...")

    outputs: List[Dict[str, Any]] = []

    try:
        with imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT, timeout=30) as imap_client:
            imap_client.login(email, app_password)

            # Chọn thư mục / mailbox (readonly=True để không tự động sửa đổi cờ thư khi duyệt)
            target_mailbox = f'"{folder_path}"' if (" " in folder_path or "/" in folder_path) and not folder_path.startswith('"') else folder_path
            status, _ = imap_client.select(target_mailbox, readonly=True)
            if status != "OK":
                status, _ = imap_client.select(folder_path, readonly=True)
                if status != "OK":
                    raise ValueError(f"Không thể mở thư mục '{folder_path}' trong hòm thư Gmail.")

            # Xác định tiêu chí tìm kiếm IMAP
            unread_filter = filters.get("unread")
            if unread_filter is True:
                search_query = "UNSEEN"
            elif unread_filter is False:
                search_query = "SEEN"
            else:
                search_query = "ALL"

            status, data = imap_client.uid("SEARCH", None, search_query)
            if status != "OK" or not data or not data[0]:
                logs.append("Không tìm thấy email nào khớp với tiêu chí tìm kiếm ban đầu.")
                if log is not None:
                    log["logs"] = logs
                return []

            uid_list = data[0].split()
            # Đảo ngược danh sách để duyệt từ thư mới nhất trở về trước
            uid_list.reverse()

            count = 0
            # Giới hạn số lượng UID quét tối đa để đảm bảo hiệu năng
            max_scan = min(len(uid_list), max(top_n * 10, 50))

            for uid in uid_list[:max_scan]:
                # Quan trọng: Sử dụng BODY.PEEK[] để việc đọc thư KHÔNG làm thay đổi cờ \Seen (không tự động đánh dấu đã đọc)
                fetch_status, fetch_data = imap_client.uid("FETCH", uid, "(BODY.PEEK[] FLAGS)")
                if fetch_status != "OK" or not fetch_data:
                    continue

                raw_email_bytes = None
                flags_text = ""
                for part_item in fetch_data:
                    if isinstance(part_item, tuple) and len(part_item) >= 2:
                        flags_text = part_item[0].decode("utf-8", errors="replace")
                        raw_email_bytes = part_item[1]
                        break

                if not raw_email_bytes:
                    continue

                msg = _message_from_bytes(raw_email_bytes)
                is_unread = "\\Seen" not in flags_text

                # Kiểm tra lọc unread in-memory
                if unread_filter is not None and is_unread != unread_filter:
                    continue

                # Trích xuất Header
                raw_subject = msg.get("Subject", "")
                subject = _decode_mime_words(raw_subject)
                message_id = msg.get("Message-ID", "") or msg.get("Message-Id", "")

                raw_from = msg.get("From", "")
                from_header = _decode_mime_words(raw_from)
                sender_email = _parseaddr(from_header)[1].lower() if from_header else ""

                to_emails = _parse_email_addresses(_decode_mime_words(msg.get("To", "")))
                cc_emails = _parse_email_addresses(_decode_mime_words(msg.get("Cc", "")))
                bcc_emails = _parse_email_addresses(_decode_mime_words(msg.get("Bcc", "")))
                all_receivers = to_emails + cc_emails + bcc_emails

                # Thời gian gửi / nhận
                date_hdr = msg.get("Date")
                received_time = None
                if date_hdr:
                    try:
                        received_time = _parsedate_to_datetime(date_hdr)
                    except Exception:
                        pass
                if received_time is None:
                    received_time = datetime.now()

                # Kiểm tra lọc theo người gửi (senders)
                if "senders" in filters:
                    senders_filter = [s.lower() for s in filters["senders"]]
                    if not any(s in sender_email or s in from_header.lower() for s in senders_filter):
                        continue

                # Kiểm tra lọc theo tiêu đề (subject)
                if "subject" in filters:
                    if str(filters["subject"]).lower() not in subject.lower():
                        continue

                # Kiểm tra lọc theo người nhận (receivers)
                if "receivers" in filters:
                    receivers_filter = [r.lower() for r in filters["receivers"]]
                    if not any(any(r in rec for rec in all_receivers) for r in receivers_filter):
                        continue

                # Bóc tách nội dung Body và Attachments
                body_plain = ""
                body_html = ""
                attachments_meta = []

                if msg.is_multipart():
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        content_disp = str(part.get("Content-Disposition", "")).lower()
                        raw_fn = part.get_filename()

                        if raw_fn:
                            fn = _decode_mime_words(raw_fn)
                            fn = Path(fn).name  # Làm sạch để tránh path traversal
                            payload_data = part.get_payload(decode=True)
                            if payload_data is not None:
                                attachments_meta.append({
                                    "filename": fn,
                                    "data": payload_data,
                                    "content_type": content_type,
                                })
                        elif "attachment" in content_disp:
                            fn = f"attachment_{len(attachments_meta) + 1}"
                            payload_data = part.get_payload(decode=True)
                            if payload_data is not None:
                                attachments_meta.append({
                                    "filename": fn,
                                    "data": payload_data,
                                    "content_type": content_type,
                                })
                        elif content_type == "text/plain" and "attachment" not in content_disp:
                            charset = part.get_content_charset() or "utf-8"
                            payload_data = part.get_payload(decode=True)
                            if payload_data:
                                try:
                                    body_plain += payload_data.decode(charset, errors="replace")
                                except LookupError:
                                    body_plain += payload_data.decode("utf-8", errors="replace")
                        elif content_type == "text/html" and "attachment" not in content_disp:
                            charset = part.get_content_charset() or "utf-8"
                            payload_data = part.get_payload(decode=True)
                            if payload_data:
                                try:
                                    body_html += payload_data.decode(charset, errors="replace")
                                except LookupError:
                                    body_html += payload_data.decode("utf-8", errors="replace")
                else:
                    content_type = msg.get_content_type()
                    charset = msg.get_content_charset() or "utf-8"
                    payload_data = msg.get_payload(decode=True)
                    if payload_data:
                        try:
                            text_decoded = payload_data.decode(charset, errors="replace")
                        except LookupError:
                            text_decoded = payload_data.decode("utf-8", errors="replace")
                        if content_type == "text/html":
                            body_html = text_decoded
                        else:
                            body_plain = text_decoded

                # Lọc bổ sung theo query 'q' (nếu có)
                if "q" in filters and filters["q"]:
                    q_lower = str(filters["q"]).lower()
                    if q_lower not in subject.lower() and q_lower not in body_plain.lower() and q_lower not in sender_email:
                        continue

                # Xử lý tải tệp đính kèm nếu download_attachments = True
                downloaded_files = []
                if download_attachments and attachments_meta:
                    os.makedirs(save_path, exist_ok=True)
                    for att in attachments_meta:
                        fname = att["filename"]
                        ext = Path(fname).suffix.lower()

                        if accepted_attachment_extensions:
                            if ext not in [e.lower() for e in accepted_attachment_extensions]:
                                continue

                        if not download_image and ext in [".png", ".gif", ".jpg", ".jpeg", ".bmp", ".webp"]:
                            continue

                        target_file = Path(save_path) / fname
                        file_counter = 1
                        while target_file.exists():
                            target_file = Path(save_path) / f"{target_file.stem}_{file_counter}{target_file.suffix}"
                            file_counter += 1

                        try:
                            with open(target_file, "wb") as f_out:
                                f_out.write(att["data"])
                            downloaded_files.append(str(target_file.resolve()))
                        except Exception as err:
                            logs.append(f"⚠️ Lỗi lưu file đính kèm '{fname}': {err}")

                uid_str = uid.decode("utf-8") if isinstance(uid, bytes) else str(uid)
                effective_body = body_plain if body_plain else remove_html_tags(body_html)
                effective_body = clean_gmail_ui_artifacts(effective_body)
                outputs.append({
                    "id": uid_str,
                    "message_id": message_id,
                    "subject": subject,
                    "from": from_header,
                    "sender_email": sender_email,
                    "to": to_emails,
                    "cc": cc_emails,
                    "bcc": bcc_emails,
                    "unread": is_unread,
                    "body": effective_body,
                    "html_body": body_html,
                    "received_time": received_time,
                    "attachments": [a["filename"] for a in attachments_meta],
                    "downloaded_files": downloaded_files,
                })

                count += 1
                if count >= top_n:
                    break

    except Exception as e:
        logs.append(f"❌ Lỗi khi đọc email qua IMAP: {e}")
        if log is not None:
            log["logs"] = logs
        raise e

    if log is not None:
        log["logs"] = logs

    return outputs


# =========================================================================
# 5. TIỆN ÍCH ĐÁNH DẤU ĐÃ ĐỌC / CHƯA ĐỌC
# =========================================================================
def mark_as_read_imap(
    uid: Union[str, int],
    folder_path: str = "INBOX",
    email: Optional[str] = None,
    app_password: Optional[str] = None,
    log: Optional[Dict[str, Any]] = None,
) -> bool:
    """Đánh dấu một email là ĐÃ ĐỌC trên IMAP bằng cách gán cờ \\Seen."""
    logs = []
    try:
        with imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT, timeout=30) as imap_client:
            imap_client.login(email, app_password)
            target_mailbox = f'"{folder_path}"' if (" " in folder_path or "/" in folder_path) and not folder_path.startswith('"') else folder_path
            status, _ = imap_client.select(target_mailbox, readonly=False)
            if status != "OK":
                status, _ = imap_client.select(folder_path, readonly=False)
                if status != "OK":
                    raise ValueError(f"Không thể mở thư mục '{folder_path}'")
            res, _ = imap_client.uid("STORE", str(uid), "+FLAGS", "(\\Seen)")
            logs.append(f"✅ Đã đánh dấu email UID {uid} là ĐÃ ĐỌC.")
            if log is not None:
                log["logs"] = logs
            return res == "OK"
    except Exception as e:
        logs.append(f"❌ Lỗi khi đánh dấu đã đọc email UID {uid}: {e}")
        if log is not None:
            log["logs"] = logs
        raise e

def mark_as_unread_imap(
    uid: Union[str, int],
    folder_path: str = "INBOX",
    email: Optional[str] = None,
    app_password: Optional[str] = None,
    log: Optional[Dict[str, Any]] = None,
) -> bool:
    """Đánh dấu một email là CHƯA ĐỌC trên IMAP bằng cách gỡ cờ \\Seen."""
    logs = []
    try:
        with imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT, timeout=30) as imap_client:
            imap_client.login(email, app_password)
            target_mailbox = f'"{folder_path}"' if (" " in folder_path or "/" in folder_path) and not folder_path.startswith('"') else folder_path
            status, _ = imap_client.select(target_mailbox, readonly=False)
            if status != "OK":
                status, _ = imap_client.select(folder_path, readonly=False)
                if status != "OK":
                    raise ValueError(f"Không thể mở thư mục '{folder_path}'")
            res, _ = imap_client.uid("STORE", str(uid), "-FLAGS", "(\\Seen)")
            logs.append(f"✅ Đã đánh dấu email UID {uid} là CHƯA ĐỌC.")
            if log is not None:
                log["logs"] = logs
            return res == "OK"
    except Exception as e:
        logs.append(f"❌ Lỗi khi đánh dấu chưa đọc email UID {uid}: {e}")
        if log is not None:
            log["logs"] = logs
        raise e

def mark_as_read(message_id: str, **kwargs) -> bool:
    """Đánh dấu một email là ĐÃ ĐỌC (tự động chọn IMAP hoặc Google API)."""
    if "smtp" in MODE or kwargs.get("mode") == "imap" or "email" in kwargs:
        return mark_as_read_imap(
            uid=message_id,
            folder_path=kwargs.get("folder_path", "INBOX"),
            email=kwargs.get("email"),
            app_password=kwargs.get("app_password"),
            log=kwargs.get("log")
        )
    service = _get_service()
    service.users().messages().modify(userId="me", id=message_id, body={"removeLabelIds": ["UNREAD"]}).execute()
    return True

def mark_as_unread(message_id: str, **kwargs) -> bool:
    """Đánh dấu một email là CHƯA ĐỌC (tự động chọn IMAP hoặc Google API)."""
    if "smtp" in MODE or kwargs.get("mode") == "imap" or "email" in kwargs:
        return mark_as_unread_imap(
            uid=message_id,
            folder_path=kwargs.get("folder_path", "INBOX"),
            email=kwargs.get("email"),
            app_password=kwargs.get("app_password"),
            log=kwargs.get("log")
        )
    service = _get_service()
    service.users().messages().modify(userId="me", id=message_id, body={"addLabelIds": ["UNREAD"]}).execute()
    return True


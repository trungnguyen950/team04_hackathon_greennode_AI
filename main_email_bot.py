import os
import sys
import time
import argparse
from datetime import datetime

# Đảm bảo mã hóa UTF-8 trên Windows console để hiển thị tiếng Việt và biểu tượng đẹp mắt
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import config
from utils import gmail_utils
from utils.log_manager import enable_stdout_interception
import email_ai_processor

# Bật tính năng tự động chuyển log sang Web Log Viewer
enable_stdout_interception()

# Cấu hình chế độ SMTP/IMAP cho gmail_utils
gmail_utils.load_configs({"mode": "smtp/imap"})


def print_banner():
    print("\n" + "=" * 75)
    print(" 🤖 HỆ THỐNG TỰ ĐỘNG THEO DÕI EMAIL & PHẢN HỒI BẰNG AI MULTI-AGENT")
    print("=" * 75)
    print(f" • Tài khoản hòm thư : {config.EMAIL_ACCOUNT}")
    print(f" • Máy chủ IMAP/SMTP : {config.IMAP_SERVER}:{config.IMAP_PORT} / {config.SMTP_SERVER}:{config.SMTP_PORT}")
    print(f" • Thư mục quét      : {config.MAIL_FOLDER}")
    print(f" • Chu kỳ kiểm tra   : {config.POLL_INTERVAL_SECONDS} giây/lần")
    print(" • Agent AI          : IT Support")
    print("=" * 75)
    print(" Nhấn Ctrl + C bất cứ lúc nào để dừng chương trình an toàn.\n")


def is_ignored_sender(sender_email: str) -> bool:
    """Kiểm tra xem địa chỉ người gửi có thuộc danh sách bỏ qua hay không."""
    if not sender_email:
        return True
    
    clean_sender = sender_email.lower().strip()
    
    # Bỏ qua chính tài khoản của bot để tránh vòng lặp vô tận (Infinite Loop)
    if clean_sender == config.EMAIL_ACCOUNT.lower():
        return True
        
    # Bỏ qua các địa chỉ no-reply hoặc daemon
    for ignored in config.IGNORE_SENDERS:
        if ignored in clean_sender:
            return True
            
    return False


def process_single_email(mail: dict, dry_run: bool = False) -> bool:
    """
    Xử lý một email cụ thể:
    1. Trích xuất thông tin
    2. Gửi cho AI LangChain xử lý
    3. Gửi email phản hồi lại cho người gửi
    4. Đánh dấu email gốc là ĐÃ ĐỌC
    """
    uid = mail.get("id")
    subject = mail.get("subject", "(Không có tiêu đề)")
    from_str = mail.get("from", "")
    sender_email = mail.get("sender_email", "")
    body = mail.get("body", "")
    message_id = mail.get("message_id", "")
    attachments = mail.get("attachments", [])

    print("-" * 75)
    print(f"📩 [PHÁT HIỆN THƯ MỚI] (UID: {uid})")
    print(f"   • Người gửi  : {from_str}")
    print(f"   • Email      : {sender_email}")
    print(f"   • Tiêu đề    : {subject}")
    print(f"   • Tệp đính kèm: {', '.join(attachments) if attachments else 'Không có'}")
    print(f"   • Đoạn trích : {body[:100].strip()}..." if len(body) > 100 else f"   • Nội dung: {body.strip()}")

    # 1. Kiểm tra bộ lọc người gửi
    if is_ignored_sender(sender_email):
        print(f"⏭️ [BỎ QUA]: Email từ '{sender_email}' thuộc danh sách loại trừ (tự động/no-reply).")
        # Đánh dấu đã đọc để không kiểm tra lại
        try:
            gmail_utils.mark_as_read_imap(
                uid=uid,
                folder_path=config.MAIL_FOLDER,
                email=config.EMAIL_ACCOUNT,
                app_password=config.EMAIL_APP_PASSWORD
            )
        except Exception:
            pass
        return False

    # 2. Xử lý qua AI LangChain
    print(f"\n🧠 [AI PROCESSING]: Đang phân tích email bằng LangChain Multi-Agent...")
    try:
        start_ai_time = time.time()
        ai_result = email_ai_processor.process_incoming_email(
            sender_name=from_str,
            sender_email=sender_email,
            subject=subject,
            body=body,
            attachments=attachments
        )
        elapsed = time.time() - start_ai_time
        print(f"✅ [AI PROCESSING HOÀN TẤT] Thời gian: {elapsed:.2f}s | Agent: {ai_result['assigned_agent'].upper()}")
    except Exception as ai_err:
        print(f"❌ [LỖI AI]: Không thể xử lý email qua AI: {ai_err}")
        return False

    reply_subject = ai_result["reply_subject"]
    reply_body_plain = ai_result["reply_body_plain"]
    reply_body_html = ai_result["reply_body_html"]

    # 3. Gửi phản hồi qua SMTP (hoặc Dry-run)
    if dry_run:
        print(f"\n🔍 [DRY RUN - KHÔNG GỬI THẬT]:")
        print(f"   • Gửi tới: {sender_email}")
        print(f"   • Tiêu đề: {reply_subject}")
        print(f"   • Nội dung phản hồi (Plain text trích đoạn):\n{reply_body_plain[:250]}...")
        return True

    print(f"\n📤 [SENDING EMAIL]: Đang gửi email phản hồi tới '{sender_email}'...")
    try:
        send_success = gmail_utils.send_email_smtp(
            subject=reply_subject,
            body=reply_body_html,  # Gửi định dạng HTML chuyên nghiệp
            to_emails=[sender_email],
            email=config.EMAIL_ACCOUNT,
            app_password=config.EMAIL_APP_PASSWORD,
            in_reply_to=message_id,
            references=message_id
        )
        if send_success:
            print(f"✅ [GỬI THÀNH CÔNG] Đã gửi phản hồi '{reply_subject}' tới: {sender_email}")
        else:
            print(f"⚠️ [CẢNH BÁO] Không nhận được phản hồi thành công từ hàm gửi email.")
    except Exception as send_err:
        print(f"❌ [LỖI GỬI EMAIL]: Thất bại khi gửi email tới '{sender_email}': {send_err}")
        return False

    # 4. Đánh dấu thư gốc là ĐÃ ĐỌC (Seen) trên IMAP
    if config.AUTO_MARK_AS_READ:
        try:
            gmail_utils.mark_as_read_imap(
                uid=uid,
                folder_path=config.MAIL_FOLDER,
                email=config.EMAIL_ACCOUNT,
                app_password=config.EMAIL_APP_PASSWORD
            )
            print(f"📌 [ĐÃ ĐÁNH DẤU]: Đã đổi trạng thái thư UID {uid} thành 'ĐÃ ĐỌC'.")
        except Exception as mark_err:
            print(f"⚠️ [CẢNH BÁO]: Không thể đánh dấu thư là đã đọc: {mark_err}")

    print("-" * 75 + "\n")
    return True


def run_check_cycle(dry_run: bool = False) -> int:
    """Thực hiện một chu kỳ kiểm tra hộp thư đến."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now_str}] 🔍 Đang quét hòm thư '{config.MAIL_FOLDER}' tìm thư chưa đọc...")

    try:
        unread_mails = gmail_utils.read_mails_imap(
            folder_path=config.MAIL_FOLDER,
            filters={"unread": True, "top": config.TOP_UNREAD_LIMIT},
            email=config.EMAIL_ACCOUNT,
            app_password=config.EMAIL_APP_PASSWORD
        )
    except Exception as e:
        print(f"❌ [LỖI KẾT NỐI IMAP]: {e}")
        return 0

    if not unread_mails:
        print(f"    -> Hộp thư sạch sẽ! Không có thư mới chưa đọc.")
        return 0

    print(f"    -> Tìm thấy {len(unread_mails)} thư mới cần xử lý.")
    processed_count = 0

    for mail in unread_mails:
        try:
            success = process_single_email(mail, dry_run=dry_run)
            if success:
                processed_count += 1
        except Exception as item_err:
            print(f"❌ [LỖI BẤT NGỜ] Khi xử lý thư UID {mail.get('id')}: {item_err}")
            continue

    return processed_count


def main():
    parser = argparse.ArgumentParser(description="Chương trình AI tự động kiểm tra và phản hồi email")
    parser.add_argument("--once", action="store_true", help="Chỉ kiểm tra 1 lần duy nhất rồi thoát (thích hợp để test)")
    parser.add_argument("--interval", type=int, default=config.POLL_INTERVAL_SECONDS, help="Khoảng thời gian giữa các lần quét (giây)")
    parser.add_argument("--dry-run", action="store_true", help="Chạy thử nghiệm AI tạo phản hồi mà không gửi email thật và không đánh dấu đã đọc")
    args = parser.parse_args()

    config.POLL_INTERVAL_SECONDS = args.interval

    print_banner()

    if args.dry_run:
        print("⚠️ CHẾ ĐỘ DRY-RUN ĐANG BẬT: Email phản hồi sẽ chỉ hiển thị trên màn hình, không gửi đi thật.\n")

    if args.once:
        print("[CHẾ ĐỘ KIỂM TRA 1 LẦN (--once)] Bắt đầu quét...")
        count = run_check_cycle(dry_run=args.dry_run)
        print(f"\n[KẾT THÚC] Đã xử lý {count} email.")
        return

    # Vòng lặp định kỳ (Daemon Loop)
    print(f"[CHẾ ĐỘ TỰ ĐỘNG ĐỊNH KỲ] Quét mỗi {config.POLL_INTERVAL_SECONDS} giây một lần...\n")
    try:
        cycle = 1
        while True:
            print(f"--- [CHU KỲ #{cycle}] ---")
            run_check_cycle(dry_run=args.dry_run)
            cycle += 1
            print(f"⏳ Nghỉ {config.POLL_INTERVAL_SECONDS} giây trước lần quét tiếp theo...\n")
            time.sleep(config.POLL_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("\n\n🛑 [DỪNG HỆ THỐNG]: Người dùng đã nhấn Ctrl + C. Hệ thống dừng an toàn.")
    except Exception as e:
        print(f"\n💥 [LỖI KHÔNG MONG MUỐN]: {e}")


if __name__ == "__main__":
    main()


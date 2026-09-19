import os
import sys
import time
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Set

BASE_DIR = Path(__file__).parent.parent.resolve()
LOGS_DIR = BASE_DIR / "logs"
LOG_FILE = LOGS_DIR / "app.log"

# Đảm bảo thư mục logs luôn tồn tại
LOGS_DIR.mkdir(parents=True, exist_ok=True)


def classify_log_line(text: str) -> str:
    """Tự động phân loại danh mục và mức độ ưu tiên của dòng log."""
    if not text or not text.strip():
        return "blank"
    stripped = text.strip()
    if stripped.startswith("=" * 8) or stripped.startswith("-" * 8):
        return "divider"
    text_lower = text.lower()
    if "❌" in text or "[lỗi" in text_lower or "error" in text_lower or "exception" in text_lower or "traceback" in text_lower:
        return "error"
    elif "⚠️" in text or "[cảnh báo]" in text_lower or "warning" in text_lower:
        return "warning"
    elif "✅" in text or "[thành công]" in text_lower or "pass" in text_lower or "hoàn tất" in text_lower:
        return "success"
    elif "bước" in text_lower or "[ai agent 8 steps]" in text_lower or "[ai processing]" in text_lower:
        return "step"
    elif "svd" in text_lower or "servicedesk" in text_lower or "ticket" in text_lower or "workorder" in text_lower:
        return "svd"
    elif "📩" in text or "📤" in text or "email" in text_lower or "thư" in text_lower or "imap" in text_lower or "smtp" in text_lower or "hòm thư" in text_lower:
        return "email"
    return "info"


class LogManager:
    """
    Hệ thống quản lý Log tập trung:
    - Lưu file logs/app.log liên tục
    - Lưu Ring Buffer trong bộ nhớ để phục vụ client vừa kết nối
    - Hỗ trợ hàng đợi async để bắn WebSocket Realtime
    """
    def __init__(self, max_buffer_size: int = 1500):
        self.max_buffer_size = max_buffer_size
        self.buffer: List[Dict[str, Any]] = []
        self.subscribers: Set[Any] = set()
        self._loop: Optional[asyncio.AbstractEventLoop] = None

        # Nạp các log có sẵn từ file logs/app.log nếu có
        self._load_existing_logs()

    def set_event_loop(self, loop: asyncio.AbstractEventLoop):
        self._loop = loop

    def _load_existing_logs(self):
        """Đọc tối đa 250 dòng log gần nhất từ file app.log khi khởi động."""
        if not LOG_FILE.exists():
            return
        try:
            with open(LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
                recent_lines = lines[-250:]
                for line in recent_lines:
                    line_clean = strip_ansi(line.rstrip("\r\n"))
                    cat = classify_log_line(line_clean)
                    self.buffer.append({
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                        "message": line_clean,
                        "category": cat
                    })
        except Exception:
            pass

    def add_log(self, message: str, category: Optional[str] = None):
        """Thêm 1 dòng log mới vào hệ thống (giữ nguyên khoảng trống và dòng trắng)."""
        if message is None:
            return

        clean_message = strip_ansi(message).rstrip("\r\n")
        now_str = datetime.now().strftime("%H:%M:%S")
        cat = category or classify_log_line(clean_message)

        log_entry = {
            "timestamp": now_str,
            "message": clean_message,
            "category": cat
        }

        # 1. Lưu vào In-Memory Buffer
        self.buffer.append(log_entry)
        if len(self.buffer) > self.max_buffer_size:
            self.buffer.pop(0)

        # 2. Ghi vào file logs/app.log
        try:
            with open(LOG_FILE, "a", encoding="utf-8", errors="replace") as f:
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{cat.upper()}] {clean_message}\n")
        except Exception:
            pass

        # 3. Đẩy tới các WebSocket subscribers
        if self.subscribers:
            for item in list(self.subscribers):
                try:
                    target_loop, q = item
                    if target_loop and target_loop.is_running():
                        target_loop.call_soon_threadsafe(q.put_nowait, log_entry)
                    else:
                        q.put_nowait(log_entry)
                except Exception:
                    pass

    def get_logs(self, limit: int = 200, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lấy danh sách log gần nhất, có hỗ trợ bộ lọc."""
        logs = self.buffer
        if category and category != "all":
            logs = [entry for entry in logs if entry["category"] == category]
        return logs[-limit:]

    def clear(self):
        """Xóa buffer trong bộ nhớ và xóa trắng file log."""
        self.buffer.clear()
        try:
            with open(LOG_FILE, "w", encoding="utf-8") as f:
                f.write("")
        except Exception:
            pass

    def register_subscriber(self, q: asyncio.Queue, loop: Optional[asyncio.AbstractEventLoop] = None):
        if loop is None:
            try:
                loop = asyncio.get_running_loop()
            except Exception:
                loop = self._loop
        self.subscribers.add((loop, q))

    def unregister_subscriber(self, q: asyncio.Queue):
        self.subscribers = {item for item in self.subscribers if item[1] is not q}


    def broadcast_status(self, status_dict: dict):
        """Bắn trạng thái hệ thống cập nhật tới tất cả client WebSocket."""
        msg = {"type": "status_update", "status": status_dict}
        for item in list(self.subscribers):
            try:
                target_loop, q = item
                if target_loop and target_loop.is_running():
                    target_loop.call_soon_threadsafe(q.put_nowait, msg)
                else:
                    q.put_nowait(msg)
            except Exception:
                pass


# Singleton LogManager
log_manager = LogManager()


import re

ANSI_REGEX = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]|\[[0-9]{1,3}(?:;[0-9]{1,3})*m')
HTTP_ACCESS_REGEX = re.compile(r'(?:INFO|DEBUG):\s+\d{1,3}(?:\.\d{1,3}){3}:\d+\s+-\s+"(?:GET|POST|PUT|DELETE|HEAD|OPTIONS|WEBSOCKET)\s+', re.IGNORECASE)


def strip_ansi(text: str) -> str:
    """Loại bỏ toàn bộ mã màu ANSI (\x1b[32m, [0m, [36m...) tránh gây lỗi hiển thị ký tự lạ."""
    if not text:
        return ""
    return ANSI_REGEX.sub('', text)


def is_internal_noise(text: str) -> bool:
    """Loại bỏ các dòng log truy vấn HTTP nội bộ của uvicorn để giữ log nghiệp vụ sạch sẽ."""
    if not text:
        return False
    clean = strip_ansi(text).strip()
    if not clean:
        return False
    clean_lower = clean.lower()

    if HTTP_ACCESS_REGEX.search(clean):
        return True
    if 'get /api/status' in clean_lower or 'get /api/logs' in clean_lower:
        return True
    if 'websocket /ws/logs' in clean_lower:
        return True
    if 'connection open' in clean_lower or 'connection closed' in clean_lower:
        return True
    if ' - "get /' in clean_lower or ' - "post /' in clean_lower or ' - "websocket /' in clean_lower:
        return True
    if 'http/1.1 200 ok' in clean_lower or 'http/1.1 304' in clean_lower or 'http/1.1 101' in clean_lower:
        return True
    return False


def classify_stream_log(text: str, is_stderr: bool = False) -> str:
    """Phân loại log thông minh: không đánh dấu nhầm INFO từ stderr là error."""
    cat = classify_log_line(text)
    if is_stderr:
        text_lower = text.lower()
        if "info:" in text_lower or "debug:" in text_lower:
            return "info"
        if "warning:" in text_lower:
            return "warning"
        if cat != "info":
            return cat
        return "error"
    return cat


class StreamTee:
    """
    Đánh chặn sys.stdout và sys.stderr:
    Vừa in ra màn hình terminal nguyên bản (loại bỏ mã màu thô và HTTP access log của uvicorn),
    vừa gửi vào LogManager để hiển thị trên Web Console.
    """
    def __init__(self, original_stream, is_stderr: bool = False):
        self.original_stream = original_stream
        self.is_stderr = is_stderr
        self.line_buffer = ""

    def write(self, text):
        if not text:
            return

        self.line_buffer += text
        while "\n" in self.line_buffer:
            line, self.line_buffer = self.line_buffer.split("\n", 1)
            raw_line = line.strip("\r")
            clean_line = strip_ansi(raw_line)

            # Bỏ qua log truy vấn HTTP uvicorn nội bộ
            if is_internal_noise(clean_line):
                continue

            # In ra console terminal (sử dụng clean_line để tránh lỗi hiển thị mã màu thô [32m... trên Windows)
            try:
                self.original_stream.write(clean_line + "\n")
                self.original_stream.flush()
            except Exception:
                pass

            # Ghi vào Web Log Manager
            cat = classify_stream_log(clean_line, is_stderr=self.is_stderr)
            log_manager.add_log(clean_line, category=cat)

    def flush(self):
        if self.line_buffer:
            raw_line = self.line_buffer.strip("\r")
            clean_line = strip_ansi(raw_line)
            if not is_internal_noise(clean_line):
                try:
                    self.original_stream.write(clean_line)
                    self.original_stream.flush()
                except Exception:
                    pass
                cat = classify_stream_log(clean_line, is_stderr=self.is_stderr)
                log_manager.add_log(clean_line, category=cat)
            self.line_buffer = ""
        else:
            try:
                self.original_stream.flush()
            except Exception:
                pass

    def isatty(self):
        try:
            return self.original_stream.isatty()
        except Exception:
            return False

    def fileno(self):
        try:
            return self.original_stream.fileno()
        except Exception:
            raise OSError("StreamTee: fileno not supported")

    @property
    def encoding(self):
        return getattr(self.original_stream, "encoding", "utf-8")

    @property
    def errors(self):
        return getattr(self.original_stream, "errors", "replace")

    def __getattr__(self, name):
        return getattr(self.original_stream, name)


_is_intercepted = False

def enable_stdout_interception():
    """Kích hoạt việc tự động bắt mọi lệnh print() chuyển sang Web Log Viewer."""
    global _is_intercepted
    if not _is_intercepted:
        sys.stdout = StreamTee(sys.stdout, is_stderr=False)
        sys.stderr = StreamTee(sys.stderr, is_stderr=True)
        _is_intercepted = True


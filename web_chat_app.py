import os
import sys
import json
import time
import uuid
import threading
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from fastapi import FastAPI, APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

# Thiết lập BASE_DIR
BASE_DIR = Path(__file__).parent.resolve()
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import config
import email_ai_processor
from agent_8_steps import ticket_system

# Đường dẫn lưu trữ phiên chat đơn giản
CHAT_STORAGE_FILE = BASE_DIR / "data" / "simple_chat_session.json"
TEMPLATES_DIR = BASE_DIR / "templates"

# Router dùng chung để có thể mount vào web_log_app hoặc chạy độc lập
chat_router = APIRouter()
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


# =========================================================================
# QUẢN LÝ PHIÊN CHAT ĐƠN GIẢN (SESSION MANAGER)
# =========================================================================

class SimpleChatSession:
    def __init__(self, storage_path: Path):
        self.storage_path = storage_path
        self._lock = threading.Lock()
        self._ensure_storage()

    def _ensure_storage(self):
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.storage_path.exists():
            self._save_empty()

    def _save_empty(self):
        empty_session = {
            "session_id": uuid.uuid4().hex[:10],
            "ticket_id": None,
            "first_subject": None,
            "flow_type": None,
            "status": None,
            "assigned_team": None,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "messages": []
        }
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(empty_session, f, ensure_ascii=False, indent=2)
        return empty_session

    def get_session(self) -> Dict[str, Any]:
        with self._lock:
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return self._save_empty()

    def save_session(self, session_data: Dict[str, Any]):
        with self._lock:
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)

    def reset_session(self) -> Dict[str, Any]:
        with self._lock:
            return self._save_empty()


chat_session = SimpleChatSession(CHAT_STORAGE_FILE)


# =========================================================================
# SCHEMAS (PYDANTIC)
# =========================================================================

class ChatMessagePayload(BaseModel):
    message: str = Field(..., description="Nội dung chat người dùng nhập (tương đương body email)")


# =========================================================================
# ROUTER APIS
# =========================================================================

@chat_router.get("/chat", response_class=HTMLResponse, summary="Giao diện Web Chat Đơn Giản")
async def chat_page(request: Request):
    """Hiển thị trang giao diện Web Chat đơn giản gửi/nhận email msbservicedesk2026."""
    return templates.TemplateResponse(
        request=request,
        name="chat_simulator.html",
        context={
            "request": request,
            "user_email": "user@company.com",
            "target_email": config.EMAIL_ACCOUNT
        }
    )


@chat_router.get("/api/chat/history", summary="Lấy lịch sử hội thoại hiện tại")
async def get_chat_history():
    """Trả về toàn bộ tin nhắn trong phiên chat hiện tại."""
    return chat_session.get_session()


@chat_router.post("/api/chat/reset", summary="Làm mới đoạn chat")
async def reset_chat():
    """Xóa trắng cuộc trò chuyện để bắt đầu yêu cầu mới."""
    new_sess = chat_session.reset_session()
    return {"status": "success", "message": "Đã làm mới đoạn chat.", "session": new_sess}


@chat_router.post("/api/chat/message", summary="Gửi tin nhắn chat = Body email gửi MSB Service Desk")
async def send_chat_message(payload: ChatMessagePayload):
    """
    Xử lý tin nhắn chat từ người dùng:
    - Người gửi cố định: User <user@company.com>
    - Nhận tin nhắn chat làm nội dung email (body)
    - Tự động sinh tiêu đề email (subject) hoặc kế thừa Re: [Ticket ID] nếu là multi-turn
    - Gọi email_ai_processor.process_incoming_email (giữ nguyên quy trình AI Multi-Agent)
    - Nhận phản hồi email từ AI và trả lời trực tiếp trong Web Chat
    """
    user_text = payload.message.strip()
    if not user_text:
        raise HTTPException(status_code=400, detail="Nội dung tin nhắn không được để trống.")

    session = chat_session.get_session()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    start_time = time.time()

    sender_name = "User"
    sender_email = "user@company.com"

    # 1. Xác định tiêu đề và ngữ cảnh email (Lượt đầu vs Lượt đa turn)
    ticket_id = session.get("ticket_id")
    first_subject = session.get("first_subject")

    if not first_subject:
        # Lượt đầu tiên: Tự động trích xuất tiêu đề từ câu chat đầu tiên
        first_line = user_text.split("\n")[0].strip()
        effective_subject = first_line[:70] if len(first_line) > 0 else "Yêu cầu hỗ trợ IT Service Desk"
        session["first_subject"] = effective_subject
        actual_body_to_process = user_text
    else:
        # Lượt phản hồi tiếp theo (Multi-turn)
        if ticket_id:
            effective_subject = f"Re: [{ticket_id}] {first_subject}"
        else:
            effective_subject = f"Re: {first_subject}"

        # Tìm phản hồi gần nhất của bot để trích dẫn chuẩn email history
        prev_bot_msgs = [m for m in session.get("messages", []) if m.get("sender") == "bot"]
        if prev_bot_msgs:
            last_bot = prev_bot_msgs[-1]
            last_text = last_bot.get("text", "")
            quoted = "\n".join([f"> {line}" for line in last_text.strip().split("\n")[:10]])
            actual_body_to_process = (
                f"{user_text}\n\n"
                f"On {last_bot.get('timestamp', now_str)} MSB Service Desk <{config.EMAIL_ACCOUNT}> wrote:\n"
                f"{quoted}"
            )
        else:
            actual_body_to_process = user_text

    # 2. Tạo tin nhắn người dùng
    user_msg_id = f"msg_{uuid.uuid4().hex[:8]}"
    user_message = {
        "id": user_msg_id,
        "sender": "user",
        "sender_name": sender_name,
        "sender_email": sender_email,
        "text": user_text,
        "timestamp": now_str
    }
    session["messages"].append(user_message)

    # 3. Gọi AI Multi-Agent LangGraph qua email_ai_processor (hoàn toàn không gửi SMTP thật)
    try:
        ai_res = await asyncio.to_thread(
            email_ai_processor.process_incoming_email,
            sender_name=sender_name,
            sender_email=sender_email,
            subject=effective_subject,
            body=actual_body_to_process,
            attachments=[]
        )
    except Exception as e:
        ai_res = {
            "flow_type": "error",
            "reply_subject": f"Re: {effective_subject}",
            "reply_body_plain": f"Đã xảy ra sự cố khi xử lý yêu cầu: {str(e)}",
            "reply_body_html": f"<p style='color:red;'>Đã xảy ra sự cố khi xử lý yêu cầu: {str(e)}</p>",
            "assigned_agent": "IT Support Team",
            "routing_reason": "Lỗi ngoại lệ",
            "ticket_id": ticket_id or "ERROR",
            "root_cause": str(e),
            "status": "ERROR",
            "raw_answer": ""
        }

    elapsed = round(time.time() - start_time, 2)
    new_ticket_id = ai_res.get("ticket_id") or ticket_id

    # Cập nhật thông tin session
    if new_ticket_id:
        session["ticket_id"] = new_ticket_id
    session["status"] = ai_res.get("status", session.get("status"))
    session["assigned_team"] = ai_res.get("assigned_agent", session.get("assigned_team"))
    session["flow_type"] = ai_res.get("flow_type", session.get("flow_type"))

    # 4. Tạo tin nhắn phản hồi của AI Bot
    bot_msg_id = f"msg_{uuid.uuid4().hex[:8]}"
    bot_reply_text = ai_res.get("reply_body_plain", "").strip()
    if not bot_reply_text and ai_res.get("reply_body_html"):
        bot_reply_text = ai_res.get("reply_body_html")

    raw_html = ai_res.get("reply_body_html", "")
    bot_html = email_ai_processor.ensure_ticket_notification_box(
        raw_html,
        ticket_id=new_ticket_id,
        svd_url=ai_res.get("svd_url", ""),
        status=ai_res.get("status", "RESOLVED_BY_AI"),
        action_taken=ai_res.get("action_taken", "CREATED_NEW_TICKET")
    )

    bot_message = {
        "id": bot_msg_id,
        "sender": "bot",
        "sender_name": "MSB Service Desk",
        "text": bot_reply_text,
        "html": bot_html,
        "ticket_id": new_ticket_id,
        "assigned_team": ai_res.get("assigned_agent", "IT Support"),
        "status": ai_res.get("status", "RESOLVED_BY_AI"),
        "flow_type": ai_res.get("flow_type", "incident"),
        "root_cause": ai_res.get("root_cause", ""),
        "elapsed_seconds": elapsed,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    session["messages"].append(bot_message)
    chat_session.save_session(session)

    return {
        "status": "success",
        "user_message": user_message,
        "bot_message": bot_message,
        "ticket_id": new_ticket_id,
        "elapsed_seconds": elapsed
    }


# =========================================================================
# STANDALONE FASTAPI APP
# =========================================================================

app = FastAPI(
    title="MSB Service Desk - Simple Web Chat",
    description="Web Chat đơn giản gửi/nhận email với msbservicedesk2026@gmail.com",
    version="2.0.0"
)

app.include_router(chat_router)

@app.get("/", response_class=HTMLResponse)
async def root_redirect(request: Request):
    return await chat_page(request)


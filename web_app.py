import os
import sys
import json
import asyncio
import threading
import time
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.templating import Jinja2Templates

# Thiết lập đường dẫn gốc
BASE_DIR = Path(__file__).parent.resolve()
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import config
from utils.log_manager import log_manager, enable_stdout_interception, LOG_FILE
from agent_8_steps import ticket_system
import main_email_bot

# Tắt logger access của uvicorn để không bị spam log GET /api/status
import logging
logging.getLogger("uvicorn.access").disabled = True
logging.getLogger("uvicorn.access").propagate = False

# Kích hoạt đánh chặn stdout/stderr ngay khi khởi động
enable_stdout_interception()

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_running_loop()
    log_manager.set_event_loop(loop)
    print("=" * 75)
    print("🌐 [FASTAPI LOG VIEWER] Khởi chạy thành công máy chủ Web xem Log!")
    print(f"👉 Mở trình duyệt truy cập: http://0.0.0.0:{os.environ.get('PORT', 8080)}")
    print("=" * 75)

    # TỰ ĐỘNG KHỞI ĐỘNG EMAIL BOT NGAY KHI SERVER CHẠY
    bot_state["is_running"] = True
    bot_state["task"] = asyncio.create_task(email_bot_worker())

    yield
    bot_state["is_running"] = False
    if bot_state["task"]:
        bot_state["task"].cancel()

app = FastAPI(
    title="AI Service Desk - Web Log Monitor",
    description="Giao diện Web xem Log thời gian thực và quản trị Email Bot qua FastAPI",
    version="1.0.0",
    lifespan=lifespan
)

from web_chat_app import chat_router
app.include_router(chat_router)

@app.get("/health", summary="Health check for AgentBase runtime")
async def health_check():
    return {"status": "ok"}

# Cấu hình Jinja2 Templates
TEMPLATES_DIR = BASE_DIR / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Trạng thái tiến trình Email Bot nền
bot_state = {
    "is_running": False,
    "task": None,
    "last_run": None,
    "total_processed": 0
}


def get_ticket_count() -> int:
    """Đếm tổng số Ticket đã ghi nhận trong cơ sở dữ liệu."""
    try:
        tickets = ticket_system.get_all_tickets()
        return len(tickets)
    except Exception:
        return 0


def get_system_status() -> dict:
    """Tổng hợp trạng thái hoạt động của hệ thống."""
    return {
        "bot_running": bot_state["is_running"],
        "ticket_count": get_ticket_count(),
        "last_run": bot_state["last_run"],
        "poll_interval": config.POLL_INTERVAL_SECONDS,
        "email_account": config.EMAIL_ACCOUNT,
        "mail_folder": config.MAIL_FOLDER,
        "svd_url": "https://49.213.71.61:8089"
    }


async def email_bot_worker():
    """Vòng lặp ngầm quét email định kỳ của bot (đồng bộ 100% với main_email_bot.py)."""
    # In Banner khởi động giống hệt khi chạy python main_email_bot.py
    main_email_bot.print_banner()
    print(f"[CHẾ ĐỘ TỰ ĐỘNG ĐỊNH KỲ] Quét mỗi {config.POLL_INTERVAL_SECONDS} giây một lần...\n")

    cycle = 1
    while bot_state["is_running"]:
        try:
            print(f"--- [CHU KỲ #{cycle}] ---")
            bot_state["last_run"] = time.strftime("%Y-%m-%d %H:%M:%S")
            # Chạy hàm quét email trong worker thread để không block async event loop
            count = await asyncio.to_thread(main_email_bot.run_check_cycle, dry_run=False)
            bot_state["total_processed"] += count
            cycle += 1
            log_manager.broadcast_status(get_system_status())
            print(f"⏳ Nghỉ {config.POLL_INTERVAL_SECONDS} giây trước lần quét tiếp theo...\n")
        except Exception as e:
            print(f"❌ [LỖI BOT WORKER]: {e}")

        # Nghỉ giữa các chu kỳ quét
        for _ in range(config.POLL_INTERVAL_SECONDS):
            if not bot_state["is_running"]:
                break
            await asyncio.sleep(1)

    print("⏹️ [EMAIL BOT WORKER] Đã dừng tiến trình quét email tự động.")
    log_manager.broadcast_status(get_system_status())


# =========================================================================
# GIAO DIỆN HTML & WEBSOCKET STREAMING
# =========================================================================

@app.get("/", response_class=HTMLResponse, summary="Trang Chủ Giới Thiệu & Hướng Dẫn")
@app.get("/home", response_class=HTMLResponse, summary="Trang Chủ Giới Thiệu & Hướng Dẫn")
async def home_page(request: Request):
    """Hiển thị trang Home giới thiệu đề tài và hướng dẫn gửi email hỗ trợ."""
    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={
            "request": request,
            "target_email": config.EMAIL_ACCOUNT,
            "ticket_count": get_ticket_count()
        }
    )


@app.get("/logs", response_class=HTMLResponse, summary="Giao diện Web Console Log")
@app.get("/console", response_class=HTMLResponse, summary="Giao diện Web Console Log")
async def log_viewer_page(request: Request):
    """Hiển thị trang giao diện Web xem log thời gian thực."""
    return templates.TemplateResponse(
        request=request,
        name="log_viewer.html",
        context={"request": request}
    )


@app.websocket("/ws/logs")
async def websocket_logs_endpoint(websocket: WebSocket):
    """Kênh WebSocket truyền log thời gian thực về trình duyệt."""
    await websocket.accept()
    loop = asyncio.get_running_loop()
    q = asyncio.Queue()
    log_manager.register_subscriber(q, loop=loop)

    # Gửi ngay cập nhật trạng thái ban đầu cho client
    try:
        await websocket.send_json({
            "type": "status_update",
            "status": get_system_status()
        })
    except Exception:
        pass

    try:
        while True:
            # Lấy log mới phát sinh từ hàng đợi
            item = await q.get()
            if isinstance(item, dict) and item.get("type") == "status_update":
                await websocket.send_json(item)
            else:
                await websocket.send_json({
                    "type": "log",
                    "entry": item
                })
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        log_manager.unregister_subscriber(q)


# =========================================================================
# REST APIS: LOGS & QUẢN TRỊ HỆ THỐNG
# =========================================================================

@app.get("/api/logs", summary="Lấy danh sách log gần nhất")
async def get_logs_api(limit: int = 200, category: Optional[str] = None):
    """API lấy lịch sử log từ bộ nhớ đệm."""
    return log_manager.get_logs(limit=limit, category=category)


@app.post("/api/logs/clear", summary="Xóa sạch lịch sử log")
async def clear_logs_api():
    """API xóa sạch log màn hình và file app.log."""
    log_manager.clear()
    print("🧹 [LOG MANAGER] Đã xóa trắng toàn bộ lịch sử log.")
    return {"status": "success", "message": "Đã xóa toàn bộ log."}


@app.get("/api/logs/download", summary="Tải file app.log")
async def download_log_file():
    """Cho phép người dùng tải toàn bộ file app.log về máy."""
    if not LOG_FILE.exists():
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            f.write("")
    return FileResponse(
        path=str(LOG_FILE),
        filename="app.log",
        media_type="text/plain"
    )


@app.get("/api/status", summary="Lấy trạng thái hệ thống")
async def get_status_api():
    """API lấy các chỉ số vận hành hệ thống."""
    return get_system_status()


@app.post("/api/bot/trigger", summary="Kích hoạt quét hòm thư ngay 1 lần")
async def trigger_email_check():
    """Chạy ngay lập tức 1 chu kỳ kiểm tra và xử lý email."""
    print("\n⚡ [THỦ CÔNG] Người dùng kích hoạt quét hộp thư ngay từ Web Dashboard...")
    try:
        count = await asyncio.to_thread(main_email_bot.run_check_cycle, dry_run=False)
        bot_state["total_processed"] += count
        bot_state["last_run"] = time.strftime("%Y-%m-%d %H:%M:%S")
        log_manager.broadcast_status(get_system_status())
        return {
            "status": "success",
            "message": f"Hoàn tất quét hòm thư! Đã xử lý {count} thư mới.",
            "processed_count": count
        }
    except Exception as e:
        print(f"❌ [LỖI QUÉT THỦ CÔNG]: {e}")
        return JSONResponse(
            status_code=500,
            content={"status_code": 500, "message": f"Lỗi khi quét: {str(e)}"}
        )


@app.post("/api/bot/start", summary="Bật chế độ tự động quét email định kỳ")
async def start_bot_api():
    """Bật tiến trình ngầm tự động quét email theo chu kỳ."""
    if bot_state["is_running"]:
        return {"status": "already_running", "message": "Email Bot hiện đang chạy rồi."}

    bot_state["is_running"] = True
    bot_state["task"] = asyncio.create_task(email_bot_worker())
    log_manager.broadcast_status(get_system_status())
    return {"status": "started", "message": "Đã khởi động Email Bot tự động chạy ngầm!"}


@app.post("/api/bot/stop", summary="Dừng chế độ tự động quét email")
async def stop_bot_api():
    """Dừng tiến trình quét email tự động."""
    if not bot_state["is_running"]:
        return {"status": "already_stopped", "message": "Email Bot đang ở trạng thái tắt."}

    bot_state["is_running"] = False
    if bot_state["task"]:
        bot_state["task"].cancel()
        bot_state["task"] = None
    log_manager.broadcast_status(get_system_status())
    return {"status": "stopped", "message": "Đã dừng Email Bot."}


if __name__ == "__main__":
    try:
        import colorama
        colorama.init(autoreset=True)
    except Exception:
        pass

    import uvicorn
    # Tắt reload, access_log và use_colors để không sinh bất kỳ mã màu ANSI [32m... hay log truy vấn HTTP nội bộ nào ra terminal
    uvicorn.run(
        "web_app:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        reload=False,
        access_log=False,
        use_colors=False
    )


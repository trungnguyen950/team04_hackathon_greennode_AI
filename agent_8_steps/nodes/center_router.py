import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent.resolve()
DEMO_DIR = BASE_DIR / "center subagents demo"
if str(DEMO_DIR) not in sys.path:
    sys.path.insert(0, str(DEMO_DIR))

from shared_langchain_components import call_llm
from agent_8_steps.state import Agent8StepState
from agent_8_steps import kb_engine
from agent_8_steps import ticket_system

def process(state: Agent8StepState) -> dict:
    """
    CENTER ROUTER: ĐIỀU PHỐI TRUNG TÂM (TƯƠNG TỰ CENTER SUBAGENTS DEMO)
    Phân tích yêu cầu ngôn ngữ tự nhiên từ email người dùng và phân loại điều phối:
    - 'incident': Sự cố kỹ thuật (Mạng, NAC, Outlook, Windows, VPN, Kết nối phần cứng...) -> Subflow A (8 bước)
    - 'software_install': Yêu cầu cài đặt phần mềm / ứng dụng văn phòng / máy in -> Subflow B (6 bước)
    """
    user_req = state.get("user_request", {})
    full_text = user_req.get("full_text", "")
    clean_body = user_req.get("clean_body", "").lower()
    subject = user_req.get("clean_subject", "").lower()
    existing_ticket_id = user_req.get("existing_ticket_id")
    existing_svd_id = user_req.get("existing_svd_id")

    # Nếu đây là email phản hồi trên Ticket cũ, kiểm tra xem Ticket cũ thuộc loại nào
    if existing_ticket_id or existing_svd_id:
        all_tickets = ticket_system.get_all_tickets()
        for t in reversed(all_tickets):
            if (
                t.get("ticket_id") == existing_ticket_id
                or (existing_svd_id and str(t.get("svd_request_id")) == str(existing_svd_id))
                or (existing_ticket_id and t.get("svd_request_id") and str(t.get("svd_request_id")) in str(existing_ticket_id))
            ):
                cat = (t.get("category") or "").lower()
                subj = (t.get("subject") or "").lower()
                flow = (t.get("flow_type") or "").lower()
                if "install" in cat or "service request" in subj or "software_install" in flow:
                    print(f"🧭 [CENTER ROUTER]: Nhận diện Reply trên Ticket Service Request cũ ({existing_ticket_id}) -> Điều phối Subflow B")
                    return {
                        "flow_type": "software_install",
                        "routing_reason": f"Phản hồi tiếp nối Ticket Yêu cầu Dịch vụ cũ ({existing_ticket_id})"
                    }
                break

    # Danh sách tên phần mềm có trong Knowledge Base
    software_list = kb_engine.get_all_software_names()
    software_keywords = [
        "cài", "cài đặt", "install", "cài giúp", "setup", "tải", "download",
        "phần mềm", "software", "máy in", "printer", "office", "teams", "word",
        "excel", "powerpoint", "copilot", "itax", "xml", "driver"
    ]
    
    # Kiểm tra nhanh từ khóa cài đặt phần mềm
    contains_sw_keyword = any(kw in clean_body or kw in subject for kw in software_keywords)
    contains_sw_name = any(sw.lower() in clean_body or sw.lower() in subject for sw in software_list)

    prompt = f"""
Bạn là Trưởng nhóm điều phối IT Service Desk (Center Supervisor Agent).
Nhiệm vụ: Phân tích email của người dùng và quyết định chuyển tiếp yêu cầu đến Subflow quy trình phù hợp:

1. 'incident': Sự cố kỹ thuật, hỏng hóc, lỗi mạng, lỗi Outlook, không gửi được mail, mất kết nối, lỗi mật khẩu, màn hình xanh,...
2. 'software_install': Mọi yêu cầu cài đặt/nâng cấp phần mềm (kể cả phần mềm nằm ngoài danh mục hệ thống quy định ví dụ: AutoCAD, Photoshop, VS Code, SPSS, Canva...), kết nối máy in, yêu cầu cấp quyền ứng dụng.

Danh sách các phần mềm hệ thống hiện có: {', '.join(software_list)}

Yêu cầu người dùng:
"{full_text}"

Hãy trả lời theo đúng định dạng 2 dòng:
FLOW: <incident | software_install>
REASON: <Lý do ngắn gọn bằng tiếng Việt>
"""
    raw_response = call_llm(prompt).strip()

    flow_type = "incident"
    reason = "Điều phối mặc định"

    for line in raw_response.splitlines():
        line_clean = line.strip()
        if line_clean.upper().startswith("FLOW:"):
            val = line_clean.split(":", 1)[1].strip().lower()
            if val in ["incident", "software_install"]:
                flow_type = val
        elif line_clean.upper().startswith("REASON:"):
            reason = line_clean.split(":", 1)[1].strip()

    # Heuristic an toàn nếu prompt phân loại chưa khớp nhưng có dấu hiệu rõ ràng
    if (contains_sw_name or contains_sw_keyword) and ("cài" in clean_body or "cài" in subject or "install" in clean_body or "setup" in clean_body):
        flow_type = "software_install"

    print("\n" + "=" * 70)
    print("🧭 [CENTER ROUTER] ĐIỀU PHỐI QUY TRÌNH HỆ THỐNG")
    print("=" * 70)
    print(f" • Phân nhánh Subflow : {'🚀 SUBFLOW B: CÀI ĐẶT PHẦN MỀM' if flow_type == 'software_install' else '🛠️ SUBFLOW A: XỬ LÝ SỰ CỐ'}")
    print(f" • Lý do định tuyến   : {reason}")

    return {
        "flow_type": flow_type,
        "routing_reason": reason
    }


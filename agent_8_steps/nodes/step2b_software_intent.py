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
    BƯỚC 2B: SOFTWARE INTENT
    Xác định loại phần mềm cần cài đặt/hỗ trợ, mục đích sử dụng (Work Purposes),
    đối chiếu với danh mục ServiceRequest trong cơ sở tri thức Excel và gán mức ưu tiên.
    """
    user_req = state.get("user_request", {})
    full_text = user_req.get("full_text", "")
    software_list = kb_engine.get_all_software_names()
    service_items = kb_engine.load_service_requests()

    software_catalog_str = "\n".join([
        f"- {item['software_name']} (Mã KB: {item['kb_id']}) | Mục đích: {item['work_purposes']}"
        for item in service_items
    ])

    prompt = f"""
Bạn là Chuyên viên Tiếp nhận Yêu cầu Phần mềm IT (IT Software Dispatcher).
Hãy phân tích yêu cầu từ người dùng để xác định chính xác phần mềm mà người dùng cần cài đặt hoặc kết nối:

[DANH MỤC PHẦN MỀM CHUẨN TRONG HỆ THỐNG]:
{software_catalog_str}

[YÊU CẦU NGƯỜI DÙNG]:
"{full_text}"

Nhiệm vụ:
1. Xác định SOFTWARE_NAME:
   - Nếu phần mềm người dùng yêu cầu có trong danh mục chuẩn, hãy chọn đúng tên: {', '.join(software_list)}.
   - Nếu phần mềm người dùng yêu cầu KHÔNG nằm trong danh mục chuẩn trên (ví dụ: AutoCAD, Photoshop, VS Code, SPSS, Canva...), hãy trích xuất chính xác tên phần mềm từ yêu cầu của người dùng.
2. Xác định IS_IN_CATALOG: YES (nếu có trong danh mục chuẩn) hoặc NO (nếu ngoài danh mục).
3. Xác định mục đích sử dụng chính của người dùng (WORK_PURPOSE).
4. Xác định mức độ ưu tiên: LOW | MEDIUM | HIGH (mặc định yêu cầu cài phần mềm là LOW hoặc MEDIUM).
5. Tóm tắt ngắn gọn 1 câu về yêu cầu cài đặt phần mềm này.

Hãy trả về chính xác định dạng 5 dòng:
SOFTWARE_NAME: <Tên phần mềm>
IS_IN_CATALOG: <YES | NO>
WORK_PURPOSE: <Mục đích sử dụng của người dùng>
PRIORITY: <LOW | MEDIUM | HIGH>
SUMMARY: <Tóm tắt ngắn gọn yêu cầu>
"""
    raw_res = call_llm(prompt).strip()

    is_in_catalog = True
    detected_name = ""
    work_purpose = "Cài đặt phần mềm phục vụ công việc"
    priority = "LOW"
    summary = "Yêu cầu cài đặt ứng dụng"

    for line in raw_res.splitlines():
        line_clean = line.strip()
        if line_clean.upper().startswith("SOFTWARE_NAME:"):
            detected_name = line_clean.split(":", 1)[1].strip()
        elif line_clean.upper().startswith("IS_IN_CATALOG:"):
            val_cat = line_clean.split(":", 1)[1].strip().upper()
            if "NO" in val_cat or "FALSE" in val_cat:
                is_in_catalog = False
            else:
                is_in_catalog = True
        elif line_clean.upper().startswith("WORK_PURPOSE:"):
            work_purpose = line_clean.split(":", 1)[1].strip()
        elif line_clean.upper().startswith("PRIORITY:"):
            p_val = line_clean.split(":", 1)[1].strip().upper()
            if p_val in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]:
                priority = p_val
        elif line_clean.upper().startswith("SUMMARY:"):
            summary = line_clean.split(":", 1)[1].strip()

    existing_ticket_id = user_req.get("existing_ticket_id")
    existing_svd_id = user_req.get("existing_svd_id")

    # Nếu là phản hồi ticket cũ, ưu tiên kế thừa tên phần mềm từ ticket cũ nếu phần mềm hiện tại không rõ hoặc không thuộc danh mục mà ticket cũ có
    if existing_ticket_id or existing_svd_id:
        all_tickets = ticket_system.get_all_tickets()
        for t in reversed(all_tickets):
            if (
                t.get("ticket_id") == existing_ticket_id
                or (existing_svd_id and str(t.get("svd_request_id")) == str(existing_svd_id))
                or (existing_ticket_id and t.get("svd_request_id") and str(t.get("svd_request_id")) in str(existing_ticket_id))
            ):
                old_sw = t.get("software_name")
                if not old_sw and t.get("intent_name", "").startswith("Install "):
                    old_sw = t.get("intent_name").replace("Install ", "").strip()

                need_inherit = (
                    not detected_name
                    or detected_name.lower() in ["phần mềm ngoài danh mục", "phần mềm văn phòng", "phần mềm", "none", "không", "chưa rõ", "kế toán", "nhân sự", "it"]
                    or (old_sw and any(sw.lower() == old_sw.lower() for sw in software_list) and not any(sw.lower() == detected_name.lower() for sw in software_list))
                )
                if need_inherit and old_sw:
                    detected_name = old_sw
                    is_in_catalog = any(sw.lower() == detected_name.lower() for sw in software_list) or (len(detected_name) >= 4 and any(sw.lower() in detected_name.lower() for sw in software_list))
                    print(f"📌 [KẾ THỪA TICKET CŨ]: Giữ nguyên phần mềm '{detected_name}' từ Ticket cũ {existing_ticket_id}")
                break

    # Kiểm tra xem detected_name có khớp với phần mềm nào trong danh mục chuẩn không
    catalog_match = None
    for sw in software_list:
        if sw.lower() == detected_name.lower():
            catalog_match = sw
            break
        elif (len(detected_name) >= 4 and (sw.lower() in detected_name.lower() or detected_name.lower() in sw.lower())):
            catalog_match = sw
            break

    if catalog_match and is_in_catalog:
        detected_name = catalog_match
        matched_item = kb_engine.find_software_match(full_text, software_name=detected_name)
        kb_id = matched_item.get("kb_id", "SOF-UNKNOWN") if matched_item else "SOF-UNKNOWN"
        category = matched_item.get("category", "Install / Office Software") if matched_item else "Install / Office Software"
        assigned_team = matched_item.get("assigned_team", "IT Support Team") if matched_item else "IT Support Team"
    else:
        # Phần mềm không nằm trong danh mục file Excel
        is_in_catalog = False
        matched_item = None
        kb_id = "SOF-NON-CATALOG"
        category = "Install / Non-Standard Software"
        assigned_team = "IT Support Team"
        if not detected_name:
            detected_name = "Phần mềm ngoài danh mục"

    print("\n" + "=" * 70)
    print("🔹 [BƯỚC 2B: SOFTWARE INTENT] XÁC ĐỊNH LOẠI PHẦN MỀM CẦN CÀI ĐẶT")
    print("=" * 70)
    print(f" • Phần mềm xác định  : {detected_name} (Mã KB: {kb_id})")
    print(f" • Thuộc danh mục chuẩn: {'✅ CÓ' if is_in_catalog else '⚠️ KHÔNG (Ngoài danh mục)'}")
    print(f" • Nhóm danh mục      : {category}")
    print(f" • Đội ngũ phân công  : {assigned_team}")
    print(f" • Mục đích công việc : {work_purpose}")
    print(f" • Mức ưu tiên        : {priority}")
    print(f" • Tóm tắt yêu cầu    : {summary}")

    return {
        "software_intent": {
            "software_name": detected_name,
            "is_in_catalog": is_in_catalog,
            "kb_id": kb_id,
            "category": category,
            "assigned_team": assigned_team,
            "work_purpose": work_purpose,
            "priority": priority,
            "summary": summary,
            "kb_item": matched_item or {}
        }
    }


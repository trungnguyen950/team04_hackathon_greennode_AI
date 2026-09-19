import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent.resolve()
DEMO_DIR = BASE_DIR / "center subagents demo"
if str(DEMO_DIR) not in sys.path:
    sys.path.insert(0, str(DEMO_DIR))

from shared_langchain_components import call_llm
from agent_8_steps.state import Agent8StepState

def process(state: Agent8StepState) -> dict:
    """
    BƯỚC 6: RECOMMENDATION
    Đưa ra hướng xử lý chi tiết (Action Steps) dựa trên cột Resolution_Action
    và Sample_Scenario từ cơ sở tri thức Excel.
    """
    user_req = state.get("user_request", {})
    kb_data = state.get("knowledge", {})
    diag_data = state.get("diagnostic", {})
    context_data = state.get("context", {})
    intent_data = state.get("intent", {})

    if intent_data.get("is_issue_resolved"):
        print("\n" + "=" * 70)
        print("🔹 [BƯỚC 6: RECOMMENDATION] ĐƯA RA HƯỚNG XỬ LÝ & GIẢI PHÁP")
        print("=" * 70)
        print(" • Ghi nhận kết thúc xử lý sự cố. Không cần khuyến nghị thêm.")
        return {
            "recommendation": {
                "action_title": "Đóng phiếu hỗ trợ và hoàn tất",
                "steps_guidance": "Sự cố đã được xác nhận giải quyết thành công. Phiếu hỗ trợ đã được đóng.",
                "can_auto_resolve": True,
            }
        }

    full_text = user_req.get("full_text", "")
    sop_action = kb_data.get("resolution_action", "")
    sample_scenario = kb_data.get("sample_scenario", "")
    root_cause = diag_data.get("root_cause", "")
    can_auto_resolve = diag_data.get("can_auto_resolve", True)
    missing_info = context_data.get("missing_info", "")

    prompt = f"""
Bạn là Chuyên viên Hỗ trợ Cấp cao IT Service Desk (Tier 1 Support Lead).
Nhiệm vụ: Soạn thảo hướng dẫn giải quyết sự cố chi tiết và chuẩn xác cho người dùng.

[THÔNG TIN SỰ CỐ]:
"{full_text}"
- Nguyên nhân gốc: {root_cause}
- Hướng xử lý chuẩn (SOP từ Knowledge Base): {sop_action}
- Kịch bản xử lý mẫu: {sample_scenario}
- Khả năng tự xử lý: {'Người dùng có thể tự thao tác' if can_auto_resolve else 'Cần IT can thiệp'}
- Thông tin còn thiếu (nếu có): {missing_info}

Yêu cầu:
1. Đưa ra hướng xử lý rõ ràng, mạch lạc, chia thành các bước 1, 2, 3 dễ thao tác nhất.
2. Nếu người dùng cần cung cấp thêm thông tin còn thiếu ({missing_info}), hãy nhắc nhở lịch sự.
3. Cung cấp phương án dự phòng (workaround) nếu bước chính không thành công.

Hãy viết phần hướng dẫn xử lý này bằng tiếng Việt chuẩn, trang trọng và dễ hiểu.
"""
    recommendation_text = call_llm(prompt).strip()

    print("\n" + "=" * 70)
    print("🔹 [BƯỚC 6: RECOMMENDATION] ĐƯA RA HƯỚNG XỬ LÝ & GIẢI PHÁP")
    print("=" * 70)
    print(f" • Hành động chuẩn (SOP) : {sop_action}")
    print(f" • Hướng dẫn chi tiết (Trích đoạn):\n{recommendation_text[:200]}...")

    return {
        "recommendation": {
            "action_title": sop_action,
            "steps_guidance": recommendation_text,
            "can_auto_resolve": can_auto_resolve,
        }
    }


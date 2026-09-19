from agent_8_steps.state import Agent8StepState
from agent_8_steps import prerequisite_checker

def process(state: Agent8StepState) -> dict:
    """
    BƯỚC 4B: CHECK PREREQUISITES
    Kiểm tra điều kiện tiên quyết để được cài đặt phần mềm:
    - Tra cứu quy định trong cột Prerequisites của ServiceRequest.
    - Kích hoạt các hàm kiểm tra tự động:
      * check_office_365_E3_license(username) cho MS Office 365
      * check_ms_teams_license(username) cho MS Teams
      * Kiểm tra tính hợp lệ IP/phòng ban cho máy in Ricoh / Brother
    - Đưa ra kết luận người dùng có ĐỦ ĐIỀU KIỆN (is_eligible = True) hay cần bổ sung giấy phép/phê duyệt.
    """
    sw_intent = state.get("software_intent", {})
    sw_context = state.get("software_context", {})
    user_req = state.get("user_request", {})

    kb_item = sw_intent.get("kb_item", {})
    username = sw_context.get("user_id") or user_req.get("sender_email", "")
    software_name = sw_intent.get("software_name", "Phần mềm")
    is_in_catalog = sw_intent.get("is_in_catalog", True)

    if not is_in_catalog:
        is_eligible = False
        prereq_status = "NON_STANDARD_SOFTWARE"
        prereq_rule = "Non-Catalog Evaluation Required"
        summary = f"Phần mềm '{software_name}' không nằm trong danh mục phần mềm theo quy định của công ty. IT sẽ xem xét đánh giá có hỗ trợ không."
        has_prerequisites = False
        checks_performed = []
    else:
        # Thực thi đánh giá điều kiện tiên quyết
        prereq_eval = prerequisite_checker.evaluate_software_prerequisites(
            software_item=kb_item,
            username=username,
            context_data=sw_context
        )
        is_eligible = prereq_eval.get("is_eligible", True)
        prereq_status = prereq_eval.get("status", "ELIGIBLE")
        summary = prereq_eval.get("summary", "")
        prereq_rule = prereq_eval.get("prerequisite_rule", "No")
        has_prerequisites = prereq_eval.get("has_prerequisites", False)
        checks_performed = prereq_eval.get("checks_performed", [])

    print("\n" + "=" * 70)
    print("🔹 [BƯỚC 4B: CHECK PREREQUISITES] KIỂM TRA ĐIỀU KIỆN CÀI ĐẶT PHẦN MỀM")
    print("=" * 70)
    print(f" • Phần mềm kiểm tra   : {software_name}")
    print(f" • Quy tắc (Prereq Rule): {prereq_rule}")
    print(f" • Trạng thái thẩm định : {'✅ ĐỦ ĐIỀU KIỆN (ELIGIBLE)' if is_eligible else '⚠️ CẦN XEM XÉT / NGOÀI QUY ĐỊNH'}")
    print(f" • Chi tiết kiểm tra    : {summary}")
    if checks_performed:
        for c in checks_performed:
            print(f"   -> Đã gọi hàm '{c['check_name']}' cho user '{c['target_user']}': Kết quả = {c['passed']}")

    return {
        "software_prerequisites": {
            "has_prerequisites": has_prerequisites,
            "is_eligible": is_eligible,
            "status": prereq_status,
            "prerequisite_rule": prereq_rule,
            "summary": summary,
            "checks_performed": checks_performed,
        }
    }


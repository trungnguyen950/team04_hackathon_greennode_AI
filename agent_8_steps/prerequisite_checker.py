import re
from typing import Dict, Any, List

def check_office_365_E3_license(username: str) -> bool:
    """
    Kiểm tra xem tài khoản người dùng có được cấp License Microsoft 365 E3 hay không.
    (Giả lập phục vụ thử nghiệm: Luôn trả về True).
    """
    print(f"🔍 [PREREQUISITE CHECK] Kiểm tra license Microsoft 365 E3 cho tài khoản: '{username}' -> ĐẠT (True)")
    return True


def check_ms_teams_license(username: str) -> bool:
    """
    Kiểm tra xem tài khoản người dùng có được cấp License Microsoft Teams hay không.
    (Giả lập phục vụ thử nghiệm: Luôn trả về True).
    """
    print(f"🔍 [PREREQUISITE CHECK] Kiểm tra license Microsoft Teams cho tài khoản: '{username}' -> ĐẠT (True)")
    return True


def evaluate_software_prerequisites(software_item: Dict[str, Any], username: str, context_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Đánh giá điều kiện cài đặt (Prerequisites) dựa trên cấu hình từ sheet ServiceRequest.
    """
    prereq_raw = software_item.get("prerequisites", "No").strip()
    software_name = software_item.get("software_name", "")
    checks_performed = []
    is_eligible = True
    status = "ELIGIBLE"
    summary_parts = []

    # 1. Trường hợp không có điều kiện ràng buộc
    if not prereq_raw or prereq_raw.lower() in ["no", "none", "không", "không có"]:
        is_eligible = True
        status = "ELIGIBLE"
        summary_parts.append(f"Phần mềm '{software_name}' thuộc danh mục chuẩn/tự do của doanh nghiệp, không yêu cầu cấp phép bản quyền đặc thù.")
    else:
        # 2. Kiểm tra điều kiện Office 365 E3
        if "check_office_365_E3_license" in prereq_raw:
            has_e3 = check_office_365_E3_license(username)
            checks_performed.append({
                "check_name": "check_office_365_E3_license",
                "target_user": username,
                "passed": has_e3
            })
            if has_e3:
                summary_parts.append(f"Tài khoản '{username}' được xác nhận đã được cấp phép Office 365 E3.")
            else:
                is_eligible = False
                status = "MISSING_LICENSE"
                summary_parts.append(f"Tài khoản '{username}' chưa được cấp phép Office 365 E3. Cần làm thủ tục xin cấp bản quyền qua Trưởng bộ phận.")

        # 3. Kiểm tra điều kiện MS Teams License
        elif "check_ms_teams_license" in prereq_raw:
            has_teams = check_ms_teams_license(username)
            checks_performed.append({
                "check_name": "check_ms_teams_license",
                "target_user": username,
                "passed": has_teams
            })
            if has_teams:
                summary_parts.append(f"Tài khoản '{username}' được xác nhận đã được cấp phép MS Teams.")
            else:
                is_eligible = False
                status = "MISSING_LICENSE"
                summary_parts.append(f"Tài khoản '{username}' chưa có License MS Teams.")
        else:
            # Điều kiện văn bản khác
            summary_parts.append(f"Điều kiện hệ thống quy định: {prereq_raw}")

    # 4. Kiểm tra điều kiện máy in (nếu là cài driver máy in)
    if "printer" in software_name.lower():
        printer_ip = context_data.get("printer_ip", "")
        if printer_ip and printer_ip.lower() not in ["chưa rõ", "no", "none", ""]:
            summary_parts.append(f"Đã nhận diện địa chỉ IP máy in: {printer_ip}.")
        else:
            summary_parts.append("Lưu ý: Chưa phát hiện địa chỉ IP máy in cụ thể trong nội dung yêu cầu.")

    has_prerequisites = bool(prereq_raw and prereq_raw.lower() not in ["no", "none", "không", "không có"])

    return {
        "has_prerequisites": has_prerequisites,
        "is_eligible": is_eligible,
        "status": status,
        "prerequisite_rule": prereq_raw,
        "summary": " ".join(summary_parts),
        "checks_performed": checks_performed
    }


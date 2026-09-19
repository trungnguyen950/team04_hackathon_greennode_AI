import os
from pathlib import Path
from typing import List, Dict, Any, Optional

from utils import excel_utils

# Danh sách tên file Excel ưu tiên tìm kiếm
CANDIDATE_FILES = [
    "Optimized_IT_KnowledgeBase_v1.2.xlsx",
    "Optimized_IT_KnowledgeBase_v1 1.xlsx",
    "Optimized_IT_KnowledgeBase_v1.xlsx"
]

_KB_INCIDENT_CACHE: Optional[List[Dict[str, Any]]] = None
_KB_SERVICE_REQUEST_CACHE: Optional[List[Dict[str, Any]]] = None


def _resolve_excel_path(excel_path: Optional[str] = None) -> Path:
    """Xác định đường dẫn chính xác tới tệp Excel Knowledge Base."""
    if excel_path:
        p = Path(excel_path)
        if p.exists():
            return p

    base_dir = Path(__file__).parent.parent
    parent_dir = base_dir.parent

    # Tìm trong thư mục dự án hiện tại trước
    for fname in CANDIDATE_FILES:
        candidate = base_dir / fname
        if candidate.exists():
            return candidate

    # Tìm trong thư mục cha (nếu có)
    for fname in CANDIDATE_FILES:
        candidate = parent_dir / fname
        if candidate.exists():
            return candidate

    raise FileNotFoundError("Không tìm thấy bất kỳ file Knowledge Base Excel nào trong danh sách ứng viên.")


def load_knowledge_base(excel_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Nạp dữ liệu sự cố (IncidentReport / Sheet1) từ file Excel Knowledge Base.
    """
    global _KB_INCIDENT_CACHE
    if _KB_INCIDENT_CACHE is not None:
        return _KB_INCIDENT_CACHE

    target_path = _resolve_excel_path(excel_path)
    wb = excel_utils.read(str(target_path))
    sheet_names = excel_utils.all_worksheet_names(wb)

    target_sheet = "IncidentReport" if "IncidentReport" in sheet_names else "Sheet1"
    if target_sheet not in sheet_names:
        target_sheet = sheet_names[0]

    matrix = excel_utils.excel_to_matrix(str(target_path), sheet_name=target_sheet)
    if not matrix or len(matrix) < 2:
        return []

    kb_items: List[Dict[str, Any]] = []
    for row in matrix[1:]:
        if not row or not any(row):
            continue

        def get_val(idx: int) -> str:
            if idx < len(row) and row[idx] is not None:
                return str(row[idx]).strip()
            return ""

        item = {
            "kb_id": get_val(0),
            "category": get_val(1),
            "intent_name": get_val(2),
            "user_utterances": get_val(3),
            "required_context": get_val(4),
            "diagnostic_condition": get_val(5),
            "root_cause": get_val(6),
            "resolution_action": get_val(7),
            "assigned_team": get_val(8),
            "sample_scenario": get_val(9),
        }
        kb_items.append(item)

    _KB_INCIDENT_CACHE = kb_items
    print(f"✅ [KB_ENGINE] Đã nạp thành công {len(kb_items)} bản ghi sự cố từ sheet '{target_sheet}' ({target_path.name}).")
    return _KB_INCIDENT_CACHE


def load_service_requests(excel_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Nạp dữ liệu yêu cầu dịch vụ / cài đặt phần mềm (sheet ServiceRequest) từ file Excel Knowledge Base.
    Cột dữ liệu: KB_ID | Category | Software_Name | Work_Purposes | Required_Context | Prerequisites
    """
    global _KB_SERVICE_REQUEST_CACHE
    if _KB_SERVICE_REQUEST_CACHE is not None:
        return _KB_SERVICE_REQUEST_CACHE

    target_path = _resolve_excel_path(excel_path)
    wb = excel_utils.read(str(target_path))
    sheet_names = excel_utils.all_worksheet_names(wb)

    if "ServiceRequest" not in sheet_names:
        print(f"⚠️ [KB_ENGINE] Sheet 'ServiceRequest' không tồn tại trong file {target_path.name}.")
        return []

    matrix = excel_utils.excel_to_matrix(str(target_path), sheet_name="ServiceRequest")
    if not matrix or len(matrix) < 2:
        return []

    header_row = [str(col).strip().lower() if col is not None else "" for col in matrix[0]]
    def get_col_idx(names: List[str], default_idx: int) -> int:
        for name in names:
            if name.lower() in header_row:
                return header_row.index(name.lower())
        return default_idx

    idx_kb = get_col_idx(["kb_id", "id"], 0)
    idx_cat = get_col_idx(["category"], 1)
    idx_name = get_col_idx(["software_name", "software"], 2)
    idx_purposes = get_col_idx(["work_purposes", "purposes"], 3)
    idx_context = get_col_idx(["required_context", "context"], 4)
    idx_prereq = get_col_idx(["prerequisites", "prereq"], 5)
    idx_team = get_col_idx(["assigned_team", "assigned team", "team", "đội ngũ phụ trách"], 6)

    sr_items: List[Dict[str, Any]] = []
    for row in matrix[1:]:
        if not row or not any(row):
            continue

        def get_val(idx: int) -> str:
            if idx < len(row) and row[idx] is not None:
                return str(row[idx]).strip()
            return ""

        item = {
            "kb_id": get_val(idx_kb),
            "category": get_val(idx_cat),
            "software_name": get_val(idx_name),
            "work_purposes": get_val(idx_purposes),
            "required_context": get_val(idx_context),
            "prerequisites": get_val(idx_prereq),
            "assigned_team": get_val(idx_team) or "IT Support Team",
        }
        sr_items.append(item)

    _KB_SERVICE_REQUEST_CACHE = sr_items
    print(f"✅ [KB_ENGINE] Đã nạp thành công {len(sr_items)} bản ghi cài đặt phần mềm từ sheet 'ServiceRequest' ({target_path.name}).")
    return _KB_SERVICE_REQUEST_CACHE


def get_all_categories() -> List[str]:
    """Lấy danh sách các phân loại Category sự cố duy nhất."""
    items = load_knowledge_base()
    cats = list(dict.fromkeys(item["category"] for item in items if item["category"]))
    return cats


def get_all_intents() -> List[str]:
    """Lấy danh sách các Intent Name sự cố duy nhất."""
    items = load_knowledge_base()
    intents = list(dict.fromkeys(item["intent_name"] for item in items if item["intent_name"]))
    return intents


def get_all_software_names() -> List[str]:
    """Lấy danh sách tên phần mềm có trong sheet ServiceRequest."""
    items = load_service_requests()
    names = list(dict.fromkeys(item["software_name"] for item in items if item.get("software_name")))
    return names


def find_best_match(query: str, intent_name: Optional[str] = None, category: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Tìm kiếm bản ghi sự cố khớp nhất trong IncidentReport.
    """
    items = load_knowledge_base()
    if not items:
        return None

    query_lower = query.lower() if query else ""
    best_item = None
    best_score = -1

    for item in items:
        score = 0
        if intent_name and item["intent_name"].lower() == intent_name.lower():
            score += 50
        elif intent_name and intent_name.lower() in item["intent_name"].lower():
            score += 30

        if category and item["category"].lower() == category.lower():
            score += 25
        elif category and category.lower() in item["category"].lower():
            score += 15

        utterances = [u.strip().lower() for u in item["user_utterances"].split("|")]
        for u in utterances:
            if u and u in query_lower:
                score += 20
            else:
                u_words = set(u.split())
                q_words = set(query_lower.split())
                common = u_words.intersection(q_words)
                score += len(common) * 2

        if item["root_cause"].lower() in query_lower:
            score += 15

        if score > best_score:
            best_score = score
            best_item = item

    if best_item and best_score > 0:
        return best_item
        
    return items[0] if items else None


def find_software_match(query: str, software_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Tìm kiếm bản ghi phần mềm khớp nhất trong ServiceRequest dựa trên Software_Name và Work_Purposes.
    """
    items = load_service_requests()
    if not items:
        return None

    query_lower = query.lower() if query else ""
    best_item = None
    best_score = -1

    for item in items:
        score = 0
        s_name = item.get("software_name", "").lower()
        purposes = [p.strip().lower() for p in item.get("work_purposes", "").split("|")]

        # Khớp chính xác tên phần mềm
        if software_name and s_name == software_name.lower():
            score += 60
        elif software_name and software_name.lower() in s_name:
            score += 40
        elif s_name and s_name in query_lower:
            score += 45

        # Kiểm tra từ khóa trong work_purposes
        for p in purposes:
            if p and p in query_lower:
                score += 25
            else:
                p_words = set(p.split())
                q_words = set(query_lower.split())
                common = p_words.intersection(q_words)
                score += len(common) * 3

        if score > best_score:
            best_score = score
            best_item = item

    if best_item and best_score > 0:
        return best_item

    return items[0] if items else None

from typing import TypedDict, Dict, Any, List, Optional

class Agent8StepState(TypedDict, total=False):
    # =========================================================================
    # DÙNG CHUNG (SHARED / ENTRY / ROUTING)
    # =========================================================================
    # Bước 1: User Request (Tiếp nhận yêu cầu bằng ngôn ngữ tự nhiên từ email)
    user_request: Dict[str, Any]
    
    # Định tuyến: 'incident' (Sự cố kỹ thuật) hoặc 'software_install' (Cài đặt phần mềm)
    flow_type: str
    routing_reason: str

    # =========================================================================
    # SUBFLOW A: QUY TRÌNH XỬ LÝ SỰ CỐ (INCIDENT MANAGEMENT - 8 BƯỚC)
    # =========================================================================
    # Bước 2A: Intent (Xác định loại vấn đề & mức ưu tiên)
    intent: Dict[str, Any]
    
    # Bước 3A: Context (Thu thập thông tin cần thiết: UserID, Wifi/LAN, IP, Status...)
    context: Dict[str, Any]
    
    # Bước 4A: Knowledge (Tìm kiếm KB/SOP/Ticket tương tự từ sheet IncidentReport)
    knowledge: Dict[str, Any]
    
    # Bước 5A: Diagnostic (Phân tích triệu chứng và nguyên nhân có khả năng IF-THEN)
    diagnostic: Dict[str, Any]
    
    # Bước 6A: Recommendation (Đưa ra hướng xử lý và giải pháp từng bước)
    recommendation: Dict[str, Any]
    
    # Bước 7A: Ticket (Tạo/Update Incident Ticket nếu cần IT hỗ trợ)
    # Bước 8A: Resolution (Lưu kết quả xử lý, phục vụ Knowledge & đóng gói phản hồi email)

    # =========================================================================
    # SUBFLOW B: QUY TRÌNH CÀI ĐẶT PHẦN MỀM (SOFTWARE INSTALLATION)
    # =========================================================================
    # Bước 2B: Intent (Xác định loại phần mềm, work purposes, priority)
    software_intent: Dict[str, Any]
    
    # Bước 3B: Context (Thu thập thông tin phòng ban, IP máy in, thông tin máy)
    software_context: Dict[str, Any]
    
    # Bước 4B: Check Prerequisites (Kiểm tra đủ điều kiện cài đặt / license / approvals)
    software_prerequisites: Dict[str, Any]
    
    # Bước 5B: Ticket (Tạo/Update Service Request Ticket)
    # Bước 6B: Resolution (Lưu kết quả xử lý & đóng gói phản hồi email cài đặt)

    # =========================================================================
    # KẾT QUẢ CUỐI CÙNG (DÙNG CHUNG CHO CẢ 2 SUBFLOW)
    # =========================================================================
    ticket: Dict[str, Any]
    resolution: Dict[str, Any]
    error: Optional[str]

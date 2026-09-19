from langgraph.graph import StateGraph, START, END
from agent_8_steps.state import Agent8StepState
from agent_8_steps.nodes import (
    step1_user_request,
    center_router,
    # Subflow A: Incident Flow Nodes
    step2_intent,
    step3_context,
    step4_knowledge,
    step5_diagnostic,
    step6_recommendation,
    step7_ticket,
    step8_resolution,
    # Subflow B: Software Installation Flow Nodes
    step2b_software_intent,
    step3b_software_context,
    step4b_check_prerequisites,
    step5b_software_ticket,
    step6b_software_resolution,
)

# =====================================================================
# 1. SUBFLOW A: QUY TRÌNH XỬ LÝ SỰ CỐ (INCIDENT FLOW - 8 BƯỚC)
# =====================================================================
incident_graph = StateGraph(Agent8StepState)

# Các Node của Subflow A (2A -> 8A)
incident_graph.add_node("step2a_intent", step2_intent.process)
incident_graph.add_node("step3a_context", step3_context.process)
incident_graph.add_node("step4a_knowledge", step4_knowledge.process)
incident_graph.add_node("step5a_diagnostic", step5_diagnostic.process)
incident_graph.add_node("step6a_recommendation", step6_recommendation.process)
incident_graph.add_node("step7a_ticket", step7_ticket.process)
incident_graph.add_node("step8a_resolution", step8_resolution.process)

# Luồng di chuyển tuyến tính chuẩn hóa của Subflow A
incident_graph.add_edge(START, "step2a_intent")
incident_graph.add_edge("step2a_intent", "step3a_context")
incident_graph.add_edge("step3a_context", "step4a_knowledge")
incident_graph.add_edge("step4a_knowledge", "step5a_diagnostic")
incident_graph.add_edge("step5a_diagnostic", "step6a_recommendation")
incident_graph.add_edge("step6a_recommendation", "step7a_ticket")
incident_graph.add_edge("step7a_ticket", "step8a_resolution")
incident_graph.add_edge("step8a_resolution", END)

incident_subflow = incident_graph.compile()


# =====================================================================
# 2. SUBFLOW B: QUY TRÌNH CÀI ĐẶT PHẦN MỀM (SOFTWARE INSTALL FLOW - 6 BƯỚC)
# =====================================================================
software_graph = StateGraph(Agent8StepState)

# Các Node của Subflow B (2B -> 6B)
software_graph.add_node("step2b_software_intent", step2b_software_intent.process)
software_graph.add_node("step3b_software_context", step3b_software_context.process)
software_graph.add_node("step4b_check_prerequisites", step4b_check_prerequisites.process)
software_graph.add_node("step5b_software_ticket", step5b_software_ticket.process)
software_graph.add_node("step6b_software_resolution", step6b_software_resolution.process)

# Luồng di chuyển chuẩn hóa của Subflow B
software_graph.add_edge(START, "step2b_software_intent")
software_graph.add_edge("step2b_software_intent", "step3b_software_context")
software_graph.add_edge("step3b_software_context", "step4b_check_prerequisites")
software_graph.add_edge("step4b_check_prerequisites", "step5b_software_ticket")
software_graph.add_edge("step5b_software_ticket", "step6b_software_resolution")
software_graph.add_edge("step6b_software_resolution", END)

software_install_subflow = software_graph.compile()


# =====================================================================
# 3. MAIN WORKFLOW: ĐIỀU PHỐI TRUNG TÂM (CENTER SUPERVISOR / ROUTER)
# =====================================================================
def route_flow_decision(state: Agent8StepState) -> str:
    """Hàm điều hướng nhánh tiếp theo dựa trên phân loại của Center Router."""
    flow = state.get("flow_type", "incident")
    if flow == "software_install":
        return "software_install_subflow"
    return "incident_subflow"


main_workflow = StateGraph(Agent8StepState)

# Thêm Node Tiếp nhận (Bước 1) và Node Điều phối Trung tâm (Center Router)
main_workflow.add_node("step1_user_request", step1_user_request.process)
main_workflow.add_node("center_router", center_router.process)

# Thêm 2 Subflow dưới dạng các Subgraph Nodes trong LangGraph
main_workflow.add_node("incident_subflow", incident_subflow)
main_workflow.add_node("software_install_subflow", software_install_subflow)

# Cấu hình Edges chính
main_workflow.add_edge(START, "step1_user_request")
main_workflow.add_edge("step1_user_request", "center_router")

# Điều hướng rẽ nhánh có điều kiện (Conditional Edges)
main_workflow.add_conditional_edges(
    "center_router",
    route_flow_decision,
    {
        "incident_subflow": "incident_subflow",
        "software_install_subflow": "software_install_subflow"
    }
)

# Kết thúc từ 2 Subflow
main_workflow.add_edge("incident_subflow", END)
main_workflow.add_edge("software_install_subflow", END)

# Biên dịch đồ thị chính hoàn chỉnh
app = main_workflow.compile()

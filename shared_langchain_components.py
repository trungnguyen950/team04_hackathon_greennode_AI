import os
from typing import TypedDict
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

# =====================================================================
# STATE ĐIỀU PHỐI (SHARED STATE CHO CÁC AGENT)
# =====================================================================
class MultiAgentState(TypedDict):
    user_input: str              # Yêu cầu gốc từ người dùng
    assigned_agent: str          # Agent con được Center Agent chỉ định
    routing_reason: str          # Lý do Center Agent chọn agent này
    subagent_result: str         # Kết quả xử lý từ Agent con
    final_answer: str            # Câu trả lời hoàn chỉnh sau khi Center Agent tổng hợp

# =====================================================================
# CẤU HÌNH API KEY VÀ MODEL GREENNODE
# =====================================================================


def extract_content(response) -> str:
    """Trích xuất text an toàn từ kết quả trả về của GreenNode."""
    if isinstance(response, str):
        return response
    content = getattr(response, "content", response)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and "text" in item:
                parts.append(item["text"])
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(parts)
    return str(content)


def call_llm(prompt: str) -> str:
    try:
        model = ChatOpenAI(
            model="qwen/qwen3.6-flash",
            base_url="https://maas-llm-aiplatform-hcm.api.vngcloud.vn/v1",
            temperature=0
        )
        response = model.invoke(prompt)
        return extract_content(response)
    except Exception as e:
        raise e

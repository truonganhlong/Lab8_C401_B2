"""
workers/policy_tool.py — Policy & Tool Worker
Sprint 2+3: Kiểm tra policy dựa vào context, gọi MCP tools khi cần.

Input (từ AgentState):
    - task: câu hỏi
    - retrieved_chunks: context từ retrieval_worker
    - needs_tool: True nếu supervisor quyết định cần tool call

Output (vào AgentState):
    - policy_result: {"policy_applies", "policy_name", "exceptions_found", "source", "rule"}
    - mcp_tools_used: list of tool calls đã thực hiện
    - worker_io_log: log

Gọi độc lập để test:
    python workers/policy_tool.py
"""

import os
import sys
from typing import Optional

# Add parent directory to sys.path to allow importing mcp_server if run from workers/
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

try:
    from mcp_server import dispatch_tool
except ImportError:
    dispatch_tool = None # Fallback if not found

WORKER_NAME = "policy_tool_worker"


# ─────────────────────────────────────────────
# MCP Client — Sprint 3: Thay bằng real MCP call
# ─────────────────────────────────────────────

def _call_mcp_tool(tool_name: str, tool_input: dict) -> dict:
    """
    Gọi MCP tool.
    Hiện tại: Import trực tiếp từ mcp_server.py (trong-process mock).
    """
    from datetime import datetime

    try:
        if dispatch_tool is None:
            raise ImportError("mcp_server.dispatch_tool not found. Check sys.path.")
        
        result = dispatch_tool(tool_name, tool_input)
        return {
            "tool": tool_name,
            "input": tool_input,
            "output": result,
            "error": None,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "tool": tool_name,
            "input": tool_input,
            "output": None,
            "error": {"code": "MCP_CALL_FAILED", "reason": str(e)},
            "timestamp": datetime.now().isoformat(),
        }


# ─────────────────────────────────────────────
# Policy Analysis Logic
# ─────────────────────────────────────────────

def analyze_policy(task: str, chunks: list) -> dict:
    """
    Phân tích policy dựa trên context chunks.
    Xử lý các exceptions:
    - Refund: Flash Sale, Digital product, Activated product, Temporal scoping.
    - Access: Phân cấp Level 1-4, quy trình phê duyệt, Emergency escalation.
    """
    task_lower = task.lower()
    context_text = " ".join([c.get("text", "") for c in chunks]).lower()

    exceptions_found = []
    policy_name = "general_policy_check"
    
    # --- 1. REFUND POLICIES ---
    if any(kw in task_lower for kw in ["hoàn tiền", "refund", "trả hàng"]):
        policy_name = "refund_policy_v4"
        
        # Exception: Flash Sale
        if "flash sale" in task_lower or "flash sale" in context_text:
            exceptions_found.append({
                "type": "flash_sale_exception",
                "rule": "Đơn hàng Flash Sale không được hoàn tiền (Điều 3, chính sách v4).",
                "source": "policy_refund_v4.txt",
            })

        # Exception: Digital product
        if any(kw in task_lower for kw in ["license", "kỹ thuật số", "key", "subscription"]):
            exceptions_found.append({
                "type": "digital_product_exception",
                "rule": "Sản phẩm kỹ thuật số không được hoàn tiền (Điều 3).",
                "source": "policy_refund_v4.txt",
            })

        # Exception: Activated product
        if any(kw in task_lower for kw in ["đã kích hoạt", "đã sử dụng", "activated"]):
            exceptions_found.append({
                "type": "activated_exception",
                "rule": "Sản phẩm đã kích hoạt/sử dụng không được hoàn tiền (Điều 3).",
                "source": "policy_refund_v4.txt",
            })
            
        # Temporal scoping (orders before 01/02/2026)
        if "trước 01/02" in task_lower or "trước ngày 1/2" in task_lower or "31/01" in task_lower:
            exceptions_found.append({
                "type": "temporal_scoping_warning",
                "rule": "Đơn hàng trước 01/02/2026 áp dụng chính sách v3 (không có trong docs). Cần escalate.",
                "source": "temporal_metadata",
            })

    # --- 2. ACCESS CONTROL POLICIES ---
    is_access_task = any(kw in task_lower for kw in ["cấp quyền", "access", "level", "quyền truy cập"])
    if is_access_task:
        policy_name = "access_control_sop"
        
        # Detect target level
        target_level = None
        if "level 1" in task_lower: target_level = 1
        elif "level 2" in task_lower: target_level = 2
        elif "level 3" in task_lower: target_level = 3
        elif "level 4" in task_lower: target_level = 4
        
        if target_level:
            # Check if mentions specific roles or manager approval
            if "manager" not in task_lower and "it admin" not in task_lower:
                exceptions_found.append({
                    "type": "missing_approval_context",
                    "rule": f"Yêu cầu cấp quyền Level {target_level} cần có sự phê duyệt của các cấp tương ứng (SOP Section 2).",
                    "source": "access_control_sop.txt",
                })
        
        # Emergency check
        if any(kw in task_lower for kw in ["khẩn cấp", "emergency", "p1", "incident"]):
            if "tech lead" not in task_lower:
                exceptions_found.append({
                    "type": "emergency_rule_missing_approver",
                    "rule": "Quy trình escalation khẩn cấp yêu cầu Tech Lead phê duyệt bằng lời (max 24h).",
                    "source": "access_control_sop.txt",
                })

    policy_applies = len(exceptions_found) == 0
    sources = list({c.get("source", "unknown") for c in chunks if c})

    return {
        "policy_applies": policy_applies,
        "policy_name": policy_name,
        "exceptions_found": exceptions_found,
        "source": sources,
        "explanation": f"Validated against {policy_name}. Found {len(exceptions_found)} exceptions/notes.",
    }


# ─────────────────────────────────────────────
# Worker Entry Point
# ─────────────────────────────────────────────

def run(state: dict) -> dict:
    """
    Worker entry point — gọi từ graph.py.
    """
    task = state.get("task", "")
    chunks = state.get("retrieved_chunks", [])
    needs_tool = state.get("needs_tool", False)

    state.setdefault("workers_called", [])
    state.setdefault("history", [])
    state.setdefault("mcp_tools_used", [])

    state["workers_called"].append(WORKER_NAME)

    worker_io = {
        "worker": WORKER_NAME,
        "input": {
            "task": task,
            "chunks_count": len(chunks),
            "needs_tool": needs_tool,
        },
        "output": None,
        "error": None,
    }

    try:
        # Step 1: Nếu chưa có chunks và cần tìm KB, gọi MCP search_kb
        if not chunks and needs_tool:
            mcp_result = _call_mcp_tool("search_kb", {"query": task, "top_k": 3})
            state["mcp_tools_used"].append(mcp_result)
            state["history"].append(f"[{WORKER_NAME}] called MCP search_kb")

            if mcp_result.get("output") and mcp_result["output"].get("chunks"):
                chunks = mcp_result["output"]["chunks"]
                state["retrieved_chunks"] = chunks

        # Step 2: Phân tích policy cơ bản (rule-based)
        policy_result = analyze_policy(task, chunks)
        
        # Step 3: Nếu là Access task và cần tool, gọi MCP check_access_permission
        if needs_tool and policy_result["policy_name"] == "access_control_sop":
            # Trích xuất level từ task
            target_level = None
            if "level 1" in task.lower(): target_level = 1
            elif "level 2" in task.lower(): target_level = 2
            elif "level 3" in task.lower(): target_level = 3
            elif "level 4" in task.lower(): target_level = 4
            
            if target_level:
                is_emergency = any(kw in task.lower() for kw in ["khẩn cấp", "emergency", "p1"])
                mcp_res = _call_mcp_tool("check_access_permission", {
                    "access_level": target_level,
                    "requester_role": "employee", # Default role
                    "is_emergency": is_emergency
                })
                state["mcp_tools_used"].append(mcp_res)
                state["history"].append(f"[{WORKER_NAME}] called MCP check_access_permission (Level {target_level})")
                
                # Cập nhật policy_result với thông tin từ MCP
                if mcp_res.get("output"):
                    mcp_out = mcp_res["output"]
                    policy_result["mcp_validation"] = {
                        "can_grant": mcp_out.get("can_grant"),
                        "required_approvers": mcp_out.get("required_approvers"),
                    }
                    if mcp_out.get("emergency_override"):
                        policy_result["explanation"] += " (Emergency override active)"

        state["policy_result"] = policy_result

        # Step 4: Nếu cần thêm info ticket, gọi get_ticket_info
        if needs_tool and any(kw in task.lower() for kw in ["ticket", "p1", "jira"]):
            mcp_result = _call_mcp_tool("get_ticket_info", {"ticket_id": "P1-LATEST"})
            state["mcp_tools_used"].append(mcp_result)
            state["history"].append(f"[{WORKER_NAME}] called MCP get_ticket_info")

        worker_io["output"] = {
            "policy_applies": policy_result["policy_applies"],
            "policy_name": policy_result["policy_name"],
            "exceptions_count": len(policy_result.get("exceptions_found", [])),
            "mcp_calls": len(state["mcp_tools_used"]),
        }
        state["history"].append(
            f"[{WORKER_NAME}] logic complete. Name={policy_result['policy_name']}"
        )

    except Exception as e:
        worker_io["error"] = {"code": "POLICY_CHECK_FAILED", "reason": str(e)}
        state["policy_result"] = {"error": str(e)}
        state["history"].append(f"[{WORKER_NAME}] ERROR: {e}")

    state.setdefault("worker_io_logs", []).append(worker_io)
    return state


# ─────────────────────────────────────────────
# Test độc lập
# ─────────────────────────────────────────────

if __name__ == "__main__":
    # Fix Windows terminal encoding
    import sys
    if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    print("=" * 50)
    print("Policy Tool Worker — Standalone Test")
    print("=" * 50)

    test_cases = [
        {
            "task": "Khách hàng Flash Sale yêu cầu hoàn tiền vì sản phẩm lỗi — được không?",
            "retrieved_chunks": [
                {"text": "Ngoại lệ: Đơn hàng Flash Sale không được hoàn tiền.", "source": "policy_refund_v4.txt", "score": 0.9}
            ],
        },
        {
            "task": "Khách hàng muốn hoàn tiền license key đã kích hoạt.",
            "retrieved_chunks": [
                {"text": "Sản phẩm kỹ thuật số (license key, subscription) không được hoàn tiền.", "source": "policy_refund_v4.txt", "score": 0.88}
            ],
        },
        {
            "task": "Khách hàng yêu cầu hoàn tiền trong 5 ngày, sản phẩm lỗi, chưa kích hoạt.",
            "retrieved_chunks": [
                {"text": "Yêu cầu trong 7 ngày làm việc, sản phẩm lỗi nhà sản xuất, chưa dùng.", "source": "policy_refund_v4.txt", "score": 0.85}
            ],
        },
        {
            "task": "Contractor cần cấp quyền Level 2 để sửa incident P1.",
            "needs_tool": True,
            "retrieved_chunks": [], # Test MCP search_kb + check_access
        },
    ]

    for tc in test_cases:
        print(f"\n▶ Task: {tc['task'][:70]}...")
        result = run(tc.copy())
        pr = result.get("policy_result", {})
        print(f"  policy_name   : {pr.get('policy_name')}")
        print(f"  policy_applies: {pr.get('policy_applies')}")
        if pr.get("exceptions_found"):
            for ex in pr["exceptions_found"]:
                print(f"  exception: {ex['type']} — {ex['rule'][:60]}...")
        if pr.get("mcp_validation"):
            print(f"  mcp_validation: {pr['mcp_validation']}")
        print(f"  MCP calls: {len(result.get('mcp_tools_used', []))}")
        for mcp in result.get("mcp_tools_used", []):
            print(f"    - {mcp['tool']} ({mcp.get('error') or 'success'})")

    print("\n✅ policy_tool_worker test done.")

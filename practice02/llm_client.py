"""
practice02/llm_client.py
========================
带工具调用（Function Calling / Tool Use）的 LLM 多轮对话客户端

支持的工具（文件系统操作）:
    1. list_files   - 列出目录下文件及属性
    2. rename_file  - 重命名文件
    3. delete_file  - 删除文件
    4. create_file  - 新建文件并写入内容
    5. read_file    - 读取文件内容

工具调用流程（ReAct 模式）:
    用户输入
      → LLM 判断是否需要工具
        → 若需要：输出 <tool_call>...</tool_call>
        → 程序解析并执行工具
        → 将结果拼入 messages，再次调用 LLM
        → LLM 生成最终自然语言回复
      → 若不需要：直接输出回答
"""

import os
import re
import sys
import json
import http.client
import time
from urllib.parse import urlparse

# 引入同目录的工具模块（需在标准 import 后立即注入路径）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from file_tools import dispatch_tool  # noqa: E402


# ═══════════════════════════════════════════════════════════════
# 系统提示词（Prompt Engineering 核心）
# ═══════════════════════════════════════════════════════════════
SYSTEM_PROMPT = """你是一个智能文件管理助手，可以通过调用工具来操作本地文件系统。

## 你拥有以下 5 个工具

### 工具 1：list_files
描述：列出指定目录下所有文件和子目录的基本属性信息（名称、类型、大小、修改时间、权限）。
参数：
  - directory (string, 必填)：要列出内容的目录路径

### 工具 2：rename_file
描述：将指定目录下的某个文件或目录重命名为新名称。
参数：
  - directory (string, 必填)：文件所在目录路径
  - old_name  (string, 必填)：原文件名（不含路径）
  - new_name  (string, 必填)：新文件名（不含路径）

### 工具 3：delete_file
描述：删除指定目录下的某个文件（仅文件，不删除目录）。
参数：
  - directory (string, 必填)：文件所在目录路径
  - filename  (string, 必填)：要删除的文件名（不含路径）

### 工具 4：create_file
描述：在指定目录下新建一个文件，并写入指定内容。
参数：
  - directory (string, 必填)：目标目录路径（不存在时自动创建）
  - filename  (string, 必填)：新文件名（不含路径）
  - content   (string, 可选)：要写入的文本内容，默认为空

### 工具 5：read_file
描述：读取指定目录下某个文件的文本内容。
参数：
  - directory (string, 必填)：文件所在目录路径
  - filename  (string, 必填)：要读取的文件名（不含路径）

---

## 工具调用规则（严格遵守）

1. 当用户的请求需要操作文件系统时，你**必须**调用工具，不能凭空猜测结果。
2. 调用工具时，**只输出**如下 JSON 格式，不要添加任何其他内容：

<tool_call>
{"tool": "工具名称", "arguments": {"参数名": "参数值", ...}}
</tool_call>

3. 每次只能调用 **1 个工具**。如需多步操作，逐步进行。
4. 工具调用结果会以如下格式返回给你：

<tool_result>
{"success": true/false, "data": ..., "error": null/"错误信息"}
</tool_result>

5. 收到工具结果后，根据结果内容用**自然语言**回复用户，给出清晰、友好的汇报。
6. 如果工具返回 success=false，要告知用户失败原因并给出建议。
7. 如果用户请求与文件操作无关，直接用自然语言回答，无需调用工具。

---

## 回复风格

- 简洁专业，使用中文回复
- 列出文件时，使用整齐的表格或列表形式展示
- 操作成功后给出明确的确认信息
- 涉及删除操作时，提醒用户此操作不可逆
"""

# ═══════════════════════════════════════════════════════════════
# 工具定义（OpenAI Functions 格式，可选用于支持原生 function calling 的模型）
# ═══════════════════════════════════════════════════════════════
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "列出指定目录下所有文件和子目录的基本属性信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "要列出内容的目录路径"
                    }
                },
                "required": ["directory"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "rename_file",
            "description": "将指定目录下的文件或目录重命名",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "文件所在目录路径"
                    },
                    "old_name": {
                        "type": "string",
                        "description": "原文件名（不含路径）"
                    },
                    "new_name": {
                        "type": "string",
                        "description": "新文件名（不含路径）"
                    }
                },
                "required": ["directory", "old_name", "new_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_file",
            "description": "删除指定目录下的某个文件（仅文件，不删除目录）",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "文件所在目录路径"
                    },
                    "filename": {
                        "type": "string",
                        "description": "要删除的文件名（不含路径）"
                    }
                },
                "required": ["directory", "filename"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_file",
            "description": "在指定目录下新建文件并写入内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "目标目录路径"
                    },
                    "filename": {
                        "type": "string",
                        "description": "新文件名（不含路径）"
                    },
                    "content": {
                        "type": "string",
                        "description": "要写入的文本内容"
                    }
                },
                "required": ["directory", "filename"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "读取指定目录下某个文件的文本内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "文件所在目录路径"
                    },
                    "filename": {
                        "type": "string",
                        "description": "要读取的文件名（不含路径）"
                    }
                },
                "required": ["directory", "filename"]
            }
        }
    }
]


# ═══════════════════════════════════════════════════════════════
# 读取 .env 配置（复用 practice01 逻辑）
# ═══════════════════════════════════════════════════════════════
def load_env():
    env_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), '.env'
    )
    env_vars = {}
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip().strip('"')
    else:
        print(
            "Error: .env file not found. "
            "Please create one based on .env.example"
        )
    return env_vars


# ═══════════════════════════════════════════════════════════════
# 流式 HTTP 调用 LLM（复用 practice01 核心逻辑，增加工具支持）
# ═══════════════════════════════════════════════════════════════
def call_llm_stream(messages, env_vars, show_stats=True):
    """
    向 LLM 发送消息并流式接收响应。
    返回: (full_response: str, stats: dict)
    """
    base_url = env_vars.get('BASE_URL', 'http://127.0.0.1:1234/v1')
    model = env_vars.get('MODEL', 'qwen3-8b')
    token = env_vars.get('TOKEN', 'lm-studio')
    timeout = 120

    parsed_url = urlparse(base_url)
    host = parsed_url.netloc
    path = parsed_url.path or '/'

    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
        "max_tokens": 4096,
        "temperature": 0.7
    }

    start_time = time.time()
    full_resp = ""

    try:
        conn = http.client.HTTPConnection(host, timeout=timeout)
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }

        conn.request(
            "POST",
            f"{path}/chat/completions",
            json.dumps(payload),
            headers
        )

        response = conn.getresponse()
        if response.status != 200:
            body = response.read().decode("utf-8")
            print(f"\n[HTTP Error {response.status}]: {body}")
            conn.close()
            return "", {}

        while True:
            chunk = response.readline()
            if not chunk:
                break
            line = chunk.decode("utf-8").strip()
            if line.startswith("data: "):
                data_str = line[6:]
                if data_str == "[DONE]":
                    break
                try:
                    data_json = json.loads(data_str)
                    delta = data_json["choices"][0]["delta"]
                    if "content" in delta and delta["content"]:
                        txt = delta["content"]
                        print(txt, end="", flush=True)
                        full_resp += txt
                except Exception:
                    continue

        conn.close()

        # 统计信息
        end_time = time.time()
        total_time = end_time - start_time
        prompt_tokens = len(str(messages)) // 4
        completion_tokens = len(full_resp) // 4
        total_tokens = prompt_tokens + completion_tokens
        tps = total_tokens / total_time if total_time > 0 else 0

        stats = {
            "total_time": round(total_time, 2),
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "tokens_per_second": round(tps, 2)
        }

        return full_resp, stats

    except Exception as e:
        print(f"\n[LLM Error]: {e}")
        return "", {}


# ═══════════════════════════════════════════════════════════════
# 工具调用解析器
# ═══════════════════════════════════════════════════════════════
def parse_tool_call(text: str):
    """
    从 LLM 输出中提取 <tool_call>...</tool_call> 内容。
    返回: (tool_name: str, arguments: dict) 或 (None, None)
    """
    pattern = r"<tool_call>\s*(\{.*?\})\s*</tool_call>"
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        return None, None

    try:
        call_json = json.loads(match.group(1))
        tool_name = call_json.get("tool")
        arguments = call_json.get("arguments", {})
        return tool_name, arguments
    except json.JSONDecodeError as e:
        print(f"\n[解析工具调用失败]: {e}")
        print(f"原始内容: {match.group(1)}")
        return None, None


# ═══════════════════════════════════════════════════════════════
# 核心：带工具循环的对话处理
# ═══════════════════════════════════════════════════════════════
def process_with_tools(user_input: str, messages: list, env_vars: dict):
    """
    处理单轮用户输入，支持多步工具调用（ReAct 循环）。

    流程:
        1. 将用户输入追加到 messages
        2. 调用 LLM，检测是否有工具调用
        3. 若有：执行工具 → 将结果追加 → 继续调用 LLM
        4. 重复直到 LLM 不再调用工具（最多 MAX_TOOL_ROUNDS 轮）
        5. 返回最终统计信息
    """
    MAX_TOOL_ROUNDS = 10   # 防止死循环

    messages.append({"role": "user", "content": user_input})

    total_stats = {
        "total_time": 0, "prompt_tokens": 0,
        "completion_tokens": 0, "total_tokens": 0,
        "tool_calls": 0
    }

    for round_num in range(MAX_TOOL_ROUNDS + 1):

        # ── 调用 LLM ──
        print("\n助手: ", end="", flush=True)
        llm_response, stats = call_llm_stream(messages, env_vars)

        if not llm_response:
            print("获取回复失败！")
            if messages and messages[-1]["role"] == "user":
                messages.pop()
            return total_stats

        # 累计统计
        total_stats["total_time"] += stats.get("total_time", 0)
        total_stats["prompt_tokens"] += stats.get("prompt_tokens", 0)
        total_stats["completion_tokens"] += stats.get(
            "completion_tokens", 0
        )
        total_stats["total_tokens"] += stats.get("total_tokens", 0)

        # ── 检测工具调用 ──
        tool_name, arguments = parse_tool_call(llm_response)

        if tool_name is None:
            # LLM 不再调用工具，将最终回复加入历史
            messages.append({"role": "assistant", "content": llm_response})
            print("\n")
            break

        # ── 执行工具 ──
        total_stats["tool_calls"] += 1
        args_str = json.dumps(arguments, ensure_ascii=False)
        print(f"\n\n[🔧 工具调用] {tool_name}({args_str})")

        tool_result = dispatch_tool(tool_name, arguments)

        result_str = json.dumps(tool_result, ensure_ascii=False, indent=2)
        success_icon = "✅" if tool_result.get("success") else "❌"
        truncated = result_str[:300]
        suffix = "..." if len(result_str) > 300 else ""
        print(f"[{success_icon} 工具结果] {truncated}{suffix}")

        # 将工具调用和结果拼入 messages
        messages.append({"role": "assistant", "content": llm_response})
        messages.append({
            "role": "user",
            "content": f"<tool_result>\n{result_str}\n</tool_result>"
        })

        if round_num == MAX_TOOL_ROUNDS:
            print(f"\n[警告] 已达到最大工具调用轮数 ({MAX_TOOL_ROUNDS})，强制终止工具循环。")
            break

    return total_stats


# ═══════════════════════════════════════════════════════════════
# 主函数
# ═══════════════════════════════════════════════════════════════
def main():
    env_vars = load_env()
    if not env_vars:
        return

    # 初始化带系统提示词的消息列表
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]

    print("=" * 60)
    print("  🗂  文件管理助手（工具调用模式）")
    print("=" * 60)
    print("我可以帮你完成以下文件操作：")
    print("  • 列出目录内容    • 新建文件并写入")
    print("  • 读取文件内容    • 重命名文件")
    print("  • 删除文件")
    print("\n输入 'exit' 或 '退出' 结束对话")
    print("输入 'history' 查看对话历史条数")
    print("输入 'clear' 清空对话历史（保留系统提示）")
    print("-" * 60)

    try:
        while True:
            user_input = input("\n你: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ['exit', '退出']:
                print("对话结束，再见！")
                break

            if user_input.lower() == 'history':
                # 不含 system 消息的轮数
                user_turns = sum(1 for m in messages if m["role"] == "user")
                print(f"[当前对话历史: {len(messages)} 条消息，其中用户发言 {user_turns} 次]")
                continue

            if user_input.lower() == 'clear':
                messages = [{"role": "system", "content": SYSTEM_PROMPT}]
                print("[✅ 对话历史已清空，系统提示词已保留]")
                continue

            # 处理用户请求（含工具循环）
            stats = process_with_tools(user_input, messages, env_vars)

            # 输出本轮统计
            print("-" * 40)
            print(f"⏱  耗时: {round(stats['total_time'], 2)}s  "
                  f"| 🔧 工具调用: {stats['tool_calls']} 次  "
                  f"| 🪙 Token: {stats['total_tokens']}")

    except KeyboardInterrupt:
        print("\n\n检测到 Ctrl+C，对话结束！")
        print("感谢使用，再见！")


if __name__ == "__main__":
    main()

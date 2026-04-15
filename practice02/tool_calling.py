import os
import json
import http.client
import time
from urllib.parse import urlparse
from datetime import datetime


# 读取.env文件
def load_env():
    """加载环境变量配置"""
    # 尝试从当前目录的父目录查找.env
    env_paths = [
        os.path.join(os.path.dirname(__file__), '.env'),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    ]

    for env_path in env_paths:
        if os.path.exists(env_path):
            env_vars = {}
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if '=' in line:
                            key, value = line.split('=', 1)
                            env_vars[key.strip()] = value.strip().strip('"')
            return env_vars

    print("警告: .env文件未找到，使用默认配置")
    return {
        'BASE_URL': 'http://127.0.0.1:1234/v1',
        'MODEL': 'qwen3.5-9b',
        'TOKEN': 'lm-studio'
    }


# ============ 工具函数定义 ============

def list_directory_contents(dir_path):
    """
    列出目录下的文件和子目录

    Args:
        dir_path: 目录路径

    Returns:
        dict: 包含文件列表和错误信息
    """
    try:
        # 检查路径是否存在
        if not os.path.exists(dir_path):
            return {
                "success": False,
                "error": f"目录不存在: {dir_path}",
                "files": []
            }

        # 检查是否是目录
        if not os.path.isdir(dir_path):
            return {
                "success": False,
                "error": f"路径不是目录: {dir_path}",
                "files": []
            }

        files_info = []
        for item in os.listdir(dir_path):
            item_path = os.path.join(dir_path, item)
            try:
                stat_info = os.stat(item_path)
                is_dir = os.path.isdir(item_path)

                # 获取文件大小
                if is_dir:
                    size_str = "<DIR>"
                else:
                    size_bytes = stat_info.st_size
                    if size_bytes < 1024:
                        size_str = f"{size_bytes} B"
                    elif size_bytes < 1024 * 1024:
                        size_str = f"{size_bytes/1024:.1f} KB"
                    else:
                        size_str = f"{size_bytes/(1024 * 1024):.1f} MB"

                # 获取修改时间
                mod_time = datetime.fromtimestamp(stat_info.st_mtime)
                mod_time_str = mod_time.strftime("%Y-%m-%d %H:%M:%S")

                files_info.append({
                    "name": item,
                    "is_directory": is_dir,
                    "size": size_str,
                    "size_bytes": stat_info.st_size if not is_dir else 0,
                    "modified": mod_time_str,
                    "path": item_path
                })
            except Exception as e:
                files_info.append({
                    "name": item,
                    "error": f"无法获取信息: {str(e)}"
                })

        # 排序：目录在前，文件在后，按名称排序
        files_info.sort(key=lambda x: (
            not x.get('is_directory', False),
            x.get('name', '').lower()
        ))

        return {
            "success": True,
            "directory": dir_path,
            "file_count": len(files_info),
            "files": files_info
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"列出目录失败: {str(e)}",
            "files": []
        }


def rename_file(file_path, new_name):
    """
    重命名文件

    Args:
        file_path: 文件路径
        new_name: 新文件名

    Returns:
        dict: 操作结果
    """
    try:
        # 检查文件是否存在
        if not os.path.exists(file_path):
            return {
                "success": False,
                "error": f"文件不存在: {file_path}"
            }

        # 获取目录路径和新文件路径
        dir_path = os.path.dirname(file_path)
        new_file_path = os.path.join(dir_path, new_name)

        # 检查新文件是否已存在
        if os.path.exists(new_file_path):
            return {
                "success": False,
                "error": f"目标文件已存在: {new_name}"
            }

        # 执行重命名
        os.rename(file_path, new_file_path)

        return {
            "success": True,
            "message": f"文件重命名成功: "
                       f"{os.path.basename(file_path)} -> {new_name}",
            "old_path": file_path,
            "new_path": new_file_path
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"重命名文件失败: {str(e)}"
        }


def delete_file(file_path):
    """
    删除文件

    Args:
        file_path: 文件路径

    Returns:
        dict: 操作结果
    """
    try:
        # 检查文件是否存在
        if not os.path.exists(file_path):
            return {
                "success": False,
                "error": f"文件不存在: {file_path}"
            }

        # 检查是否是文件（不允许删除目录）
        if not os.path.isfile(file_path):
            return {
                "success": False,
                "error": f"路径不是文件（目录不支持删除）: {file_path}"
            }

        # 获取文件大小
        file_size = os.path.getsize(file_path)

        # 执行删除
        os.remove(file_path)

        return {
            "success": True,
            "message": f"文件删除成功: {os.path.basename(file_path)}",
            "file_path": file_path,
            "size_bytes": file_size
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"删除文件失败: {str(e)}"
        }


def create_file(file_path, content=""):
    """
    创建文件并写入内容

    Args:
        file_path: 文件路径
        content: 文件内容

    Returns:
        dict: 操作结果
    """
    try:
        # 获取目录路径
        dir_path = os.path.dirname(file_path)

        # 检查目录是否存在，如果不存在则创建
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)

        # 检查文件是否已存在
        if os.path.exists(file_path):
            return {
                "success": False,
                "error": f"文件已存在: {file_path}"
            }

        # 创建文件并写入内容
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return {
            "success": True,
            "message": f"文件创建成功: {os.path.basename(file_path)}",
            "file_path": file_path,
            "size_bytes": len(content.encode('utf-8')),
            "content_length": len(content)
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"创建文件失败: {str(e)}"
        }


def read_file(file_path, max_size=1024 * 1024):  # 默认最大1MB
    """
    读取文件内容

    Args:
        file_path: 文件路径
        max_size: 最大读取大小（字节）

    Returns:
        dict: 文件内容和信息
    """
    try:
        # 检查文件是否存在
        if not os.path.exists(file_path):
            return {
                "success": False,
                "error": f"文件不存在: {file_path}"
            }

        # 检查是否是文件
        if not os.path.isfile(file_path):
            return {
                "success": False,
                "error": f"路径不是文件: {file_path}"
            }

        # 获取文件大小
        file_size = os.path.getsize(file_path)

        # 检查文件大小
        if file_size > max_size:
            return {
                "success": False,
                "error": f"文件过大 ({file_size} 字节)，"
                         f"最大支持 {max_size} 字节",
                "file_size": file_size,
                "max_size": max_size
            }

        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 获取文件信息
        file_info = os.stat(file_path)
        mod_time = datetime.fromtimestamp(file_info.st_mtime)

        return {
            "success": True,
            "content": content,
            "file_path": file_path,
            "file_size": file_size,
            "encoding": "utf-8",
            "modified": mod_time.strftime("%Y-%m-%d %H:%M:%S"),
            "line_count": len(content.splitlines())
        }

    except UnicodeDecodeError:
        return {
            "success": False,
            "error": "文件不是UTF-8编码的文本文件，无法读取"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"读取文件失败: {str(e)}"
        }


# 工具调用处理函数
def handle_tool_call(tool_call):
    """
    处理工具调用

    Args:
        tool_call: 工具调用信息

    Returns:
        dict: 工具调用结果
    """
    function_name = tool_call.get("function", {}).get("name", "")
    arguments = tool_call.get("function", {}).get("arguments", "{}")

    try:
        args = json.loads(arguments)
    except json.JSONDecodeError:
        return {
            "error": f"参数解析失败: {arguments}",
            "tool_call_id": tool_call.get("id", "")
        }

    result = None

    # 根据函数名调用对应的工具
    if function_name == "list_directory_contents":
        dir_path = args.get("dir_path", "")
        if not dir_path:
            # 如果没有提供路径，使用当前目录
            dir_path = os.getcwd()
        result = list_directory_contents(dir_path)

    elif function_name == "rename_file":
        file_path = args.get("file_path", "")
        new_name = args.get("new_name", "")
        if not file_path or not new_name:
            return {
                "error": "需要 file_path 和 new_name 参数",
                "tool_call_id": tool_call.get("id", "")
            }
        result = rename_file(file_path, new_name)

    elif function_name == "delete_file":
        file_path = args.get("file_path", "")
        if not file_path:
            return {
                "error": "需要 file_path 参数",
                "tool_call_id": tool_call.get("id", "")
            }
        result = delete_file(file_path)

    elif function_name == "create_file":
        file_path = args.get("file_path", "")
        content = args.get("content", "")
        if not file_path:
            return {
                "error": "需要 file_path 参数",
                "tool_call_id": tool_call.get("id", "")
            }
        result = create_file(file_path, content)

    elif function_name == "read_file":
        file_path = args.get("file_path", "")
        if not file_path:
            return {
                "error": "需要 file_path 参数",
                "tool_call_id": tool_call.get("id", "")
            }
        result = read_file(file_path)

    else:
        result = {
            "error": f"未知的工具函数: {function_name}",
            "tool_call_id": tool_call.get("id", "")
        }

    # 添加工具调用ID
    if result and "tool_call_id" not in result:
        result["tool_call_id"] = tool_call.get("id", "")

    return result


# 流式调用LLM
def call_llm_stream(messages, env_vars, tools=None):
    """
    调用LLM（支持流式输出和工具调用）

    Args:
        messages: 消息列表
        env_vars: 环境变量
        tools: 工具定义列表

    Returns:
        tuple: (响应内容, 统计信息, 工具调用列表)
    """
    base_url = env_vars.get('BASE_URL', 'http://127.0.0.1:1234/v1')
    model = env_vars.get('MODEL', 'qwen3.5-9b')
    token = env_vars.get('TOKEN', 'lm-studio')
    timeout = 60

    parsed_url = urlparse(base_url)
    host = parsed_url.netloc
    path = parsed_url.path or '/'

    data = {
        "model": model,
        "messages": messages,
        "stream": True,
        "max_tokens": 4096,
        "temperature": 0.7
    }

    # 如果有工具定义，添加到请求中
    if tools:
        data["tools"] = tools

    start_time = time.time()
    full_resp = ""
    tool_calls = []

    try:
        conn = http.client.HTTPConnection(host, timeout=timeout)
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }

        conn.request(
            "POST",
            f"{path}/chat/completions",
            json.dumps(data),
            headers
        )

        response = conn.getresponse()
        if response.status != 200:
            print(f"Error: HTTP {response.status}")
            conn.close()
            return "", {}, []

        print("\n助手: ", end="", flush=True)

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
                    choice = data_json.get("choices", [{}])[0]
                    delta = choice.get("delta", {})

                    # 检查是否有工具调用
                    if "tool_calls" in delta:
                        for tool_call in delta["tool_calls"]:
                            if "function" in tool_call and \
                               "name" in tool_call["function"]:
                                tool_name = tool_call["function"]["name"]
                                print(
                                    f"\n[调用工具: {tool_name}]",
                                    end=" ",
                                    flush=True
                                )

                    # 收集工具调用
                    if "tool_calls" in delta:
                        tool_calls = delta["tool_calls"]

                    # 输出内容
                    if "content" in delta:
                        txt = delta["content"]
                        print(txt, end="", flush=True)
                        full_resp += txt

                except json.JSONDecodeError:
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

        print("\n")
        return full_resp, stats, tool_calls

    except Exception as e:
        print(f"Error: {e}")
        return "", {}, []


# 工具定义
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_directory_contents",
            "description": "列出指定目录下的所有文件和子目录，"
                           "包括文件大小、修改时间等信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "dir_path": {
                        "type": "string",
                        "description": "要列出内容的目录路径。"
                                       "如果不提供，则使用当前目录。"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "rename_file",
            "description": "重命名文件",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "要重命名的文件完整路径"
                    },
                    "new_name": {
                        "type": "string",
                        "description": "新的文件名（不包括路径）"
                    }
                },
                "required": ["file_path", "new_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_file",
            "description": "删除指定的文件（注意：删除操作不可逆！）",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "要删除的文件完整路径"
                    }
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_file",
            "description": "创建新文件并写入内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "要创建的文件完整路径"
                    },
                    "content": {
                        "type": "string",
                        "description": "要写入文件的内容，可以是空字符串"
                    }
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "读取文件内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "要读取的文件完整路径"
                    }
                },
                "required": ["file_path"]
            }
        }
    }
]

# 系统提示词
SYSTEM_PROMPT = """你是一个文件管理助手，可以帮助用户进行文件和目录操作。

你可以使用的工具：
1. list_directory_contents - 列出目录内容
2. rename_file - 重命名文件
3. delete_file - 删除文件
4. create_file - 创建文件
5. read_file - 读取文件

使用指南：
1. 当用户询问目录内容时，使用list_directory_contents
2. 当用户想要重命名文件时，使用rename_file
3. 当用户想要删除文件时，使用delete_file（注意确认）
4. 当用户想要创建文件时，使用create_file
5. 当用户想要读取文件内容时，使用read_file

注意事项：
- 在删除文件前，请确认用户意图
- 对于不存在的路径，给出友好提示
- 操作完成后，向用户报告结果
- 如果用户没有指定完整路径，可以询问或使用合理默认值

当前工作目录：{current_dir}
请根据用户请求，使用合适的工具进行操作。"""


# 主函数
def main():
    """主程序"""
    env_vars = load_env()

    if not env_vars:
        print("无法加载配置，程序退出。")
        return

    # 获取当前工作目录
    current_dir = os.getcwd()

    # 初始化消息列表
    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT.format(current_dir=current_dir)
        }
    ]

    print("=" * 60)
    print("文件管理助手（支持工具调用）")
    print("=" * 60)
    print(f"当前工作目录: {current_dir}")
    print("\n可用命令示例：")
    print("  • 查看当前目录内容: 列出文件")
    print("  • 查看其他目录: 查看 /path/to/directory 的内容")
    print("  • 创建文件: 创建 test.txt 文件，内容为 'Hello World'")
    print("  • 读取文件: 读取 test.txt 的内容")
    print("  • 重命名文件: 把 test.txt 改名为 new.txt")
    print("  • 删除文件: 删除 new.txt")
    print("\n输入 'exit' 或 '退出' 结束对话")
    print("按 Ctrl+C 强制退出")
    print("-" * 60)

    try:
        while True:
            user_input = input("\n你: ").strip()

            if user_input.lower() in ['exit', '退出', 'quit']:
                print("对话结束，再见！")
                break
            if not user_input:
                continue

            # 添加用户消息
            messages.append({"role": "user", "content": user_input})

            # 调用LLM
            assistant_response, stats, tool_calls = call_llm_stream(
                messages, env_vars, TOOLS
            )

            # 处理工具调用
            if tool_calls:
                print("\n[处理工具调用...]")

                # 保存工具调用的消息
                tool_message = {
                    "role": "assistant",
                    "content": assistant_response,
                    "tool_calls": tool_calls
                }
                messages.append(tool_message)

                # 处理每个工具调用
                for tool_call in tool_calls:
                    result = handle_tool_call(tool_call)

                    # 将工具结果添加到消息
                    messages.append({
                        "role": "tool",
                        "content": json.dumps(result, ensure_ascii=False),
                        "tool_call_id": result.get("tool_call_id", "")
                    })

                    # 输出工具调用结果
                    if result.get("success"):
                        tool_name = tool_call.get(
                            'function', {}
                        ).get('name', 'unknown')
                        print(f"[工具 {tool_name} 执行成功]")
                        if "message" in result:
                            print(f"结果: {result['message']}")
                    else:
                        tool_name = tool_call.get(
                            'function', {}
                        ).get('name', 'unknown')
                        print(f"[工具 {tool_name} 执行失败]")
                        print(f"错误: {result.get('error', '未知错误')}")

                # 如果有工具调用，需要再次调用LLM来获取最终响应
                print("\n[继续对话...]")
                assistant_response, stats, _ = call_llm_stream(
                    messages, env_vars, TOOLS
                )

            # 添加助手响应到消息历史
            if assistant_response:
                messages.append({
                    "role": "assistant",
                    "content": assistant_response
                })

                # 输出统计信息
                if stats:
                    print("\n" + "-" * 40)
                    print("本次统计信息:")
                    print(f"• 耗时: {stats['total_time']} 秒")
                    print(f"• 提示token: {stats['prompt_tokens']}")
                    print(f"• 回复token: {stats['completion_tokens']}")
                    print(f"• 总token: {stats['total_tokens']}")
                    print(f"• 速度: {stats['tokens_per_second']} tokens/s")
                    print("-" * 40)
            else:
                print("获取回复失败！")
                if messages and messages[-1]["role"] == "user":
                    messages.pop()  # 移除失败的用户消息

    except KeyboardInterrupt:
        print("\n\n检测到 Ctrl+C，对话结束！")
        print("感谢使用，再见！")
    except Exception as e:
        print(f"\n发生错误: {e}")
        print("程序异常退出")


if __name__ == "__main__":
    main()

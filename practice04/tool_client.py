import os
import json
import http.client
import time
import sys

from urllib.parse import urlparse


# 读取.env文件
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


# 工具函数1：列出目录下的文件及其属性
def list_files(directory):
    """
    列出某个目录下有哪些文件（包括文件的基本属性、大小等信息）
    参数:
        directory: 目录路径
    返回:
        文件信息列表
    """
    try:
        files_info = []
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            if os.path.isfile(item_path):
                stat_info = os.stat(item_path)
                files_info.append({
                    "name": item,
                    "type": "file",
                    "size": stat_info.st_size,  # 字节
                    "mtime": time.strftime(
                        '%Y-%m-%d %H:%M:%S',
                        time.localtime(stat_info.st_mtime)
                    ),
                    "path": item_path
                })
            elif os.path.isdir(item_path):
                files_info.append({
                    "name": item,
                    "type": "directory",
                    "path": item_path
                })
        return json.dumps(
            {"status": "success", "data": files_info},
            ensure_ascii=False,
            indent=2
        )
    except Exception as e:
        return json.dumps(
            {"status": "error", "message": str(e)},
            ensure_ascii=False
        )


# 工具函数2：修改文件名称
def rename_file(directory, old_name, new_name):
    """
    修改某个目录下某个文件的名字
    参数:
        directory: 目录路径
        old_name: 旧文件名
        new_name: 新文件名
    返回:
        操作结果
    """
    try:
        old_path = os.path.join(directory, old_name)
        new_path = os.path.join(directory, new_name)
        os.rename(old_path, new_path)
        return json.dumps(
            {"status": "success", "message": f"文件已重命名为: {new_name}"},
            ensure_ascii=False
        )
    except Exception as e:
        return json.dumps(
            {"status": "error", "message": str(e)},
            ensure_ascii=False
        )


# 工具函数3：删除文件
def delete_file(directory, file_name):
    """
    删除某个目录下的某个文件
    参数:
        directory: 目录路径
        file_name: 文件名
    返回:
        操作结果
    """
    try:
        file_path = os.path.join(directory, file_name)
        os.remove(file_path)
        return json.dumps(
            {"status": "success", "message": f"文件已删除: {file_name}"},
            ensure_ascii=False
        )
    except Exception as e:
        return json.dumps(
            {"status": "error", "message": str(e)},
            ensure_ascii=False
        )


# 工具函数4：创建文件并写入内容
def create_file(directory, file_name, content):
    """
    在某个目录下新建1个文件，并且写入内容
    参数:
        directory: 目录路径
        file_name: 文件名
        content: 文件内容
    返回:
        操作结果
    """
    try:
        file_path = os.path.join(directory, file_name)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return json.dumps(
            {"status": "success", "message": f"文件已创建: {file_name}"},
            ensure_ascii=False
        )
    except Exception as e:
        return json.dumps(
            {"status": "error", "message": str(e)},
            ensure_ascii=False
        )


# 工具函数5：读取文件内容
def read_file(directory, file_name):
    """
    读取某个目录下的某个文件的内容
    参数:
        directory: 目录路径
        file_name: 文件名
    返回:
        文件内容
    """
    try:
        file_path = os.path.join(directory, file_name)
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return json.dumps(
            {"status": "success", "data": content},
            ensure_ascii=False
        )
    except Exception as e:
        return json.dumps(
            {"status": "error", "message": str(e)},
            ensure_ascii=False
        )


# 工具函数6：curl网络访问
def curl(url):
    """
    通过curl访问网页并返回网页内容
    参数:
        url: 网页URL
    返回:
        网页内容
    """
    try:
        import urllib.request
        import urllib.error
        
        with urllib.request.urlopen(url) as response:
            # 尝试使用utf-8编码，失败则使用latin-1
            try:
                content = response.read().decode('utf-8')
            except UnicodeDecodeError:
                content = response.read().decode('latin-1')
        # 限制返回内容长度，避免输出过多
        if len(content) > 1000:
            content = content[:1000] + "... (内容过长，已截断)"
        return json.dumps(
            {"status": "success", "data": content},
            ensure_ascii=False
        )
    except urllib.error.URLError as e:
        return json.dumps(
            {"status": "error", "message": f"URL错误: {str(e)}"},
            ensure_ascii=False
        )
    except Exception as e:
        return json.dumps(
            {"status": "error", "message": str(e)},
            ensure_ascii=False
        )


# 流式输出 + 统计耗时、token、速度
def call_llm_stream(messages, env_vars):
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

    start_time = time.time()

    try:
        conn = http.client.HTTPSConnection(host, timeout=timeout)
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
            print(f"Error: {response.status}")
            conn.close()
            return "", {}

        print("\n助手: ")
        full_resp = ""
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
                    if "content" in delta:
                        txt = delta["content"]
                        print(txt, end="", flush=True)
                        full_resp += txt
                except Exception:
                    continue

        conn.close()

        # 统计
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
        return full_resp, stats

    except Exception as e:
        print(f"Error: {e}")
        return "", {}


# 解析工具调用请求
def parse_tool_call(response):
    """
    解析LLM返回的工具调用请求
    返回:
        (tool_name, tool_args) 或 (None, None)
    """
    try:
        # 查找工具调用的JSON部分，处理Markdown代码块
        if "tool_call" in response:
            # 移除Markdown代码块标记
            response = response.replace('```json', '')
            response = response.replace('```', '').strip()

            # 尝试直接解析整个响应
            # 查找JSON对象的开始
            start = response.find('{')
            if start != -1:
                # 找到匹配的大括号
                count = 0
                end = start
                for i in range(start, len(response)):
                    if response[i] == '{':
                        count += 1
                    elif response[i] == '}':
                        count -= 1
                        if count == 0:
                            end = i + 1
                            break

                if end > start:
                    tool_call_json = response[start:end]
                    tool_call = json.loads(tool_call_json)
                    return (
                        tool_call["tool_call"]["name"],
                        tool_call["tool_call"]["args"]
                    )
        return None, None
    except Exception as e:
        print(f"解析工具调用失败: {e}")
        # 尝试直接提取工具调用信息
        try:
            if "tool_call" in response:
                import re
                # 移除Markdown代码块标记
                response = response.replace('```json', '')
                response = response.replace('```', '').strip()
                # 提取工具名称
                name_match = re.search(r'"name":\s*"([^"]+)"', response)
                # 提取参数
                args_match = re.search(r'"args":\s*\{([^}]+)\}', response)
                if name_match and args_match:
                    tool_name = name_match.group(1)
                    args_str = args_match.group(1)
                    # 解析参数
                    args = {}
                    for arg in args_str.split(','):
                        arg = arg.strip()
                        if arg:
                            key_match = re.search(
                                r'"([^"]+)":\s*"([^"]+)"',
                                arg
                            )
                            if key_match:
                                key = key_match.group(1)
                                value = key_match.group(2)
                                args[key] = value
                    return tool_name, args
        except Exception as e2:
            print(f"备用解析也失败: {e2}")
        return None, None


# 工具函数7：读取聊天历史日志
def read_chat_log():
    """
    读取聊天历史日志文件
    返回: 日志内容
    """
    log_dir = "D:\\chat-log"
    log_file = os.path.join(log_dir, "log.txt")
    
    try:
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
            return json.dumps(
                {"status": "success", "data": content},
                ensure_ascii=False
            )
        else:
            return json.dumps(
                {"status": "error", "message": "聊天历史日志文件不存在"},
                ensure_ascii=False
            )
    except Exception as e:
        return json.dumps(
            {"status": "error", "message": str(e)},
            ensure_ascii=False
        )


# 工具函数8：调用AnythingLLM API
def anythingllm_query(message):
    """
    调用AnythingLLM的聊天API接口
    参数:
        message: 查询消息
    返回:
        API响应结果
    """
    import subprocess
    
    try:
        # 加载环境变量
        env_vars = load_env()
        api_key = env_vars.get('ANYTHING_API_KEY')
        workspace_slug = env_vars.get('ANYTHING_WORKSPACE_SLUG')
        
        if not api_key or not workspace_slug:
            return json.dumps(
                {
                    "status": "error", 
                    "message": "缺少ANYTHING_API_KEY或ANYTHING_WORKSPACE_SLUG环境变量"
                },
                ensure_ascii=False
            )
        
        # 构建API URL
        url = f"http://localhost:3001/api/v1/workspace/{workspace_slug}/chat"
        
        # 构建请求数据
        data = {
            "message": message,
            "stream": False
        }
        
        # 构建curl命令
        curl_cmd = [
            "curl",
            "-X", "POST",
            "-H", f"Authorization: Bearer {api_key}",
            "-H", "Content-Type: application/json",
            "-d", json.dumps(data, ensure_ascii=False),
            url
        ]
        
        # 执行curl命令
        result = subprocess.run(
            curl_cmd,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        
        # 检查执行结果
        if result.returncode != 0:
            return json.dumps(
                {"status": "error", "message": f"curl执行失败: {result.stderr}"},
                ensure_ascii=False
            )
        
        # 解析响应
        try:
            response_data = json.loads(result.stdout)
            return json.dumps(
                {"status": "success", "data": response_data},
                ensure_ascii=False
            )
        except json.JSONDecodeError:
            return json.dumps(
                {"status": "error", "message": f"响应解析失败: {result.stdout}"},
                ensure_ascii=False
            )
    except Exception as e:
        return json.dumps(
            {"status": "error", "message": str(e)},
            ensure_ascii=False
        )


# 执行工具调用
def execute_tool_call(tool_name, tool_args):
    """
    执行工具调用
    """
    if tool_name == "list_files":
        return list_files(tool_args["directory"])
    elif tool_name == "rename_file":
        return rename_file(
            tool_args["directory"],
            tool_args["old_name"],
            tool_args["new_name"]
        )
    elif tool_name == "delete_file":
        return delete_file(tool_args["directory"], tool_args["file_name"])
    elif tool_name == "create_file":
        return create_file(
            tool_args["directory"],
            tool_args["file_name"],
            tool_args["content"]
        )
    elif tool_name == "read_file":
        return read_file(tool_args["directory"], tool_args["file_name"])
    elif tool_name == "curl":
        return curl(tool_args["url"])
    elif tool_name == "read_chat_log":
        return read_chat_log()
    elif tool_name == "anythingllm_query":
        return anythingllm_query(tool_args["message"])
    else:
        return json.dumps(
            {"status": "error", "message": f"Unknown tool: {tool_name}"},
            ensure_ascii=False
        )


def extract_key_info(messages, env_vars):
    """
    提取聊天历史中的关键信息，按照5W规则
    """
    # 分离系统提示和对话内容
    conversation_messages = [
        msg for msg in messages if msg["role"] != "system"
    ]
    
    if len(conversation_messages) < 2:
        return
    
    # 构建提取提示词
    extract_prompt = f"""
    请从以下聊天记录中提取关键信息，按照5W规则（Who、What、When、Where、Why）进行提取。
    每条关键信息应该包含：
    - Who：谁
    - What：做了什么事
    - When：什么时候（可选）
    - Where：在何处（可选）
    - Why：为什么要做这个事（可选）
    
    聊天记录：
    {json.dumps(conversation_messages, ensure_ascii=False, indent=2)}
    
    请以JSON格式返回提取的关键信息，格式如下：
    {{"key_infos": [
        {{"Who": "", "What": "", "When": "", "Where": "", "Why": ""}}
    ]}}
    """
    
    # 调用LLM进行提取
    extract_messages = [
        {
            "role": "system", 
            "content": "你是一个专业的信息提取助手，擅长按照5W规则提取关键信息。"
        },
        {"role": "user", "content": extract_prompt}
    ]
    
    print("\n🔍 正在提取关键信息...")
    extract_response, _ = call_llm_stream(extract_messages, env_vars)
    
    try:
        # 尝试解析提取结果
        extract_data = json.loads(extract_response.strip())
        key_infos = extract_data.get("key_infos", [])
        
        if key_infos:
            # 写入日志文件
            log_dir = "D:\\chat-log"
            log_file = os.path.join(log_dir, "log.txt")
            
            # 确保目录存在
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            # 追加写入日志
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write("\n=== 关键信息提取 ===\n")
                f.write(f"提取时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                for i, info in enumerate(key_infos, 1):
                    f.write(f"\n{str(i)}. Who: {info.get('Who', '')}\n")
                    f.write(f"   What: {info.get('What', '')}\n")
                    if info.get('When'):
                        f.write(f"   When: {info.get('When')}\n")
                    if info.get('Where'):
                        f.write(f"   Where: {info.get('Where')}\n")
                    if info.get('Why'):
                        f.write(f"   Why: {info.get('Why')}\n")
                f.write("\n")
            
            print(f"✅ 关键信息提取完成：{len(key_infos)}条信息已记录")
        else:
            print("⚠️ 未提取到关键信息")
    except Exception as e:
        print(f"❌ 提取关键信息失败：{e}")


# ================== 新增：聊天历史压缩相关函数 ==================

def calculate_history_stats(messages):
    """
    计算聊天历史的统计信息
    返回: (轮数, 总字符长度)
    """
    # 计算轮数（排除系统提示，每轮包含user和assistant）
    conversation_messages = [
        msg for msg in messages if msg["role"] != "system"
    ]
    rounds = len(conversation_messages) // 2

    # 计算总长度
    total_length = sum(len(msg.get("content", "")) for msg in messages)

    return rounds, total_length


def print_separator(char="━", length=50):
    """
    打印分隔线
    """
    print(char * length)


def print_stats(stats, messages):
    """
    美化统计信息显示
    """
    print_separator()
    print("[统计信息] 本次统计")
    print_separator()
    print(f"[时间] 耗时: {stats['total_time']} 秒")
    print(f"[输入] 提示token: {stats['prompt_tokens']}")
    print(f"[输出] 回复token: {stats['completion_tokens']}")
    print(f"[总计] 总token: {stats['total_tokens']}")
    print(f"[速度] 速度: {stats['tokens_per_second']} tokens/s")

    # 显示当前历史状态
    rounds, length = calculate_history_stats(messages)
    print(f"[状态] 当前对话：{rounds}轮，{length}字符")
    print_separator()


def format_tool_call(tool_name, tool_args):
    """
    格式化工具调用显示
    """
    print(f"\n[工具] 调用: {tool_name}")
    if tool_name == "anythingllm_query":
        print(f"[查询] 内容: {tool_args.get('message', '')}")
    elif tool_name == "list_files":
        print(f"[目录] 路径: {tool_args.get('directory', '')}")
    elif tool_name == "curl":
        print(f"[网络] URL: {tool_args.get('url', '')}")
    elif tool_name == "create_file":
        print(f"[文件] 名称: {tool_args.get('file_name', '')}")
    elif tool_name == "read_file":
        print(f"[文件] 名称: {tool_args.get('file_name', '')}")


def format_tool_result(tool_name, tool_result):
    """
    格式化工具执行结果显示
    """
    try:
        result_data = json.loads(tool_result)
        if result_data.get("status") == "success":
            if tool_name == "anythingllm_query":
                # 提取 AnythingLLM 的 textResponse
                data = result_data.get("data", {})
                text_response = data.get("textResponse", "")
                if text_response:
                    print("\n[结果] 文档仓库查询结果：")
                    print_separator()
                    print(text_response)
                    print_separator()
                else:
                    print("\n[警告] 文档仓库返回空结果")
            else:
                print("\n[成功] 工具执行成功")
        else:
            print(f"\n[错误] 工具执行失败: {result_data.get('message', '未知错误')}")
    except json.JSONDecodeError:
        print(f"\n[结果] 工具执行结果: {tool_result}")


def compress_history(messages, env_vars):
    """
    压缩聊天历史
    策略：保留最近30%的对话原文，压缩前70%
    """
    # 分离系统提示和对话内容
    system_messages = [
        msg for msg in messages if msg["role"] == "system"
    ]
    conversation_messages = [
        msg for msg in messages if msg["role"] != "system"
    ]
    
    if len(conversation_messages) < 4:  # 至少要有2轮对话才需要压缩
        return messages
    
    # 计算分割点：保留最后30%
    total_msgs = len(conversation_messages)
    keep_count = max(2, int(total_msgs * 0.3))  # 至少保留2条消息
    compress_count = total_msgs - keep_count
    
    # 要压缩的消息和要保留的消息
    to_compress = conversation_messages[:compress_count]
    to_keep = conversation_messages[compress_count:]
    
    # 构建压缩提示词
    compress_prompt = f"""
    请将以下聊天记录进行简洁的总结，保留关键信息、重要决策和用户偏好。
    总结应简明扼要，便于后续对话参考。
    
    聊天记录：
    {json.dumps(to_compress, ensure_ascii=False, indent=2)}
    
    请以JSON格式返回总结，格式如下：
    {{"summary": "总结内容"}}
    """
    
    # 调用LLM进行压缩
    compress_messages = [
        {
            "role": "system", 
            "content": "你是一个专业的对话总结助手，擅长提取关键信息。"
        },
        {"role": "user", "content": compress_prompt}
    ]
    
    print("\n[压缩] 上下文过长，正在智能压缩...")
    summary_response, _ = call_llm_stream(compress_messages, env_vars)
    
    try:
        # 尝试解析总结
        summary_data = json.loads(summary_response.strip())
        summary = summary_data.get("summary", "无法生成总结")
    except Exception:
        # 如果解析失败，直接使用原始响应
        summary = summary_response.strip()
    
    # 构建新的消息列表
    new_messages = system_messages.copy()
    
    # 添加压缩后的历史摘要
    new_messages.append({
        "role": "system",
        "content": f"以下是之前的对话摘要（已压缩）：\n{summary}"
    })
    
    # 添加保留的原始对话
    new_messages.extend(to_keep)

    print(f"[完成] 压缩完成：{len(to_compress)}条消息已合并")
    return new_messages


def should_compress_history(messages, max_rounds=5, max_length=3000):
    """
    判断是否需要压缩历史
    """
    rounds, total_length = calculate_history_stats(messages)
    
    if rounds > max_rounds:
        print(f"\n[压缩] 对话轮数过多({rounds}轮)，正在智能压缩...")
        return True

    if total_length > max_length:
        print(f"\n[压缩] 上下文过长({total_length}字符)，正在智能压缩...")
        return True
    
    return False


# 主函数
def main():
    env_vars = load_env()

    if not env_vars:
        return

    # 系统提示词，包含工具调用能力
    system_prompt = """
    你是一个具有文件操作能力的助手，你可以使用以下工具：

    1. list_files：列出某个目录下有哪些文件（包括文件的基本属性、大小等信息）
       参数：
       - directory: 目录路径

    2. rename_file：修改某个目录下某个文件的名字
       参数：
       - directory: 目录路径
       - old_name: 旧文件名
       - new_name: 新文件名

    3. delete_file：删除某个目录下的某个文件
       参数：
       - directory: 目录路径
       - file_name: 文件名

    4. create_file：在某个目录下新建1个文件，并且写入内容
       参数：
       - directory: 目录路径
       - file_name: 文件名
       - content: 文件内容

    5. read_file：读取某个目录下的某个文件的内容
       参数：
       - directory: 目录路径
       - file_name: 文件名

    6. curl：通过curl访问网页并返回网页内容
       参数：
       - url: 网页URL

    7. read_chat_log：读取聊天历史日志文件
       参数：无

    8. anythingllm_query：调用AnythingLLM的聊天API接口查询文档仓库
       参数：
       - message: 查询消息

    当用户需要执行文件操作、网络访问或查询文档仓库时，你需要以JSON格式返回工具调用请求，格式如下：
    {"tool_call": {"name": "工具名称", "args": {"参数名": "参数值"}}}

    例如：
    当用户说"列出当前目录的文件"，你应该返回：
    {"tool_call": {"name": "list_files", "args": {"directory": "."}}}
    当用户说"访问百度"，你应该返回：
    {"tool_call": {"name": "curl", "args": {"url": "https://www.baidu.com"}}}
    当用户说"查找聊天历史"，你应该返回：
    {"tool_call": {"name": "read_chat_log", "args": {}}}
    当用户提到"文档仓库"、"文件仓库"、"仓库"或需要查询文档内容时，你应该返回：
    {
        "tool_call": {
            "name": "anythingllm_query", 
            "args": {"message": "用户的查询内容"}
        }
    }
    """

    # 对话轮数计数器
    conversation_rounds = 0

    messages = [{"role": "system", "content": system_prompt}]

    # 检查是否有命令行参数
    if len(sys.argv) > 1:
        # 从命令行参数获取用户输入
        user_input = ' '.join(sys.argv[1:])
        print(f"你: {user_input}")

        messages.append({"role": "user", "content": user_input})
        assistant_response, stats = call_llm_stream(messages, env_vars)

        if assistant_response:
            # 检查是否是工具调用
            tool_name, tool_args = parse_tool_call(assistant_response)
            if tool_name and tool_args:
                format_tool_call(tool_name, tool_args)
                tool_result = execute_tool_call(tool_name, tool_args)
                format_tool_result(tool_name, tool_result)
            else:
                print("助手没有调用工具")

            # 输出统计
            print_stats(stats, messages)
        else:
            print("获取回复失败！")
    else:
        # 交互式模式
        print("=== 工具调用模式（流式输出 + 历史压缩）===")
        print("输入 'exit' 或 '退出' 结束对话")
        print("按 Ctrl+C 强制退出")
        print("-" * 50)

        try:
            while True:
                user_input = input("\n你: ")

                if user_input.lower() in ['exit', '退出']:
                    print("对话结束，再见！")
                    break

                # 检查是否需要查找聊天历史
                search_chat_history = False
                if user_input.startswith("/search"):
                    search_chat_history = True
                elif any(
                    keyword in user_input.lower() 
                    for keyword in [
                        "查找聊天历史", "查看聊天记录", 
                        "聊天历史", "历史记录"
                    ]
                ):
                    search_chat_history = True

                # 如果需要查找聊天历史，读取log.txt文件
                if search_chat_history:
                    log_dir = "D:\\chat-log"
                    log_file = os.path.join(log_dir, "log.txt")
                    if os.path.exists(log_file):
                        try:
                            with open(log_file, 'r', encoding='utf-8') as f:
                                log_content = f.read()
                            # 将聊天历史添加到对话中
                            messages.append({
                                "role": "system",
                                "content": f"以下是聊天历史日志内容：\n{log_content}"
                            })
                            print("\n📖 已加载聊天历史日志")
                        except Exception as e:
                            print(f"❌ 读取聊天历史失败：{e}")
                    else:
                        print("⚠️ 聊天历史日志文件不存在")

                messages.append({"role": "user", "content": user_input})
                
                # 增加对话轮数计数
                conversation_rounds += 1
                
                # 🔥 新增：每5轮提取一次关键信息
                if conversation_rounds % 5 == 0:
                    extract_key_info(messages, env_vars)
                
                # 🔥 新增：检查是否需要压缩历史
                if should_compress_history(
                    messages, max_rounds=5, max_length=3000
                ):
                    messages = compress_history(messages, env_vars)
                
                assistant_response, stats = call_llm_stream(messages, env_vars)

                if assistant_response:
                    # 检查是否是工具调用
                    tool_name, tool_args = parse_tool_call(assistant_response)
                    if tool_name and tool_args:
                        format_tool_call(tool_name, tool_args)
                        tool_result = execute_tool_call(tool_name, tool_args)
                        format_tool_result(tool_name, tool_result)
                        # 将工具执行结果添加到对话历史
                        messages.append(
                            {
                                "role": "assistant",
                                "content": assistant_response
                            }
                        )
                        messages.append(
                            {
                                "role": "system",
                                "content": f"工具执行结果: {tool_result}"
                            }
                        )
                    else:
                        messages.append(
                            {
                                "role": "assistant",
                                "content": assistant_response
                            }
                        )

                    # 输出统计
                    print_stats(stats, messages)
                else:
                    print("获取回复失败！")
                    if messages:
                        messages.pop()
        except KeyboardInterrupt:
            print("\n\n检测到Ctrl+C，对话结束！")
            print("感谢使用，再见！")


if __name__ == "__main__":
    main()

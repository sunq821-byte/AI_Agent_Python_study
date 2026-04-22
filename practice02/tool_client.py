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
    else:
        return json.dumps(
            {"status": "error", "message": f"Unknown tool: {tool_name}"},
            ensure_ascii=False
        )


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

    当用户需要执行文件操作或网络访问时，你需要以JSON格式返回工具调用请求，格式如下：
    {"tool_call": {"name": "工具名称", "args": {"参数名": "参数值"}}}

    例如：
    当用户说"列出当前目录的文件"，你应该返回：
    {"tool_call": {"name": "list_files", "args": {"directory": "."}}}
    当用户说"访问百度"，你应该返回：
    {"tool_call": {"name": "curl", "args": {"url": "https://www.baidu.com"}}}
    """

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
                print(f"\n执行工具调用: {tool_name}")
                tool_result = execute_tool_call(tool_name, tool_args)
                print(f"工具执行结果: {tool_result}")
            else:
                print("助手没有调用工具")

            # 输出统计
            print("本次统计信息")
            print(f"耗时: {stats['total_time']} 秒")
            print(f"提示token: {stats['prompt_tokens']}")
            print(f"回复token: {stats['completion_tokens']}")
            print(f"总token: {stats['total_tokens']}")
            print(f"速度: {stats['tokens_per_second']} tokens/s")
        else:
            print("获取回复失败！")
    else:
        # 交互式模式
        print("=== 工具调用模式（流式输出）===")
        print("输入 'exit' 或 '退出' 结束对话")
        print("按 Ctrl+C 强制退出")
        print("-" * 50)

        try:
            while True:
                user_input = input("\n你: ")

                if user_input.lower() in ['exit', '退出']:
                    print("对话结束，再见！")
                    break

                messages.append({"role": "user", "content": user_input})
                assistant_response, stats = call_llm_stream(messages, env_vars)

                if assistant_response:
                    # 检查是否是工具调用
                    tool_name, tool_args = parse_tool_call(assistant_response)
                    if tool_name and tool_args:
                        print(f"\n执行工具调用: {tool_name}")
                        tool_result = execute_tool_call(tool_name, tool_args)
                        print(f"工具执行结果: {tool_result}")
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
                    print("本次统计信息")
                    print(f"耗时: {stats['total_time']} 秒")
                    print(f"提示token: {stats['prompt_tokens']}")
                    print(f"回复token: {stats['completion_tokens']}")
                    print(f"总token: {stats['total_tokens']}")
                    print(f"速度: {stats['tokens_per_second']} tokens/s")
                else:
                    print("获取回复失败！")
                    if messages:
                        messages.pop()
        except KeyboardInterrupt:
            print("\n\n检测到Ctrl+C，对话结束！")
            print("感谢使用，再见！")


if __name__ == "__main__":
    main()

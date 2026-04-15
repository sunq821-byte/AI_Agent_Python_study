import os
import json
import http.client
import time
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


# 工具函数1：列出目录文件及属性
def list_files(directory):
    """列出某个目录下有哪些文件（包括文件的基本属性，大小等信息）"""
    try:
        files = []
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            stat = os.stat(item_path)
            file_info = {
                "name": item,
                "path": item_path,
                "size": stat.st_size,
                "is_directory": os.path.isdir(item_path),
                "mode": stat.st_mode,
                "mtime": stat.st_mtime
            }
            files.append(file_info)
        return {
            "success": True,
            "data": files,
            "message": f"成功列出目录 {directory} 中的 {len(files)} 个文件"
        }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "message": f"错误：{str(e)}"
        }


# 工具函数2：修改文件名
def rename_file(old_path, new_name):
    """修改某个目录下某个文件的名字"""
    try:
        directory = os.path.dirname(old_path)
        new_path = os.path.join(directory, new_name)
        os.rename(old_path, new_path)
        return {
            "success": True,
            "data": {
                "old_path": old_path,
                "new_path": new_path
            },
            "message": f"成功将文件 {old_path} 重命名为 {new_name}"
        }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "message": f"错误：{str(e)}"
        }


# 工具函数3：删除文件
def delete_file(file_path):
    """删除某个目录下的某个文件"""
    try:
        os.remove(file_path)
        return {
            "success": True,
            "data": {"file_path": file_path},
            "message": f"成功删除文件 {file_path}"
        }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "message": f"错误：{str(e)}"
        }


# 工具函数4：新建文件并写入内容
def create_file(file_path, content):
    """在某个目录下新建1个文件，并且写入内容"""
    try:
        directory = os.path.dirname(file_path)
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return {
            "success": True,
            "data": {
                "file_path": file_path,
                "content_length": len(content)
            },
            "message": f"成功创建文件 {file_path} 并写入内容"
        }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "message": f"错误：{str(e)}"
        }


# 工具函数5：读取文件内容
def read_file(file_path):
    """读取某个目录下的某个文件的内容"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return {
            "success": True,
            "data": {
                "file_path": file_path,
                "content": content,
                "content_length": len(content)
            },
            "message": f"成功读取文件 {file_path} 的内容"
        }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "message": f"错误：{str(e)}"
        }


# 工具映射
tools = {
    "list_files": list_files,
    "rename_file": rename_file,
    "delete_file": delete_file,
    "create_file": create_file,
    "read_file": read_file
}


# 工具描述（系统提示词的一部分）
tool_descriptions = [
    {
        "name": "list_files",
        "description": "列出某个目录下有哪些文件（包括文件的基本属性，大小等信息）",
        "parameters": {
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "description": "要列出文件的目录路径"
                }
            },
            "required": ["directory"]
        }
    },
    {
        "name": "rename_file",
        "description": "修改某个目录下某个文件的名字",
        "parameters": {
            "type": "object",
            "properties": {
                "old_path": {
                    "type": "string",
                    "description": "原文件路径"
                },
                "new_name": {
                    "type": "string",
                    "description": "新文件名"
                }
            },
            "required": ["old_path", "new_name"]
        }
    },
    {
        "name": "delete_file",
        "description": "删除某个目录下的某个文件",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "要删除的文件路径"
                }
            },
            "required": ["file_path"]
        }
    },
    {
        "name": "create_file",
        "description": "在某个目录下新建1个文件，并且写入内容",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "要创建的文件路径"
                },
                "content": {
                    "type": "string",
                    "description": "要写入文件的内容"
                }
            },
            "required": ["file_path", "content"]
        }
    },
    {
        "name": "read_file",
        "description": "读取某个目录下的某个文件的内容",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "要读取的文件路径"
                }
            },
            "required": ["file_path"]
        }
    }
]


# 调用LLM API（支持工具调用）
def call_llm_with_tools(messages, env_vars):
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
        "tools": tool_descriptions,
        "tool_choice": "auto",
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
            return None, {}

        response_data = json.loads(response.read().decode('utf-8'))
        conn.close()

        end_time = time.time()
        total_time = end_time - start_time

        # 检查是否需要工具调用
        choices = response_data.get('choices')
        if choices and choices[0].get('message'):
            message = choices[0]['message']
            if message.get('tool_calls'):
                # 处理工具调用
                for tool_call in message['tool_calls']:
                    tool_name = tool_call['function']['name']
                    tool_args = json.loads(tool_call['function']['arguments'])

                    print(f"\n工具调用: {tool_name}")
                    print(f"参数: {tool_args}")

                    # 执行工具函数
                    if tool_name in tools:
                        result = tools[tool_name](**tool_args)
                        print(f"执行结果: {result['message']}")

                        # 将工具执行结果添加到对话历史
                        tool_message = {
                            "role": "tool",
                            "tool_call_id": tool_call['id'],
                            "name": tool_name,
                            "content": json.dumps(result)
                        }
                        messages.append(tool_message)

                        # 再次调用LLM获取最终响应
                        return call_llm_with_tools(messages, env_vars)
                    else:
                        print(f"未知工具: {tool_name}")
                        return None, {}
            else:
                # 直接返回LLM的响应
                assistant_response = message.get('content', '')
                usage = response_data.get('usage', {})
                stats = {
                    "total_time": round(total_time, 2),
                    "prompt_tokens": usage.get('prompt_tokens', 0),
                    "completion_tokens": usage.get('completion_tokens', 0),
                    "total_tokens": usage.get('total_tokens', 0),
                    "tokens_per_second": (
                        round(usage.get('total_tokens', 0) / total_time, 2)
                        if total_time > 0 else 0
                    )
                }
                return assistant_response, stats

        return None, {}

    except Exception as e:
        print(f"Error: {e}")
        return None, {}


# 主函数
def main():
    env_vars = load_env()

    if not env_vars:
        return

    # 系统提示词
    system_prompt = (
        "你是一个智能助手，能够使用工具来执行文件操作。以下是你可以使用的工具：\n\n"
        "1. list_files: 列出某个目录下有哪些文件（包括文件的基本属性，大小等信息）\n"
        "2. rename_file: 修改某个目录下某个文件的名字\n"
        "3. delete_file: 删除某个目录下的某个文件\n"
        "4. create_file: 在某个目录下新建1个文件，并且写入内容\n"
        "5. read_file: 读取某个目录下的某个文件的内容\n\n"
        "当用户的请求需要执行文件操作时，请使用相应的工具。工具执行完成后，"
        "你需要根据执行结果给用户一个清晰的回复。\n\n"
        "请使用中文回复用户。"
    )

    messages = [
        {"role": "system", "content": system_prompt}
    ]

    print("=== 工具调用模式 ===")
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
            assistant_response, stats = call_llm_with_tools(messages, env_vars)

            if assistant_response:
                messages.append(
                    {"role": "assistant", "content": assistant_response}
                )
                print("\n助手: ")
                print(assistant_response)

                if stats:
                    print("\n本次统计信息")
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

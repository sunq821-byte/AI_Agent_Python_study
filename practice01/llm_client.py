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


# 主函数
def main():
    env_vars = load_env()

    if not env_vars:
        return

    messages = []
    print("=== 多轮对话模式（流式输出）===")
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
                messages.append({
                    "role": "assistant",
                    "content": assistant_response
                })

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

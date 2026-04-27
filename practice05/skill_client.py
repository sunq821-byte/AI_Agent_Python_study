import os
import json
import http.client
import time
import sys
import re

from urllib.parse import urlparse


# ── 环境变量 ──────────────────────────────────────────────
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
        print("Error: .env file not found.")
    return env_vars


# ── Skills 目录 ───────────────────────────────────────────
def _skills_dir():
    """返回 .agents/skills 目录的绝对路径"""
    project_root = os.path.dirname(os.path.dirname(__file__))
    return os.path.join(project_root, '.agents', 'skills')


def _parse_frontmatter(text):
    """
    解析 YAML front matter（--- 之间的内容）。
    返回 (meta_dict, body_text)。
    """
    pattern = re.compile(r'^---\s*\n(.*?)\n---\s*\n', re.DOTALL)
    match = pattern.match(text)
    if not match:
        return {}, text

    meta = {}
    for line in match.group(1).splitlines():
        if ':' in line:
            k, _, v = line.partition(':')
            meta[k.strip()] = v.strip()

    body = text[match.end():]
    return meta, body


# ── 技能工具函数 1：读取可用技能列表 ─────────────────────
def list_available_skills():
    """
    读取 .agents/skills 目录下所有一级子目录中的 SKILL.md，
    提取 name 和 description 字段，以 JSON 格式返回技能列表。

    返回:
        {"skills": [{"name": "...", "description": "..."}]}
    """
    skills_root = _skills_dir()
    skills = []

    if not os.path.isdir(skills_root):
        return json.dumps({"skills": []}, ensure_ascii=False)

    for entry in sorted(os.listdir(skills_root)):
        skill_dir = os.path.join(skills_root, entry)
        if not os.path.isdir(skill_dir):
            continue
        skill_md = os.path.join(skill_dir, 'SKILL.md')
        if not os.path.isfile(skill_md):
            continue
        with open(skill_md, 'r', encoding='utf-8') as f:
            content = f.read()
        meta, _ = _parse_frontmatter(content)
        skills.append({
            "name": meta.get('name', entry),
            "description": meta.get('description', '')
        })

    return json.dumps({"skills": skills}, ensure_ascii=False, indent=2)


# ── 技能工具函数 2：读取技能正文内容 ─────────────────────
def load_skill_content(skill_name):
    """
    读取指定技能的 SKILL.md 正文内容（YAML front matter 之后的部分）。

    参数:
        skill_name: 技能名称（子目录名 或 SKILL.md 中的 name 字段）
    返回:
        技能正文文本（str），若找不到返回 None
    """
    skills_root = _skills_dir()
    if not os.path.isdir(skills_root):
        return None

    for entry in os.listdir(skills_root):
        skill_dir = os.path.join(skills_root, entry)
        if not os.path.isdir(skill_dir):
            continue
        skill_md = os.path.join(skill_dir, 'SKILL.md')
        if not os.path.isfile(skill_md):
            continue
        with open(skill_md, 'r', encoding='utf-8') as f:
            content = f.read()
        meta, body = _parse_frontmatter(content)
        # 匹配目录名 或 name 字段
        if entry == skill_name or meta.get('name') == skill_name:
            return body.strip()

    return None


# ── LLM 流式调用 ──────────────────────────────────────────
def call_llm_stream(messages, env_vars):
    base_url = env_vars.get('BASE_URL', 'http://127.0.0.1:1234/v1')
    model = env_vars.get('MODEL', 'qwen3-8b')
    token = env_vars.get('TOKEN', 'lm-studio')
    timeout = 120

    parsed_url = urlparse(base_url)
    host = parsed_url.netloc
    path = parsed_url.path.rstrip('/')

    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
        "max_tokens": 4096,
        "temperature": 0.7,
        "extra_body": {"enable_thinking": False}
    }

    start_time = time.time()

    try:
        if parsed_url.scheme == 'https':
            conn = http.client.HTTPSConnection(host, timeout=timeout)
        else:
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
            print(f"Error: HTTP {response.status}")
            conn.close()
            return "", {}

        print("\n助手: ", end="", flush=True)
        full_resp = ""
        in_think = False
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
                        # 跳过 <think>...</think> 内容
                        if "<think>" in txt:
                            in_think = True
                        if in_think:
                            if "</think>" in txt:
                                in_think = False
                            continue
                        print(txt, end="", flush=True)
                        full_resp += txt
                except Exception:
                    continue

        conn.close()

        elapsed = time.time() - start_time
        prompt_tokens = len(str(messages)) // 4
        completion_tokens = len(full_resp) // 4
        total_tokens = prompt_tokens + completion_tokens

        stats = {
            "total_time": round(elapsed, 2),
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "tokens_per_second": round(
                total_tokens / elapsed if elapsed > 0 else 0, 2
            )
        }
        print("\n")
        return full_resp, stats

    except Exception as e:
        print(f"\nError: {e}")
        return "", {}


# ── 工具调用解析 ──────────────────────────────────────────
def parse_tool_call(response):
    """解析 LLM 返回的 JSON tool_call 指令"""
    if "tool_call" not in response:
        return None, None
    try:
        clean = re.sub(r'```json|```', '', response).strip()
        start = clean.find('{')
        if start == -1:
            return None, None
        count = 0
        end = start
        for i in range(start, len(clean)):
            if clean[i] == '{':
                count += 1
            elif clean[i] == '}':
                count -= 1
                if count == 0:
                    end = i + 1
                    break
        obj = json.loads(clean[start:end])
        tc = obj.get("tool_call", {})
        return tc.get("name"), tc.get("args", {})
    except Exception:
        return None, None


# ── 主程序 ────────────────────────────────────────────────
def build_system_prompt(skills_json):
    """构建包含技能列表的系统提示词"""
    return f"""你是一个智能助手，能够识别用户意图并动态加载技能。

## 可用技能列表
以下是当前可用的技能，以 JSON 格式提供：

{skills_json}

## 技能调用规则

当用户的请求与某个技能的 description 相关时，你必须先调用
load_skill_content 加载该技能的详细说明，然后严格遵照技能说明
来完成用户的请求。

## 工具调用格式

当你需要调用工具时，只返回如下 JSON，不要有任何其他文字：
{{"tool_call": {{"name": "工具名称", "args": {{"参数名": "参数值"}}}}}}

## 可用工具

- load_skill_content：加载指定技能的详细说明
  参数：skill_name（技能名称，即 skills 列表中的 name 字段）

## 工作流程

1. 收到用户请求，检查是否与某个技能相关。
2. 若相关，先调用 load_skill_content 加载技能正文。
3. 加载完成后，严格按照技能说明执行任务，直接回复用户。
4. 若不相关，直接回复用户。
"""


def execute_tool(tool_name, tool_args):
    """执行工具调用"""
    if tool_name == "load_skill_content":
        skill_name = tool_args.get("skill_name", "")
        body = load_skill_content(skill_name)
        if body:
            return json.dumps(
                {
                    "status": "success",
                    "skill_name": skill_name,
                    "content": body
                },
                ensure_ascii=False
            )
        return json.dumps(
            {"status": "error", "message": f"技能 '{skill_name}' 不存在"},
            ensure_ascii=False
        )
    return json.dumps(
        {"status": "error", "message": f"未知工具: {tool_name}"},
        ensure_ascii=False
    )


def print_separator(char="━", length=50):
    print(char * length)


def print_stats(stats, messages):
    print_separator()
    print(f"[时间] {stats['total_time']}s  "
          f"[Token] {stats['total_tokens']}  "
          f"[速度] {stats['tokens_per_second']} t/s  "
          f"[消息数] {len(messages)}")
    print_separator()


def run_once(user_input, env_vars, verbose=True):
    """
    单次请求：读取技能列表 → 构建 system prompt → 对话循环（最多 5 轮）
    返回最终 LLM 回复文本。
    """
    # 每次请求都重新读取最新技能列表
    skills_json = list_available_skills()
    if verbose:
        skills_data = json.loads(skills_json)
        print(f"\n[Skills] 已加载 {len(skills_data['skills'])} 个技能: "
              f"{[s['name'] for s in skills_data['skills']]}")

    system_prompt = build_system_prompt(skills_json)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input}
    ]

    for turn in range(5):
        resp, stats = call_llm_stream(messages, env_vars)
        if not resp:
            print("获取回复失败！")
            return ""

        tool_name, tool_args = parse_tool_call(resp)

        if tool_name:
            print(f"[工具] 调用: {tool_name}  参数: {tool_args}")
            tool_result = execute_tool(tool_name, tool_args)
            result_data = json.loads(tool_result)

            messages.append({"role": "assistant", "content": resp})

            if tool_name == "load_skill_content" and \
                    result_data.get("status") == "success":
                skill_content = result_data["content"]
                print(f"[Skills] 已加载技能正文: {result_data['skill_name']}")
                # 将技能正文以 tool result 的形式注入（user角色，避免多system）
                messages.append({
                    "role": "user",
                    "content": (
                        f"[技能加载成功] 技能 [{result_data['skill_name']}] "
                        f"的详细规则如下，请严格遵照执行，然后完成我之前的请求：\n\n"
                        f"{skill_content}"
                    )
                })
            else:
                messages.append({
                    "role": "user",
                    "content": f"工具执行结果: {tool_result}"
                })
            # 继续下一轮，让 LLM 生成最终回复
            continue

        # 无工具调用 → 最终回复
        if verbose:
            print_stats(stats, messages)
        return resp

    print("[警告] 达到最大工具调用轮数限制")
    return ""


def main():
    env_vars = load_env()
    if not env_vars:
        return

    # ── 命令行单次模式 ──────────────────────────────────
    if len(sys.argv) > 1:
        user_input = ' '.join(sys.argv[1:])
        print(f"你: {user_input}")
        run_once(user_input, env_vars)
        return

    # ── 交互式模式 ──────────────────────────────────────
    print("=" * 50)
    print("=== Practice05: Skills 动态加载客户端 ===")
    print("输入 'exit' 或 '退出' 结束对话")
    print("=" * 50)

    try:
        while True:
            user_input = input("\n你: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ('exit', '退出'):
                print("再见！")
                break
            run_once(user_input, env_vars)
    except KeyboardInterrupt:
        print("\n\n已退出。")


if __name__ == "__main__":
    main()

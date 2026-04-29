"""
practice06 — 链式工具调用（Chained Tool Calls）
在 practice05 基础上实现：前一个工具的输出作为后一个工具的输入，
LLM 根据中间结果自主决定后续调用链。
"""
import os
import json
import http.client
import time
import sys
import re
from urllib.parse import urlparse


# ══════════════════════════════════════════════════════════
#  环境变量
# ══════════════════════════════════════════════════════════
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


# ══════════════════════════════════════════════════════════
#  ChainedCallContext — 链式调用上下文管理器
# ══════════════════════════════════════════════════════════
class ChainedCallContext:
    """
    在多个工具调用之间传递数据和状态。

    属性：
        max_iterations  最大迭代次数，防止无限循环（默认 10）
        steps           已执行的步骤列表，每项格式：
                        {"step": int, "tool": str, "args": dict,
                         "result": str, "success": bool}
        variables       中间变量字典，供后续步骤按名引用
        iteration       当前迭代计数
    """

    def __init__(self, max_iterations: int = 10):
        self.max_iterations = max_iterations
        self.steps: list[dict] = []
        self.variables: dict[str, object] = {}
        self.iteration: int = 0

    # ── 记录一步执行结果 ──────────────────────────────────
    def record_step(self, tool: str, args: dict,
                    result: str, success: bool = True) -> None:
        """记录每一步工具调用及其结果，同时存入中间变量。"""
        step_num = len(self.steps) + 1
        self.steps.append({
            "step": step_num,
            "tool": tool,
            "args": args,
            "result": result,
            "success": success
        })
        # 将结果存入 variables，key 格式：step{N}_result / {tool_name}_result
        self.variables[f"step{step_num}_result"] = result
        self.variables[f"{tool}_result"] = result

    # ── 构建给 LLM 看的步骤摘要 ──────────────────────────
    def steps_summary(self) -> str:
        """将已执行步骤格式化为可读文本，供 build_analysis_prompt 使用。"""
        if not self.steps:
            return "（尚未执行任何工具调用）"
        lines = []
        for s in self.steps:
            status_tag = "✅" if s["success"] else "❌"
            args_str = json.dumps(s["args"], ensure_ascii=False)
            # 结果过长时截断
            result_preview = s["result"]
            if len(result_preview) > 600:
                result_preview = result_preview[:600] + "...[已截断]"
            lines.append(
                f"步骤 {s['step']} {status_tag}  工具={s['tool']}\n"
                f"  参数：{args_str}\n"
                f"  结果：{result_preview}"
            )
        return "\n\n".join(lines)

    # ── 获取最新一步的结果 ────────────────────────────────
    @property
    def last_result(self) -> str:
        return self.steps[-1]["result"] if self.steps else ""

    # ── 是否超出迭代限制 ──────────────────────────────────
    @property
    def exhausted(self) -> bool:
        return self.iteration >= self.max_iterations


# ══════════════════════════════════════════════════════════
#  工具函数
# ══════════════════════════════════════════════════════════

def _project_root() -> str:
    return os.path.dirname(os.path.dirname(__file__))


def _skills_dir() -> str:
    return os.path.join(_project_root(), '.agents', 'skills')


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """解析 YAML front matter，返回 (meta_dict, body)。"""
    pattern = re.compile(r'^---\s*\n(.*?)\n---\s*\n', re.DOTALL)
    m = pattern.match(text)
    if not m:
        return {}, text
    meta = {}
    for line in m.group(1).splitlines():
        if ':' in line:
            k, _, v = line.partition(':')
            meta[k.strip()] = v.strip()
    return meta, text[m.end():]


# ── 工具 1：搜索文件（含关键词过滤）─────────────────────
def search_files(directory: str, keyword: str = "",
                 extensions: list[str] | None = None) -> str:
    """
    在指定目录下递归搜索文件。

    参数：
        directory   搜索根目录（相对于项目根目录或绝对路径）
        keyword     文件内容中包含的关键词（空则只按扩展名过滤）
        extensions  文件扩展名列表，如 [".py", ".md"]（空则不过滤）
    返回：
        JSON 字符串，包含匹配文件路径列表
    """
    if not os.path.isabs(directory):
        directory = os.path.join(_project_root(), directory)

    if not os.path.isdir(directory):
        return json.dumps(
            {"status": "error",
             "message": f"目录不存在: {directory}"},
            ensure_ascii=False
        )

    matches = []
    try:
        for root, _, files in os.walk(directory):
            # 跳过 venv / __pycache__ / .git 等目录
            skip_dirs = {'venv', '__pycache__', '.git', 'node_modules',
                         '.workbuddy'}
            root_parts = set(root.replace('\\', '/').split('/'))
            if root_parts & skip_dirs:
                continue

            for fname in files:
                if extensions:
                    ext = os.path.splitext(fname)[1].lower()
                    if ext not in extensions:
                        continue

                fpath = os.path.join(root, fname)

                if keyword:
                    try:
                        with open(fpath, 'r', encoding='utf-8',
                                  errors='ignore') as f:
                            content = f.read()
                        if keyword.lower() not in content.lower():
                            continue
                    except Exception:
                        continue

                matches.append(fpath)

    except Exception as e:
        return json.dumps(
            {"status": "error", "message": str(e)},
            ensure_ascii=False
        )

    return json.dumps(
        {"status": "success", "count": len(matches), "files": matches},
        ensure_ascii=False, indent=2
    )


# ── 工具 2：读取文件内容 ──────────────────────────────────
def read_file(filepath: str, max_chars: int = 3000) -> str:
    """
    读取文件内容，超长时截断。

    参数：
        filepath   文件路径（相对于项目根目录或绝对路径）
        max_chars  最多读取字符数（默认 3000）
    """
    if not os.path.isabs(filepath):
        filepath = os.path.join(_project_root(), filepath)

    if not os.path.isfile(filepath):
        return json.dumps(
            {"status": "error", "message": f"文件不存在: {filepath}"},
            ensure_ascii=False
        )

    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read(max_chars)
        truncated = os.path.getsize(filepath) > max_chars
        return json.dumps(
            {
                "status": "success",
                "filepath": filepath,
                "content": content,
                "truncated": truncated
            },
            ensure_ascii=False
        )
    except Exception as e:
        return json.dumps(
            {"status": "error", "message": str(e)},
            ensure_ascii=False
        )


# ── 工具 3：网页访问（curl）──────────────────────────────
def curl(url: str, max_chars: int = 4000) -> str:
    """
    访问网页并返回文本内容，自动去除 HTML 标签。

    参数：
        url       目标 URL
        max_chars 最多返回字符数（默认 4000）
    """
    try:
        parsed = urlparse(url)
        host = parsed.netloc
        path = parsed.path or '/'
        if parsed.query:
            path += '?' + parsed.query

        if parsed.scheme == 'https':
            conn = http.client.HTTPSConnection(host, timeout=15)
        else:
            conn = http.client.HTTPConnection(host, timeout=15)

        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; PracticeBot/1.0)",
            "Accept": "text/html,application/xhtml+xml;charset=utf-8",
            "Accept-Language": "zh-CN,zh;q=0.9"
        }
        conn.request("GET", path, headers=headers)
        resp = conn.getresponse()

        # 跟随重定向（最多 3 次）
        redirects = 0
        while resp.status in (301, 302, 303, 307, 308) and redirects < 3:
            location = resp.getheader("Location", "")
            if not location:
                break
            if location.startswith('/'):
                location = f"{parsed.scheme}://{host}{location}"
            conn.close()
            parsed2 = urlparse(location)
            host2 = parsed2.netloc or host
            path2 = parsed2.path or '/'
            if parsed2.query:
                path2 += '?' + parsed2.query
            if parsed2.scheme == 'https':
                conn = http.client.HTTPSConnection(host2, timeout=15)
            else:
                conn = http.client.HTTPConnection(host2, timeout=15)
            conn.request("GET", path2, headers=headers)
            resp = conn.getresponse()
            redirects += 1

        raw = resp.read(max_chars * 5).decode('utf-8', errors='ignore')
        conn.close()

        # 简单去除 HTML 标签
        text = re.sub(r'<style[^>]*?>.*?</style>', '', raw,
                      flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<script[^>]*?>.*?</script>', '', text,
                      flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'&nbsp;', ' ', text)
        text = re.sub(r'&[a-z]+;', '', text)
        text = re.sub(r'\s+', ' ', text).strip()

        if len(text) > max_chars:
            text = text[:max_chars] + "...[已截断]"

        return json.dumps(
            {"status": "success", "url": url,
             "content": text, "http_status": resp.status},
            ensure_ascii=False
        )

    except Exception as e:
        return json.dumps(
            {"status": "error", "message": str(e)},
            ensure_ascii=False
        )


# ── 工具 4：写入文件 ──────────────────────────────────────
def write_file(filepath: str, content: str,
               mode: str = 'w') -> str:
    """
    将内容写入文件（自动创建目录）。

    参数：
        filepath  目标文件路径（相对项目根目录或绝对路径）
        content   写入内容
        mode      'w'（覆盖，默认） 或 'a'（追加）
    """
    if not os.path.isabs(filepath):
        filepath = os.path.join(_project_root(), filepath)

    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, mode, encoding='utf-8') as f:
            f.write(content)
        return json.dumps(
            {"status": "success", "filepath": filepath,
             "bytes_written": len(content.encode('utf-8'))},
            ensure_ascii=False
        )
    except Exception as e:
        return json.dumps(
            {"status": "error", "message": str(e)},
            ensure_ascii=False
        )


# ── 工具 5：加载技能内容 ──────────────────────────────────
def load_skill_content(skill_name: str) -> str:
    """加载指定技能的 SKILL.md 正文。"""
    skills_root = _skills_dir()
    if not os.path.isdir(skills_root):
        return json.dumps(
            {"status": "error", "message": "skills 目录不存在"},
            ensure_ascii=False
        )
    for entry in os.listdir(skills_root):
        skill_dir = os.path.join(skills_root, entry)
        if not os.path.isdir(skill_dir):
            continue
        skill_md = os.path.join(skill_dir, 'SKILL.md')
        if not os.path.isfile(skill_md):
            continue
        with open(skill_md, 'r', encoding='utf-8') as f:
            raw = f.read()
        meta, body = _parse_frontmatter(raw)
        if entry == skill_name or meta.get('name') == skill_name:
            return json.dumps(
                {"status": "success",
                 "skill_name": skill_name,
                 "content": body.strip()},
                ensure_ascii=False
            )
    return json.dumps(
        {"status": "error",
         "message": f"技能 '{skill_name}' 不存在"},
        ensure_ascii=False
    )


# ── 工具注册表 ────────────────────────────────────────────
TOOL_REGISTRY: dict[str, callable] = {
    "search_files":      search_files,
    "read_file":         read_file,
    "curl":              curl,
    "write_file":        write_file,
    "load_skill_content": load_skill_content,
}

TOOL_DESCRIPTIONS = """## 可用工具

| 工具名 | 功能 | 核心参数 |
|--------|------|----------|
| search_files | 递归搜索目录下的文件，支持关键词和扩展名过滤 | directory, keyword, extensions |
| read_file | 读取文件内容 | filepath, max_chars(可选) |
| curl | 访问网页并返回文本 | url |
| write_file | 将内容写入文件（自动建目录） | filepath, content, mode(可选:w/a) |
| load_skill_content | 加载指定技能的详细规则 | skill_name |

## 工具间数据传递规则

- 前一步工具的结果会完整出现在"已执行步骤历史"中
- 你可以直接引用前步结果中的任何字段（文件路径、文本内容等）
- 例如：search_files 返回文件列表 → 逐一用 read_file 读取
- 例如：curl 返回网页内容 → 用 write_file 保存到本地
"""


# ══════════════════════════════════════════════════════════
#  build_analysis_prompt — 构建分析提示词
# ══════════════════════════════════════════════════════════
def build_analysis_prompt(user_request: str,
                          context: ChainedCallContext) -> str:
    """
    构建发送给 LLM 的分析提示词，包含：
      1. 用户原始请求
      2. 已执行的工具调用历史
      3. 可用工具说明
      4. 决策规则
      5. JSON 输出格式要求

    返回：
        str — 完整的用户消息文本
    """
    steps_text = context.steps_summary()

    prompt = f"""## 用户原始请求
{user_request}

## 已执行的工具调用历史（第 {context.iteration} 轮，共 {context.max_iterations} 轮上限）
{steps_text}

{TOOL_DESCRIPTIONS}

## 决策规则
1. 仔细分析用户请求，判断还需要哪些步骤才能完成任务。
2. 如果任务已经完成，返回 done=true 并给出最终总结性回答。
3. 如果还需要继续，选择最合适的下一个工具，返回 done=false。
4. 工具调用时，可以直接复用前步结果中的具体值（如文件路径、内容片段）。
5. 不要重复执行已经成功完成的步骤。
6. 如果某步出错，可以尝试替代方案，或在回答中说明原因。

## 输出格式要求（严格 JSON，不允许有任何其他文字）

任务完成时：
{{"done": true, "answer": "最终回答内容（对用户请求的完整总结）"}}

继续调用工具时：
{{"done": false, "tool_call": {{"name": "工具名称",
  "arguments": {{"参数名": "参数值"}}}}}}
"""
    return prompt


# ══════════════════════════════════════════════════════════
#  LLM 调用（非流式，专用于链式推理）
# ══════════════════════════════════════════════════════════
def call_llm(messages: list[dict], env_vars: dict,
             temperature: float = 0.3) -> tuple[str, dict]:
    """
    非流式 LLM 调用，用于链式推理（需要精确解析 JSON 输出）。
    返回 (response_text, stats)。
    """
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
        "stream": False,
        "max_tokens": 4096,
        "temperature": temperature,
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

        resp = conn.getresponse()
        body = resp.read().decode('utf-8')
        conn.close()

        if resp.status != 200:
            print(f"[LLM] HTTP {resp.status}: {body[:200]}")
            return "", {}

        data = json.loads(body)
        # 支持 tool_calls 格式（OpenAI Function Calling）
        choice = data["choices"][0]
        msg = choice.get("message", {})

        # 优先取 tool_calls
        if msg.get("tool_calls"):
            tc = msg["tool_calls"][0]["function"]
            synth = json.dumps(
                {"done": False,
                 "tool_call": {
                     "name": tc["name"],
                     "arguments": json.loads(tc.get("arguments", "{}"))
                 }},
                ensure_ascii=False
            )
            text = synth
        else:
            text = msg.get("content", "").strip()

        elapsed = time.time() - start_time
        usage = data.get("usage", {})
        stats = {
            "total_time": round(elapsed, 2),
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
        }
        return text, stats

    except Exception as e:
        print(f"[LLM] 调用失败: {e}")
        return "", {}


# ══════════════════════════════════════════════════════════
#  parse_chained_response — 解析链式响应
# ══════════════════════════════════════════════════════════
def parse_chained_response(raw: str) -> dict | None:
    """
    解析 LLM 返回的 JSON 决策对象。
    支持：
      - 纯 JSON
      - ```json ... ``` 包裹的 JSON
      - 混有其他文字时提取第一个 {...} 块

    返回：
        {"done": bool, "answer": str}
        或
        {"done": bool, "tool_call": {"name": str, "arguments": dict}}
        或 None（解析失败）
    """
    if not raw:
        return None

    # 1. 去掉 markdown 代码块
    text = re.sub(r'```json\s*', '', raw)
    text = re.sub(r'```\s*', '', text)
    text = text.strip()

    # 2. 提取第一个完整 {...} 块
    start = text.find('{')
    if start == -1:
        return None

    depth = 0
    end = start
    for i in range(start, len(text)):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    # 3. 尝试解析提取的块
    obj = None
    if end > start:
        try:
            obj = json.loads(text[start:end])
        except json.JSONDecodeError:
            obj = None

    # 4. fallback：花括号不匹配（如 answer 内含 {模板} 被截断）
    #    用 raw_decode 从 start 位置尽量解析合法 JSON
    if obj is None:
        try:
            decoder = json.JSONDecoder()
            obj, _ = decoder.raw_decode(text[start:])
        except json.JSONDecodeError:
            return None

    # 3. 校验结构
    if "done" not in obj:
        return None

    if obj["done"] is True:
        if "answer" not in obj:
            # 宽松兼容：LLM 可能用 "result" 或 "response"
            obj["answer"] = (
                obj.get("result") or obj.get("response") or str(obj)
            )
        return obj

    # done=false 时必须有 tool_call
    if "tool_call" not in obj:
        return None

    tc = obj["tool_call"]
    # 兼容 "args" 和 "arguments"
    if "args" in tc and "arguments" not in tc:
        tc["arguments"] = tc.pop("args")

    return obj


# ══════════════════════════════════════════════════════════
#  execute_chained_tool_call — 链式调用主引擎
# ══════════════════════════════════════════════════════════
def execute_chained_tool_call(user_request: str,
                              env_vars: dict,
                              max_iterations: int = 10,
                              verbose: bool = True) -> str:
    """
    执行链式工具调用的完整流程。

    流程：
      1. 初始化 ChainedCallContext 和消息历史
      2. 循环（最多 max_iterations 次）：
         a. 构建分析提示词
         b. 调用 LLM 获取决策
         c. 解析 JSON 响应
         d. 如果 done=true，返回最终答案
         e. 如果 done=false，执行工具，记录到上下文
      3. 超出限制时返回已有结果的总结

    参数：
        user_request    用户原始请求文本
        env_vars        环境变量字典（BASE_URL / MODEL / TOKEN）
        max_iterations  最大迭代次数
        verbose         是否打印详细日志

    返回：
        最终回答字符串
    """
    ctx = ChainedCallContext(max_iterations=max_iterations)

    # 系统提示词：说明链式调用规则
    system_prompt = """你是一个具备链式工具调用能力的 AI 智能体。

## 链式调用规则
1. 每次只决策一个工具调用，不要一次列出多步。
2. 根据已执行步骤的实际结果来决定下一步，而不是提前假设。
3. 工具返回的数据（如文件路径、网页内容）可以直接作为下一步工具的参数。
4. 当且仅当用户请求完全满足时，返回 done=true。
5. 你必须只输出 JSON，不要输出任何解释性文字。

## 链式调用示例

示例：用户请求"搜索包含关键词的文件并总结内容"

步骤1 决策：
{"done": false, "tool_call": {"name": "search_files",
  "arguments": {"directory": ".", "keyword": "def"}}}

步骤2 决策（拿到搜索结果后，逐文件读取）：
{"done": false, "tool_call": {"name": "read_file",
  "arguments": {"filepath": "practice05/skill_client.py"}}}

步骤3 决策（所有内容已读取，完成任务）：
{"done": true, "answer": "共找到 2 个文件，主要定义了以下函数：..."}
"""

    messages = [
        {"role": "system", "content": system_prompt},
    ]

    _banner("链式调用启动", verbose)
    _log(f"用户请求: {user_request}", verbose)

    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_time_start = time.time()

    while not ctx.exhausted:
        ctx.iteration += 1
        _log(f"\n{'─'*50}\n[第 {ctx.iteration} 轮]", verbose)

        # 构建本轮分析提示词
        analysis_prompt = build_analysis_prompt(user_request, ctx)
        messages_this_turn = messages + [
            {"role": "user", "content": analysis_prompt}
        ]

        # 调用 LLM
        raw_response, stats = call_llm(
            messages_this_turn, env_vars, temperature=0.2
        )

        total_prompt_tokens += stats.get("prompt_tokens", 0)
        total_completion_tokens += stats.get("completion_tokens", 0)

        if not raw_response:
            _log("[错误] LLM 未返回响应，终止链式调用。", verbose)
            break

        _log(f"[LLM 原始输出] {raw_response[:300]}", verbose)

        # 解析响应
        decision = parse_chained_response(raw_response)

        if decision is None:
            _log("[警告] 无法解析 LLM 响应为有效 JSON，跳过本轮。", verbose)
            # 将失败信息加入历史，让 LLM 下一轮知道
            ctx.record_step(
                tool="[解析失败]",
                args={},
                result=f"无法解析: {raw_response[:200]}",
                success=False
            )
            continue

        # 任务完成
        if decision.get("done") is True:
            answer = decision.get("answer", "（LLM 未提供最终回答）")
            _banner("任务完成", verbose)
            _log(answer, verbose)
            _print_chain_stats(
                ctx, total_prompt_tokens, total_completion_tokens,
                time.time() - total_time_start, verbose
            )
            return answer

        # 继续调用工具
        tc = decision.get("tool_call", {})
        tool_name = tc.get("name", "")
        tool_args = tc.get("arguments", {})

        if not tool_name:
            _log("[警告] done=false 但未提供 tool_call.name，跳过。", verbose)
            continue

        args_str = json.dumps(tool_args, ensure_ascii=False)
        _log(f"[工具调用] {tool_name}  参数: {args_str}", verbose)

        # 执行工具
        tool_result, success = _run_tool(tool_name, tool_args, verbose)

        # 记录到上下文（历史通过 ctx.steps 传入 analysis_prompt）
        ctx.record_step(
            tool=tool_name,
            args=tool_args,
            result=tool_result,
            success=success
        )

    # 超出迭代上限
    _log(f"\n[警告] 已达到最大迭代次数 ({max_iterations})，返回当前结果。", verbose)
    _print_chain_stats(
        ctx, total_prompt_tokens, total_completion_tokens,
        time.time() - total_time_start, verbose
    )

    if ctx.last_result:
        return f"（已达最大迭代次数）最后一步结果：\n{ctx.last_result}"
    return "（链式调用未能完成任务，请检查工具配置。）"


# ══════════════════════════════════════════════════════════
#  内部辅助
# ══════════════════════════════════════════════════════════
def _run_tool(tool_name: str, tool_args: dict,
              verbose: bool = True) -> tuple[str, bool]:
    """执行指定工具，返回 (result_str, success_bool)。"""
    fn = TOOL_REGISTRY.get(tool_name)
    if fn is None:
        msg = json.dumps(
            {"status": "error", "message": f"未知工具: {tool_name}"},
            ensure_ascii=False
        )
        _log(f"  [错误] {msg}", verbose)
        return msg, False

    try:
        result = fn(**tool_args)
        # 判断是否成功
        try:
            r_data = json.loads(result)
            success = r_data.get("status") != "error"
        except Exception:
            success = True

        # 打印结果摘要
        preview = result if len(result) < 200 else result[:200] + "..."
        _log(f"  [结果] {preview}", verbose)
        return result, success

    except TypeError as e:
        # 参数不匹配时友好提示
        msg = json.dumps(
            {"status": "error", "message": f"参数错误: {e}"},
            ensure_ascii=False
        )
        _log(f"  [参数错误] {e}", verbose)
        return msg, False

    except Exception as e:
        msg = json.dumps(
            {"status": "error", "message": str(e)},
            ensure_ascii=False
        )
        _log(f"  [执行错误] {e}", verbose)
        return msg, False


def _log(msg: str, verbose: bool) -> None:
    if verbose:
        print(msg)


def _banner(title: str, verbose: bool) -> None:
    if verbose:
        print(f"\n{'═'*50}")
        print(f"  {title}")
        print(f"{'═'*50}")


def _print_chain_stats(ctx: ChainedCallContext,
                       prompt_tokens: int,
                       completion_tokens: int,
                       elapsed: float,
                       verbose: bool) -> None:
    if not verbose:
        return
    print(f"\n{'━'*50}")
    print(
        f"[链式统计] 共 {len(ctx.steps)} 步  "
        f"迭代 {ctx.iteration} 次  "
        f"耗时 {elapsed:.1f}s  "
        f"Token {prompt_tokens+completion_tokens}"
    )
    print(f"{'━'*50}")


# ══════════════════════════════════════════════════════════
#  测试用例
# ══════════════════════════════════════════════════════════
TESTS = [
    {
        "id": "test1",
        "name": "文件搜索链式调用",
        "request": (
            "请查找 practice05 目录下所有包含'def'关键词的文件，"
            "并总结这些文件的主要内容"
        )
    },
    {
        "id": "test2",
        "name": "技能查询链式调用",
        "request": "我想了解 notice 技能的详细规则"
    },
    {
        "id": "test3",
        "name": "网页处理链式调用",
        "request": (
            "访问 https://www.nsu.edu.cn/HTML/news/2024/06/"
            "article_3974.html 并总结页面内容，"
            "保存到 practice06/summary.txt"
        )
    },
]


def run_tests(env_vars: dict, test_ids: list[str] | None = None) -> None:
    """运行指定测试用例（不指定则全部运行）。"""
    targets = [t for t in TESTS
               if test_ids is None or t["id"] in test_ids]

    for i, test in enumerate(targets, 1):
        print(f"\n{'#'*60}")
        print(f"# 测试 {i}/{len(targets)}：{test['name']}")
        print(f"# ID: {test['id']}")
        print(f"{'#'*60}")
        print(f"请求：{test['request']}\n")

        answer = execute_chained_tool_call(
            user_request=test["request"],
            env_vars=env_vars,
            max_iterations=10,
            verbose=True
        )

        print(f"\n[最终回答]\n{answer}")

        if i < len(targets):
            print("\n按 Enter 继续下一个测试...", end="")
            input()


# ══════════════════════════════════════════════════════════
#  主程序入口
# ══════════════════════════════════════════════════════════
def main():
    env_vars = load_env()
    if not env_vars:
        return

    # ── 命令行模式 ───────────────────────────────────────
    # python chained_tool_client.py test         → 全部测试
    # python chained_tool_client.py test1        → 单个测试
    # python chained_tool_client.py "自定义请求"  → 单次调用
    if len(sys.argv) > 1:
        arg = sys.argv[1]

        if arg == "test":
            run_tests(env_vars)
            return

        if arg in [t["id"] for t in TESTS]:
            run_tests(env_vars, test_ids=[arg])
            return

        # 自定义请求
        user_input = ' '.join(sys.argv[1:])
        print(f"你: {user_input}")
        answer = execute_chained_tool_call(
            user_input, env_vars, max_iterations=10
        )
        print(f"\n最终回答：\n{answer}")
        return

    # ── 交互式模式 ──────────────────────────────────────
    print("=" * 60)
    print("=== Practice06: 链式工具调用（Chained Tool Calls）===")
    print("输入 'test'  运行全部测试用例")
    print("输入 'test1/test2/test3' 运行指定测试")
    print("输入 'exit'  退出")
    print("=" * 60)

    try:
        while True:
            user_input = input("\n你: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ('exit', '退出'):
                print("再见！")
                break
            if user_input.lower() == 'test':
                run_tests(env_vars)
                continue
            if user_input.lower() in [t["id"] for t in TESTS]:
                run_tests(env_vars, test_ids=[user_input.lower()])
                continue

            answer = execute_chained_tool_call(
                user_input, env_vars, max_iterations=10
            )
            print(f"\n最终回答：\n{answer}")

    except KeyboardInterrupt:
        print("\n\n已退出。")


if __name__ == "__main__":
    main()

# AI智能体开发学习项目

## 项目概述

这是一个基于Python的AI智能体开发学习项目，旨在帮助开发者学习如何使用Python标准库与OpenAI兼容的大语言模型（LLM）API进行交互。项目提供了一个完整的客户端实现，支持流式输出、多轮对话，并包含性能统计功能。

**项目特色**：
- **流式输出**：实时显示LLM响应，提升用户体验
- **多轮对话**：自动维护对话历史，实现上下文连贯的交互
- **性能监控**：详细的token消耗、响应时间和处理速度统计
- **零依赖**：纯Python标准库实现，无需安装第三方包
- **教学友好**：代码结构清晰，注释详细，适合学习参考

## 核心功能

- **环境变量管理**：通过`.env`文件配置LLM服务参数
- **LLM API调用**：使用Python标准库`http.client`发送请求
- **流式输出支持**：实时显示LLM响应，提升用户体验
- **多轮对话支持**：维护对话历史，自动添加到上下文
- **性能统计**：统计token消耗、响应时间和处理速度
- **错误处理**：处理网络异常、编码问题等常见错误
- **优雅退出**：支持Ctrl+C强制退出和命令行退出
- **跨平台兼容**：支持Windows、Linux和macOS

## 技术架构

- **语言**：Python 3.11+
- **核心库**：
  - `http.client`：发送HTTP请求
  - `json`：处理JSON数据
  - `time`：性能统计
  - `os`：文件操作
  - `urllib.parse`：URL解析
- **依赖**：无第三方依赖，纯标准库实现
- **配置管理**：使用`.env`文件管理配置参数

## 环境要求

- Python 3.11或更高版本
- 网络连接（访问LLM服务）
- LLM服务（如OpenAI、Azure OpenAI、LM Studio等）

## 安装部署

### 1. 克隆项目

```bash
git clone <repository-url>
cd code_AI
```

### 2. 初始化Git仓库（如果尚未初始化）

```bash
git init
git add .
git commit -m "Initial commit"
```

### 3. 创建虚拟环境

```bash
# Windows
python -m venv venv

# Linux/macOS
python3 -m venv venv
```

### 4. 激活虚拟环境

```bash
# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate
```

### 5. 配置环境变量

复制`.env.example`文件为`.env`并填写正确的配置参数：

```bash
cp .env.example .env
```

编辑`.env`文件，填写以下参数：

```env
# OpenAI兼容协议的LLM配置

# 基础URL
BASE_URL="http://127.0.0.1:1234/v1"  # 例如LM Studio的本地地址

# 模型名称
MODEL="qwen3.5-9b"  # 或其他支持的模型

# API密钥
TOKEN="your-api-key-here"  # 本地服务通常不需要实际密钥

# 其他可选配置
TIMEOUT=30
MAX_TOKENS=1000
TEMPERATURE=0.7
```

## 使用指南

### 运行多轮对话（流式输出）

```bash
python practice01/llm_client.py
```

程序将进入交互模式，您可以输入问题与LLM进行对话。

**退出方式**：
- 输入`exit`或`退出`正常结束对话
- 按`Ctrl+C`强制退出程序

**功能特点**：
- 流式输出：实时显示LLM的响应内容
- 历史记录：自动将对话历史添加到上下文中
- 性能统计：每次对话后显示详细的性能数据

### 运行工具调用功能（流式输出）

```bash
# 交互式模式
python practice02/tool_client.py

# 命令行模式
python practice02/tool_client.py 列出当前目录的文件
python practice02/tool_client.py 访问百度
```

**工具调用功能**：
- **list_files**：列出目录下的文件及其属性
- **rename_file**：修改文件名称
- **delete_file**：删除文件
- **create_file**：创建文件并写入内容
- **read_file**：读取文件内容
- **curl**：通过网络访问网页并返回网页内容

**使用示例**：
```
=== 工具调用模式（流式输出）===
输入 'exit' 或 '退出' 结束对话
按 Ctrl+C 强制退出
--------------------------------------------------

你: 列出当前目录的文件

助手: {"tool_call": {"name": "list_files", "args": {"directory": "."}}}

执行工具调用: list_files
工具执行结果: {"status": "success", "data": [{"name": "README.md", "type": "file", "size": 3000, "mtime": "2026-04-15 10:00:00", "path": ".\README.md"}, ...]}

本次统计信息
耗时: 1.23 秒
提示token: 100
回复token: 50
总token: 150
速度: 121.95 tokens/s

你: 访问百度

助手: {"tool_call": {"name": "curl", "args": {"url": "https://www.baidu.com"}}}

执行工具调用: curl
工具执行结果: {"status": "success", "data": "<!DOCTYPE html>... (内容过长，已截断)"}

本次统计信息
耗时: 0.56 秒
提示token: 150
回复token: 60
总token: 210
速度: 375.00 tokens/s
```

### practice03 工具调用示例

#### 1. 列出目录文件

```
你: 列出当前目录的文件
助手: {"tool_call": {"name": "list_files", "args": {"directory": "."}}}
```

#### 2. 创建文件

```
你: 创建一个名为test.txt的文件，内容为"Hello World"
助手: {"tool_call": {"name": "create_file", "args": {"directory": ".", "file_name": "test.txt", "content": "Hello World"}}}
```

#### 3. 读取文件

```
你: 读取test.txt文件
助手: {"tool_call": {"name": "read_file", "args": {"directory": ".", "file_name": "test.txt"}}}
```

#### 4. 网络访问

```
你: 访问百度
助手: {"tool_call": {"name": "curl", "args": {"url": "https://www.baidu.com"}}}
```

### 聊天历史压缩机制

- **触发条件**：对话轮数超过5轮或上下文长度超过3000字符
- **压缩策略**：保留最近30%的对话原文，压缩前70%的内容
- **压缩方式**：调用LLM对前70%的对话内容进行总结
- **压缩效果**：减少上下文长度，提高对话效率
- **关键信息提取**：每5轮对话自动提取关键信息，按照5W规则记录到本地日志文件

### 示例对话

```
=== 多轮对话模式（流式输出）===
输入 'exit' 或 '退出' 结束对话
按 Ctrl+C 强制退出
--------------------------------------------------

你: 你好，我想了解一下AI智能体开发

助手: 你好！AI智能体开发是一个非常有趣的领域，它涉及创建能够自主执行任务、做出决策并与环境交互的智能系统。

本次统计信息
耗时: 2.34 秒
提示token: 12
回复token: 56
总token: 68
速度: 29.06 tokens/s

你: 什么是大语言模型？

助手: 大语言模型（Large Language Model，LLM）是一种基于深度学习的人工智能模型，通过大规模文本数据训练而成...

本次统计信息
耗时: 3.12 秒
提示token: 78
回复token: 124
总token: 202
速度: 64.74 tokens/s
```

### 流式输出说明

流式输出功能通过以下方式实现：

1. **实时响应**：LLM生成的内容会逐字显示，而不是等待完整响应
2. **用户体验**：减少等待时间，提供更自然的交互体验
3. **技术实现**：使用SSE（Server-Sent Events）协议接收数据流

### 多轮对话上下文管理

程序自动维护对话历史，每次新的请求都会包含之前的对话内容：

```python
messages = [
    {"role": "user", "content": "第一个问题"},
    {"role": "assistant", "content": "第一个回答"},
    {"role": "user", "content": "第二个问题"},
    {"role": "assistant", "content": "第二个回答"},
    # ... 继续添加
]
```

这种设计确保LLM能够理解对话的上下文，提供连贯的回复。

## 常见问题解答

### 1. 连接错误：`[WinError 10061] 由于目标计算机积极拒绝，无法连接`

**解决方案**：
- 确认LLM服务（如LM Studio）已启动
- 检查`.env`文件中的`BASE_URL`配置是否正确
- 验证网络连接是否正常

### 2. SSL错误：`[SSL: WRONG_VERSION_NUMBER] wrong version number`

**解决方案**：
- 检查`BASE_URL`的协议是否正确（HTTP或HTTPS）
- 本地服务（如LM Studio）通常使用HTTP协议

### 3. Unicode编码错误：`UnicodeEncodeError: 'gbk' codec can't encode character`

**解决方案**：
- 程序已内置处理此类错误的代码，会自动替换无法编码的字符

### 4. 如何选择合适的LLM服务？

**建议**：
- 初学者：使用LM Studio（本地部署，无需API密钥）
- 专业开发：使用OpenAI或Azure OpenAI（需要API密钥）
- 研究用途：使用开源模型（如LLaMA、Mistral等）

### 5. 流式输出有什么优势？

**优势**：
- **实时响应**：无需等待完整生成，立即看到内容
- **用户体验**：减少等待焦虑，提供更自然的交互
- **性能监控**：可以实时观察生成过程
- **中断控制**：可以随时通过Ctrl+C中断生成

### 6. 如何正确退出程序？

**退出方式**：
- **正常退出**：输入`exit`或`退出`，程序会优雅地结束对话
- **强制退出**：按`Ctrl+C`，程序会捕获中断信号并显示退出信息

**注意事项**：
- 强制退出不会保存对话历史
- 建议在对话完成后使用正常退出方式
- 如果程序卡住，可以使用强制退出

## 项目结构

```
code_AI/
├── .env.example          # 环境变量模板
├── .gitignore           # Git忽略文件
├── practice01/          # 练习代码目录
│   └── llm_client.py    # LLM客户端实现
├── practice02/          # 工具调用功能目录
│   └── tool_client.py   # 带工具调用的LLM客户端
├── practice03/          # 工具调用客户端（带聊天历史压缩）
│   ├── tool_client.py   # 主程序文件
│   └── README.md        # 项目说明文档
├── README.md            # 项目文档
└── venv/                # 虚拟环境（自动生成）
```

## 核心功能模块

### 1. 环境变量管理

```python
def load_env():
    # 读取.env文件并解析配置参数
    # 返回环境变量字典
```

### 2. 流式输出API调用

```python
def call_llm_stream(messages, env_vars):
    # 构建并发送HTTP请求（启用流式输出）
    # 实时处理SSE数据流
    # 统计性能指标
    # 返回完整响应和统计信息
```

**流式输出实现细节**：
- 设置`"stream": True`参数启用流式输出
- 使用`response.readline()`逐行读取SSE数据
- 解析`data:`前缀的JSON数据
- 实时显示`delta.content`内容

### 3. 多轮对话管理

```python
def main():
    # 初始化对话历史
    # 处理用户输入（支持Ctrl+C退出）
    # 调用流式输出API
    # 维护对话上下文
    # 显示性能统计
```

**退出机制**：
- 正常退出：输入`exit`或`退出`
- 强制退出：捕获`KeyboardInterrupt`异常（Ctrl+C）

### 4. 工具调用功能（practice02）

**核心功能**：
- 工具函数：实现文件操作和网络访问功能
- 工具调用解析：解析LLM返回的工具调用请求
- 工具执行：执行相应的工具函数并返回结果
- 系统提示词：包含工具调用能力的系统提示词

**工具函数**：

```python
# 列出目录下的文件及其属性
def list_files(directory):
    # 实现文件列表功能

# 修改文件名称
def rename_file(directory, old_name, new_name):
    # 实现文件重命名功能

# 删除文件
def delete_file(directory, file_name):
    # 实现文件删除功能

# 创建文件并写入内容
def create_file(directory, file_name, content):
    # 实现文件创建功能

# 读取文件内容
def read_file(directory, file_name):
    # 实现文件读取功能

# 网络访问
def curl(url):
    # 实现网络访问功能
```

**工具调用解析**：

```python
def parse_tool_call(response):
    # 解析LLM返回的工具调用请求
    # 处理Markdown代码块
    # 提取工具名称和参数
```

**工具执行**：

```python
def execute_tool_call(tool_name, tool_args):
    # 根据工具名称执行相应的工具函数
    # 返回工具执行结果
```

## 贡献指南

1. **Fork** 本项目
2. **创建** 您的特性分支 (`git checkout -b feature/amazing-feature`)
3. **提交** 您的更改 (`git commit -m 'Add some amazing feature'`)
4. **推送到** 分支 (`git push origin feature/amazing-feature`)
5. **开启** 一个Pull Request

## 许可证

本项目采用MIT许可证。详见[LICENSE](LICENSE)文件。

## 联系方式

- 项目维护者：[Your Name]
- 邮箱：[your.email@example.com]
- GitHub：[your-github-username]

---

**注意**：本项目仅用于学习和教育目的，实际使用时请遵守相关LLM服务的使用条款和隐私政策。
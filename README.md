# AI智能体开发学习项目

## 项目概述

这是一个基于Python的AI智能体开发学习项目，旨在帮助开发者学习如何使用Python标准库与OpenAI兼容的大语言模型（LLM）API进行交互。项目提供了一个完整的客户端实现，支持单轮和多轮对话，并包含性能统计功能。

## 核心功能

- **环境变量管理**：通过`.env`文件配置LLM服务参数
- **LLM API调用**：使用Python标准库`http.client`发送请求
- **多轮对话支持**：维护对话历史，实现上下文连贯的交互
- **性能统计**：统计token消耗、响应时间和处理速度
- **错误处理**：处理网络异常、编码问题等常见错误
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

### 运行多轮对话

```bash
python practice01/llm_client.py
```

程序将进入交互模式，您可以输入问题与LLM进行对话。输入`exit`或`退出`结束对话。

### 示例对话

```
=== 多轮对话模式 ===
输入 'exit' 或 '退出' 结束对话

你: 你好，我想了解一下AI智能体开发

助手: 你好！AI智能体开发是一个非常有趣的领域，它涉及创建能够自主执行任务、做出决策并与环境交互的智能系统。

Statistics:
Total time: 2.34 seconds
Prompt tokens: 12
Completion tokens: 56
Total tokens: 68
Tokens per second: 29.06

你: 什么是大语言模型？

助手: 大语言模型（Large Language Model，LLM）是一种基于深度学习的人工智能模型，通过大规模文本数据训练而成...

Statistics:
Total time: 3.12 seconds
Prompt tokens: 78
Completion tokens: 124
Total tokens: 202
Tokens per second: 64.74
```

### 预设对话示例

如果您希望运行预设的对话示例（非交互式），可以修改`main()`函数中的`conversation`列表：

```python
# 预设的多轮对话示例
conversation = [
    "你好，我想了解一下AI智能体开发",
    "什么是大语言模型？",
    "如何使用Python调用LLM API？",
    "多轮对话和单轮对话有什么区别？"
]
```

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

## 项目结构

```
code_AI/
├── .env.example          # 环境变量模板
├── .gitignore           # Git忽略文件
├── practice01/          # 练习代码目录
│   └── llm_client.py    # LLM客户端实现
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

### 2. LLM API调用

```python
def call_llm(messages, env_vars):
    # 构建并发送HTTP请求
    # 处理响应并统计性能
    # 返回结果和统计信息
```

### 3. 多轮对话管理

```python
def main():
    # 初始化对话历史
    # 处理用户输入
    # 调用LLM API
    # 维护对话上下文
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
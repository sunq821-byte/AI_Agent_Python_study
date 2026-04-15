"""
file_tools.py - 文件操作工具函数集
提供 5 个标准文件操作函数，供 LLM Tool Call 使用

每个函数均返回统一格式:
    {"success": bool, "data": Any, "error": str | None}
"""

import os
import stat
import time


# ─────────────────────────────────────────────
# 工具 1：列出目录下的文件及基本属性
# ─────────────────────────────────────────────
def list_files(directory: str) -> dict:
    """
    列出指定目录下所有文件（含子目录）的基本信息。

    参数:
        directory (str): 要列出内容的目录路径

    返回:
        dict: {
            "success": bool,
            "data": [
                {
                    "name": str,        # 文件/目录名
                    "type": str,        # "file" | "directory"
                    "size_bytes": int,  # 文件大小（字节），目录为 0
                    "size_human": str,  # 人类可读大小，如 "1.23 KB"
                    "modified_at": str, # 最后修改时间，ISO 格式
                    "permissions": str  # 权限字符串，如 "rw-r--r--"
                },
                ...
            ],
            "error": str | None
        }
    """
    try:
        if not os.path.exists(directory):
            return {"success": False, "data": None,
                    "error": f"目录不存在: {directory}"}
        if not os.path.isdir(directory):
            return {"success": False, "data": None,
                    "error": f"路径不是目录: {directory}"}

        entries = []
        for entry_name in os.listdir(directory):
            full_path = os.path.join(directory, entry_name)
            try:
                st = os.stat(full_path)
                is_dir = os.path.isdir(full_path)
                size_bytes = st.st_size if not is_dir else 0
                modified_at = time.strftime(
                    "%Y-%m-%d %H:%M:%S", time.localtime(st.st_mtime)
                )
                # 构造权限字符串
                mode = st.st_mode
                perms = stat.filemode(mode)

                entries.append({
                    "name": entry_name,
                    "type": "directory" if is_dir else "file",
                    "size_bytes": size_bytes,
                    "size_human": _human_size(size_bytes),
                    "modified_at": modified_at,
                    "permissions": perms
                })
            except PermissionError:
                entries.append({
                    "name": entry_name,
                    "type": "unknown",
                    "size_bytes": 0,
                    "size_human": "N/A",
                    "modified_at": "N/A",
                    "permissions": "N/A"
                })

        # 按类型（目录优先）再按名称排序
        entries.sort(key=lambda x: (0 if x["type"] == "directory" else 1,
                                     x["name"].lower()))
        return {"success": True, "data": entries, "error": None}

    except Exception as e:
        return {"success": False, "data": None, "error": str(e)}


# ─────────────────────────────────────────────
# 工具 2：重命名文件
# ─────────────────────────────────────────────
def rename_file(directory: str, old_name: str, new_name: str) -> dict:
    """
    将指定目录下的某个文件或目录重命名。

    参数:
        directory (str): 目录路径
        old_name  (str): 原文件名（不含路径）
        new_name  (str): 新文件名（不含路径）

    返回:
        dict: {"success": bool, "data": str | None, "error": str | None}
              data 为操作成功后的新完整路径
    """
    try:
        if not os.path.exists(directory):
            return {"success": False, "data": None,
                    "error": f"目录不存在: {directory}"}

        old_path = os.path.join(directory, old_name)
        new_path = os.path.join(directory, new_name)

        if not os.path.exists(old_path):
            return {"success": False, "data": None,
                    "error": f"源文件不存在: {old_path}"}
        if os.path.exists(new_path):
            return {"success": False, "data": None,
                    "error": f"目标文件已存在，重命名被拒绝: {new_path}"}

        os.rename(old_path, new_path)
        return {"success": True, "data": new_path,
                "error": None}

    except Exception as e:
        return {"success": False, "data": None, "error": str(e)}


# ─────────────────────────────────────────────
# 工具 3：删除文件
# ─────────────────────────────────────────────
def delete_file(directory: str, filename: str) -> dict:
    """
    删除指定目录下的某个文件（仅限文件，不删除目录）。

    参数:
        directory (str): 目录路径
        filename  (str): 要删除的文件名（不含路径）

    返回:
        dict: {"success": bool, "data": str | None, "error": str | None}
              data 为被删除文件的完整路径（操作成功时）
    """
    try:
        if not os.path.exists(directory):
            return {"success": False, "data": None,
                    "error": f"目录不存在: {directory}"}

        file_path = os.path.join(directory, filename)

        if not os.path.exists(file_path):
            return {"success": False, "data": None,
                    "error": f"文件不存在: {file_path}"}
        if os.path.isdir(file_path):
            return {"success": False, "data": None,
                    "error": f"目标是目录而非文件，删除被拒绝: {file_path}"}

        os.remove(file_path)
        return {"success": True, "data": file_path, "error": None}

    except Exception as e:
        return {"success": False, "data": None, "error": str(e)}


# ─────────────────────────────────────────────
# 工具 4：新建文件并写入内容
# ─────────────────────────────────────────────
def create_file(directory: str, filename: str, content: str = "") -> dict:
    """
    在指定目录下新建一个文件，并写入内容（目录不存在时自动创建）。

    参数:
        directory (str): 目标目录路径
        filename  (str): 新文件名（不含路径）
        content   (str): 要写入的文本内容，默认为空字符串

    返回:
        dict: {"success": bool, "data": str | None, "error": str | None}
              data 为新建文件的完整路径（操作成功时）
    """
    try:
        # 目录不存在则递归创建
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

        file_path = os.path.join(directory, filename)

        if os.path.exists(file_path):
            return {"success": False, "data": None,
                    "error": f"文件已存在，创建被拒绝（请先删除或改用其他名称）: {file_path}"}

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return {"success": True, "data": file_path, "error": None}

    except Exception as e:
        return {"success": False, "data": None, "error": str(e)}


# ─────────────────────────────────────────────
# 工具 5：读取文件内容
# ─────────────────────────────────────────────
def read_file(directory: str, filename: str) -> dict:
    """
    读取指定目录下某个文件的文本内容。

    参数:
        directory (str): 目录路径
        filename  (str): 文件名（不含路径）

    返回:
        dict: {"success": bool, "data": str | None, "error": str | None}
              data 为文件文本内容（操作成功时）
    """
    try:
        if not os.path.exists(directory):
            return {"success": False, "data": None,
                    "error": f"目录不存在: {directory}"}

        file_path = os.path.join(directory, filename)

        if not os.path.exists(file_path):
            return {"success": False, "data": None,
                    "error": f"文件不存在: {file_path}"}
        if os.path.isdir(file_path):
            return {"success": False, "data": None,
                    "error": f"目标是目录而非文件: {file_path}"}

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        return {"success": True, "data": content, "error": None}

    except UnicodeDecodeError:
        return {"success": False, "data": None,
                "error": "文件编码不是 UTF-8，无法以文本方式读取"}
    except Exception as e:
        return {"success": False, "data": None, "error": str(e)}


# ─────────────────────────────────────────────
# 内部辅助：字节数 → 人类可读
# ─────────────────────────────────────────────
def _human_size(size_bytes: int) -> str:
    if size_bytes == 0:
        return "0 B"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}" if unit != "B" else f"{size_bytes} B"
        size_bytes /= 1024
    return f"{size_bytes:.2f} PB"


# ─────────────────────────────────────────────
# 统一工具调度入口（供 llm_client.py 调用）
# ─────────────────────────────────────────────
TOOL_REGISTRY = {
    "list_files": list_files,
    "rename_file": rename_file,
    "delete_file": delete_file,
    "create_file": create_file,
    "read_file":   read_file,
}


def dispatch_tool(tool_name: str, arguments: dict) -> dict:
    """
    根据工具名称和参数，调度并执行对应的工具函数。

    参数:
        tool_name  (str):  工具名称，须在 TOOL_REGISTRY 中注册
        arguments  (dict): 工具所需的参数字典

    返回:
        dict: 工具函数的返回值（统一格式）
    """
    if tool_name not in TOOL_REGISTRY:
        return {
            "success": False,
            "data": None,
            "error": f"未知工具: {tool_name}，可用工具: {list(TOOL_REGISTRY.keys())}"
        }
    try:
        return TOOL_REGISTRY[tool_name](**arguments)
    except TypeError as e:
        return {"success": False, "data": None,
                "error": f"参数错误: {e}"}

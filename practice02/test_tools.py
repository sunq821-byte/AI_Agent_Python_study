"""
practice02/test_tools.py
========================
5 个文件操作工具函数的单元测试脚本
运行: python practice02/test_tools.py
"""

import sys
import os
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(__file__))
from file_tools import (
    list_files, create_file, read_file,
    rename_file, delete_file, dispatch_tool
)

PASS = "[OK]"
FAIL = "[FAIL]"


def run_tests():
    # 使用临时目录，不影响项目文件
    tmp = tempfile.mkdtemp(prefix="practice02_test_")
    print("临时测试目录:", tmp)
    print()

    errors = []

    try:
        # ── 测试 1：list_files 空目录 ──
        r = list_files(tmp)
        if r["success"] and isinstance(r["data"], list) and len(r["data"]) == 0:
            print(PASS, "list_files (空目录): 文件数=0")
        else:
            errors.append("list_files 空目录失败")
            print(FAIL, "list_files 空目录:", r)

        # ── 测试 4：create_file ──
        content = "Hello, Tool Call!\n这是一个工具调用测试文件。\n第三行内容。"
        r = create_file(tmp, "hello.txt", content)
        if r["success"] and os.path.isfile(r["data"]):
            print(PASS, "create_file:", r["data"])
        else:
            errors.append("create_file 失败")
            print(FAIL, "create_file:", r)

        # ── 测试 5：read_file ──
        r = read_file(tmp, "hello.txt")
        if r["success"] and r["data"] == content:
            print(PASS, "read_file: 内容完整匹配")
        else:
            errors.append("read_file 失败或内容不匹配")
            print(FAIL, "read_file:", r)

        # ── 测试 1 再次：list_files 有文件 ──
        r = list_files(tmp)
        if r["success"] and len(r["data"]) == 1:
            entry = r["data"][0]
            print(PASS, "list_files (有文件): name={} size={}".format(
                entry["name"], entry["size_human"]))
        else:
            errors.append("list_files 有文件失败")
            print(FAIL, "list_files 有文件:", r)

        # ── 测试 2：rename_file ──
        r = rename_file(tmp, "hello.txt", "hello_renamed.txt")
        if r["success"] and os.path.isfile(os.path.join(tmp, "hello_renamed.txt")):
            print(PASS, "rename_file: hello.txt -> hello_renamed.txt")
        else:
            errors.append("rename_file 失败")
            print(FAIL, "rename_file:", r)

        # ── 测试 3：delete_file ──
        r = delete_file(tmp, "hello_renamed.txt")
        if r["success"] and not os.path.exists(os.path.join(tmp, "hello_renamed.txt")):
            print(PASS, "delete_file: 文件已删除")
        else:
            errors.append("delete_file 失败")
            print(FAIL, "delete_file:", r)

        # ── 验证目录为空 ──
        r = list_files(tmp)
        if r["success"] and len(r["data"]) == 0:
            print(PASS, "delete 后目录为空: 确认")
        else:
            errors.append("delete 后目录不为空")
            print(FAIL, "delete 后目录:", r)

        # ── dispatch_tool 统一入口 ──
        r = dispatch_tool("create_file", {
            "directory": tmp,
            "filename": "dispatch_test.txt",
            "content": "通过dispatch_tool调用"
        })
        if r["success"]:
            print(PASS, "dispatch_tool 调度 create_file: OK")
        else:
            errors.append("dispatch_tool 失败")
            print(FAIL, "dispatch_tool:", r)

        # ── dispatch 未知工具错误处理 ──
        r = dispatch_tool("unknown_tool", {})
        if not r["success"] and "未知工具" in (r.get("error") or ""):
            print(PASS, "dispatch_tool 未知工具错误处理: OK")
        else:
            errors.append("未知工具错误处理失败")
            print(FAIL, "未知工具:", r)

        # ── 边界测试：读取不存在的文件 ──
        r = read_file(tmp, "nonexistent.txt")
        if not r["success"] and r["error"]:
            print(PASS, "read_file (不存在文件) 正确返回错误:", r["error"])
        else:
            errors.append("read_file 不存在文件应返回错误")
            print(FAIL, "read_file 不存在文件:", r)

        # ── 边界测试：重复创建同名文件 ──
        create_file(tmp, "dup.txt", "first")
        r = create_file(tmp, "dup.txt", "second")
        if not r["success"] and r["error"]:
            print(PASS, "create_file (重复文件名) 正确拒绝:", r["error"])
        else:
            errors.append("重复创建文件应被拒绝")
            print(FAIL, "重复创建文件:", r)

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # ── 汇总 ──
    print()
    print("=" * 40)
    if not errors:
        print("  所有测试通过！(11/11)")
    else:
        print("  失败: {} 项".format(len(errors)))
        for e in errors:
            print("    -", e)
    print("=" * 40)
    return len(errors) == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)

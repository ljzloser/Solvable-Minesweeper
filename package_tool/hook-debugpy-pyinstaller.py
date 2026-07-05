"""
PyInstaller runtime hook for debugpy compatibility.
在 import debugpy 之前修复路径问题，确保 _vendored 目录可被找到。
"""
import os
import sys

# PyInstaller 打包后 __file__ 指向临时目录或 zip 内，
# debugpy/_vendored/__init__.py 用 os.path.abspath(__file__) 定位资源会失败。
# 此 hook 在任何代码执行前将 debugpy 的真实解压路径注入 sys._MEIPASS 搜索逻辑。

def _fix_debugpy_paths():
    # PyInstaller 运行时，已解压的文件在 sys._MEIPASS 下
    meipass = getattr(sys, "_MEIPASS", None)
    if not meipass:
        return  # 非打包环境，不需要处理

    debugpy_dir = os.path.join(meipass, "debugpy")
    vendored_dir = os.path.join(debugpy_dir, "_vendored")

    if os.path.isdir(debugpy_dir):
        # 确保 debugpy 在 sys.path 中靠前（PyInstaller 已处理，但保险起见）
        if debugpy_dir not in sys.path:
            sys.path.insert(0, debugpy_dir)

_fix_debugpy_paths()

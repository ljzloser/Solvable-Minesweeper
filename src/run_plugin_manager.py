"""
启动插件管理器进程

独立进程运行，连接到扫雷主进程
"""
import sys
import os
import argparse

# 确保 src 目录在路径中
src_dir = os.path.dirname(os.path.abspath(__file__))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)


def main():
    parser = argparse.ArgumentParser(description="插件管理器")
    parser.add_argument(
        "--endpoint",
        "-e",
        default=None,
        help="ZMQ 端点地址（默认 tcp://127.0.0.1:5555）",
    )
    parser.add_argument(
        "--no-gui",
        action="store_true",
        help="不显示界面（后台运行）",
    )
    parser.add_argument(
        "--plugin-dir",
        "-p",
        action="append",
        help="插件目录（可多次指定）",
    )
    args = parser.parse_args()

    # 初始化 loguru 日志系统
    from plugin_manager.app_paths import get_log_dir
    from plugin_manager.logging_setup import init_logging
    init_logging(get_log_dir(), console=True)
    
    # 确定端点（Windows 不支持 ipc，使用 tcp）
    if args.endpoint is None:
        endpoint = "tcp://127.0.0.1:5555"
    else:
        endpoint = args.endpoint
    
    # 确定插件目录
    plugin_dirs = args.plugin_dir
    if plugin_dirs is None:
        # 默认插件目录
        plugin_dirs = [os.path.join(src_dir, "plugins")]
    
    from plugin_manager import PluginManager
    
    # 创建并启动
    manager = PluginManager(
        endpoint=endpoint,
        plugin_dirs=plugin_dirs,
    )
    
    if args.no_gui:
        # 后台模式
        try:
            manager.start()
            print(f"插件管理器已启动: {endpoint}")
            print("按 Ctrl+C 停止")
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            manager.stop()
    else:
        # GUI 模式
        from PyQt5.QtWidgets import QApplication
        app = QApplication(sys.argv)
        manager.start_with_gui(app)
        sys.exit(app.exec_())


if __name__ == "__main__":
    main()

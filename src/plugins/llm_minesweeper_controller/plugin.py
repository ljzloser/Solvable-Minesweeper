"""
llm_minesweeper_controller - 插件主类
"""
from __future__ import annotations

from ctypes import cast
import json
from typing import Dict, Any, Optional, List

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import QThread, pyqtSignal

from plugin_sdk import BasePlugin, PluginInfo, make_plugin_icon, WindowMode
from plugin_sdk.config_types import OtherInfoBase
from shared_types.events import BoardUpdateEvent, GameStatusChangeEvent
from shared_types.commands import NewGameCommand, MouseClickCommand

from .widgets import LlmMinesweeperControllerWidget
from .config import LlmMinesweeperControllerConfig
from .api_client import LLMClient, ChatResponse
from .function_registry import FunctionRegistry


class LLMWorker(QThread):
    """LLM 工作线程"""

    log_signal = pyqtSignal(str)
    chat_signal = pyqtSignal(str, str)  # role, text
    finished_signal = pyqtSignal(bool, str)  # success, message

    def __init__(self, client: LLMClient, registry: FunctionRegistry,
                 messages: List[Dict[str, Any]]):
        super().__init__()
        self.client = client
        self.registry = registry
        self.messages = messages
        self._stop_flag = False

    def stop(self) -> None:
        """请求停止工作线程"""
        self._stop_flag = True
        self.requestInterruption()

    def run(self):
        """执行多轮对话循环（无上限）"""
        try:
            tools = self.registry.get_tools_schema()
            round_num = 0

            while True:
                # 检查停止标志
                if self._stop_flag or self.isInterruptionRequested():
                    self.finished_signal.emit(False, "用户请求停止")
                    return

                round_num += 1
                self.log_signal.emit(f"=== 第 {round_num} 轮对话 ===")

                # 调用 LLM
                response: ChatResponse = self.client.chat(
                    messages=self.messages,
                    tools=tools,
                    temperature=0.3,
                )

                if not response.success:
                    self.finished_signal.emit(
                        False, f"API 调用失败: {response.error}")
                    return

                # 显示 LLM 文本回复
                if response.has_content:
                    self.chat_signal.emit("assistant", response.content)

                # 检查是否需要调用工具
                if response.has_tool_calls:
                    # 将 assistant 消息加入历史
                    self.messages.append(
                        LLMClient.build_assistant_tool_message(
                            response.content,
                            response.tool_calls
                        )
                    )

                    # 处理每个 tool_call
                    for tool_call in response.tool_calls:
                        tool_call_id = tool_call.get("id", "")
                        func_data = tool_call.get("function", {})
                        func_name = func_data.get("name", "")

                        try:
                            func_args_str = func_data.get("arguments", "{}")
                            func_args = json.loads(func_args_str) if isinstance(
                                func_args_str, str) else func_args_str
                        except json.JSONDecodeError:
                            func_args = {}

                        self.log_signal.emit(f"调用函数: {func_name}({func_args})")
                        self.chat_signal.emit(
                            "tool", f"{func_name}({func_args})")

                        # 执行函数
                        result = self.registry.execute_function(
                            func_name, func_args)

                        self.log_signal.emit(f"执行结果: {result}")

                        # 构建 tool 结果消息
                        tool_msg = LLMClient.build_tool_result_message(
                            tool_call_id, result)
                        self.messages.append(tool_msg)

                    # 继续下一轮对话（让 LLM 处理工具结果）
                    continue

                # 没有 tool_calls，对话结束
                self.finished_signal.emit(True, "LLM 分析完成")
                return

        except Exception as e:
            self.finished_signal.emit(False, f"执行异常: {str(e)}")


class LlmMinesweeperControllerPlugin(BasePlugin):
    """使用 LLM 控制扫雷的插件"""

    _widget: LlmMinesweeperControllerWidget

    @classmethod
    def plugin_info(cls) -> PluginInfo:
        return PluginInfo(
            name="llm_minesweeper_controller",
            version="1.0.0",
            description="使用 LLM 分析并控制扫雷游戏",
            window_mode=WindowMode.TAB,
            icon=make_plugin_icon("#4CAF50", "L"),
            other_info=LlmMinesweeperControllerConfig,
            required_controls=[NewGameCommand, MouseClickCommand],
        )

    @property
    def other_info(self) -> LlmMinesweeperControllerConfig:
        return super().other_info  # type: ignore

    def _setup_subscriptions(self) -> None:
        self.subscribe(BoardUpdateEvent, self._on_board_update)
        self.subscribe(GameStatusChangeEvent, self._on_game_status_change)

    def _create_widget(self) -> QWidget | None:
        self._widget = LlmMinesweeperControllerWidget()
        return self._widget

    def on_initialized(self) -> None:
        self.logger.info("LlmMinesweeperControllerPlugin 已初始化")

        # 检查控制权限状态
        self._log_control_auth_status()

        # 初始化组件
        self._init_llm_client()
        self._init_function_registry()

        # 设置 UI 回调
        self._widget.set_test_button_callback(self._test_connection)
        self._widget.set_analyze_callback(self._start_analysis)

        # 监听配置变化
        self.config_changed.connect(self._on_config_changed)

        # 当前棋盘状态
        self._current_board: Optional[Dict[str, Any]] = None

        # 当前游戏状态 (1=ready, 2=playing, 3=win, 4=fail, ...)
        self._game_status: int = 1

        # 当前工作线程
        self._worker: Optional[LLMWorker] = None

    def _log_control_auth_status(self) -> None:
        """检查控制权限"""
        has_new_game = self.has_control_auth(NewGameCommand)
        has_click = self.has_control_auth(MouseClickCommand)
        self.logger.info(f"NewGameCommand 权限: {has_new_game}")
        self.logger.info(f"MouseClickCommand 权限: {has_click}")
        self._widget.log_message(
            f"权限: NewGame={has_new_game}, MouseClick={has_click}")

    def _init_llm_client(self) -> None:
        """初始化 LLM 客户端"""
        api_key = self.other_info.api_key
        base_url = self.other_info.api_base_url
        model = self.other_info.model_name
        timeout = self.other_info.request_timeout

        if api_key:
            self.llm_client = LLMClient(
                api_key=api_key,
                base_url=base_url,
                model=model,
                timeout=timeout,
            )
            self.logger.info("LLM 客户端已初始化")
            self._widget.log_message(f"LLM 客户端已初始化 (model: {model})")
        else:
            self.llm_client = None
            self.logger.warning("未配置 API 密钥")
            self._widget.log_message("未配置 API 密钥，LLM 功能不可用")

    def _init_function_registry(self) -> None:
        """初始化 Function 注册表"""
        self.function_registry = FunctionRegistry()
        self._register_minesweeper_functions()

    def _register_minesweeper_functions(self) -> None:
        """注册扫雷相关的函数"""
        registry = self.function_registry

        @registry.register(
            description="点击指定位置的格子",
            param_descriptions={
                "col": "列索引 (从 0 开始，即 X 坐标)",
                "row": "行索引 (从 0 开始，即 Y 坐标)",
                "button": "鼠标按钮: 'left' 左键揭开, 'right' 右键标旗, 'middle' 中键快速揭开周围格子",
            }
        )
        def click_cell(col: int, row: int, button: str = "left") -> Dict[str, Any]:
            return self._execute_click_cell(col, row, button)

        @registry.register(
            description="开始新游戏，不传难度参数则使用默认难度",
            param_descriptions={
                "difficulty": "游戏难度（可选）: 'easy' 初级(8x8), 'medium' 中级(16x16), 'hard' 高级(16x30)",
            }
        )
        def start_new_game(difficulty: str = None) -> Dict[str, Any]:
            return self._execute_start_new_game(difficulty)

        @registry.register(
            description="获取当前棋盘状态",
        )
        def get_board_state() -> Dict[str, Any]:
            return self._get_current_board_state()

        @registry.register(
            description="获取局部棋盘区域，返回以(col,row)为中心的局部格子，radius自己决定（建议3-5）",
            param_descriptions={
                "col": "中心列索引 (从 0 开始)",
                "row": "中心行索引 (从 0 开始)",
                "radius": "半径，自己决定大小，默认3，返回(2*radius+1)x(2*radius+1)的区域",
            }
        )
        def get_local_board(col: int, row: int, radius: int = 3) -> Dict[str, Any]:
            return self._get_local_board(col, row, radius)

    def on_control_auth_changed(self, cmd_type, granted: bool) -> None:
        """控制权限变更回调"""
        if cmd_type == NewGameCommand:
            self._widget.log_message(
                f"NewGameCommand 权限: {'已授权' if granted else '未授权'}")
        elif cmd_type == MouseClickCommand:
            self._widget.log_message(
                f"MouseClickCommand 权限: {'已授权' if granted else '未授权'}")

    def _on_config_changed(self, name: str, value) -> None:
        """配置变化回调"""
        self.logger.info(f"配置变化: {name} = {value}")
        self._widget.log_message(f"配置更新: {name}")

        # API 相关配置变化时重新初始化客户端
        if name in ["api_key", "api_base_url", "model_name", "request_timeout"]:
            self._init_llm_client()

    def _on_board_update(self, event: BoardUpdateEvent) -> None:
        """处理棋盘更新事件"""
        self._widget.log_message("收到棋盘更新事件")

        # 更新当前棋盘状态
        self._current_board = self._extract_board_data(event)

    def _on_game_status_change(self, event: GameStatusChangeEvent) -> None:
        """处理游戏状态变化事件

        状态值：
        - 1: ready (准备)
        - 2: playing (游戏中)
        - 3: win (胜利)
        - 4: fail (失败)
        - 5: show (显示概率)
        - 6: study (研究模式)
        - 7/8: display 相关
        """
        status_names = {
            1: "准备",
            2: "游戏中",
            3: "胜利",
            4: "失败",
            5: "显示概率",
            6: "研究模式",
            7: "播放录像",
            8: "播放概率",
        }

        last_name = status_names.get(
            event.last_status, f"未知({event.last_status})")
        current_name = status_names.get(
            event.current_status, f"未知({event.current_status})")

        self._widget.log_message(f"游戏状态变化: {last_name} -> {current_name}")

        # 记录当前游戏状态
        self._game_status = event.current_status

        # 如果游戏结束（胜利或失败），更新状态显示
        if event.current_status == 3:
            self._widget.update_status("游戏胜利!")
        elif event.current_status == 4:
            self._widget.update_status("游戏失败!")
        elif event.current_status == 1:
            self._widget.update_status("游戏准备中...")

    # ═══════════════════════════════════════════════════════════════
    # LLM 对话流程
    # ═══════════════════════════════════════════════════════════════

    def _test_connection(self) -> None:
        """测试 API 连接"""
        if not self.llm_client:
            self._widget.log_message("请先配置 API 密钥")
            return

        self._widget.log_message("正在测试连接...")
        self._widget.set_buttons_enabled(False)

        response = self.llm_client.test_connection()

        if response.success:
            self._widget.update_status("连接成功")
            self._widget.log_message(f"连接成功! 模型: {self.other_info.model_name}")
        else:
            self._widget.update_status("连接失败")
            self._widget.log_message(f"连接失败: {response.error}")

        self._widget.set_buttons_enabled(True)

    def _auto_continue_analysis(self) -> None:
        """自动继续分析（异常中断后）"""
        if self._game_status != 2:  # 不是进行中
            self._widget.log_message("游戏已结束，不再继续分析")
            return

        if self._worker and self._worker.isRunning():
            return

        self._widget.log_message("自动继续分析...")
        self._start_analysis()

    def _start_analysis(self) -> None:
        """开始 LLM 分析"""
        if not self.llm_client:
            self._widget.log_message("请先配置 API 密钥")
            return

        if self._worker and self._worker.isRunning():
            self._widget.log_message("已有分析任务在运行")
            return

        # 构建初始消息
        messages = self._build_initial_messages()

        # 创建并启动工作线程
        self._worker = LLMWorker(
            client=self.llm_client,
            registry=self.function_registry,
            messages=messages,
        )

        # 连接信号
        self._worker.log_signal.connect(self._widget.log_message)
        self._worker.chat_signal.connect(self._widget.add_chat_message)
        self._worker.finished_signal.connect(self._on_analysis_finished)

        self._widget.set_buttons_enabled(False)
        self._worker.start()

    def _on_analysis_finished(self, success: bool, message: str) -> None:
        """分析完成回调"""
        if self._widget is None:
            return
        self._widget.set_buttons_enabled(True)

        if success:
            self._widget.update_status("分析完成")
        else:
            self._widget.update_status("分析中断")
        self._widget.log_message(message)

        # 无论成功还是失败，如果游戏状态是进行中，自动继续分析
        # 防止AI没有进行任何函数调用就结束
        if self._game_status == 2:  # playing
            self._widget.log_message("游戏进行中，1秒后继续分析...")
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(1000, self._auto_continue_analysis)

    def _build_initial_messages(self) -> List[Dict[str, Any]]:
        """构建初始消息列表"""
        messages = []

        # 系统提示词
        system_prompt = self.other_info.system_prompt
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # 当前棋盘状态
        board_state = self._get_current_board_state()
        game_status = board_state.get('game_status', 'unknown')

        board_info = f"""当前棋盘状态:
- 行数: {board_state.get('rows', 0)}
- 列数: {board_state.get('cols', 0)}
- 剩余地雷: {board_state.get('mines_remaining', 0)}
- 游戏时间: {board_state.get('game_time', 0):.1f}秒
- 游戏状态: {game_status}
- 棋盘数据 (cells[row][col], -1=未揭开, 0-8=周围地雷数, F=标旗, M=踩到的地雷):
{json.dumps(board_state.get('cells', []), ensure_ascii=False)}

请分析当前局面并选择最佳操作。"""

        messages.append({"role": "user", "content": board_info})

        return messages

    # ═══════════════════════════════════════════════════════════════
    # 可调用的函数实现
    # ═══════════════════════════════════════════════════════════════

    def _execute_click_cell(self, col: int, row: int, button: str = "left") -> Dict[str, Any]:
        """执行点击格子操作

        Args:
            col: 列索引 (x 坐标, 从 0 开始)
            row: 行索引 (y 坐标, 从 0 开始)
            button: 鼠标按钮 ("left" 或 "right")
        """
        if not self.has_control_auth(MouseClickCommand):
            return {"success": False, "error": "无权限执行鼠标点击命令"}

        try:
            # button 转换: "left" -> 0, "right" -> 2
            button_map = {"left": 0, "right": 2, "middle": 1}
            button_value = button_map.get(button.lower(), 0)

            # 构建并发送鼠标点击命令
            click_cmd = MouseClickCommand(
                row=row,
                col=col,
                button=button_value,
            )
            self.send_command(click_cmd)

            self._widget.log_message(f"已点击格子: 行{row}, 列{col}, 按钮: {button}")
            return {
                "success": True,
                "message": f"格子点击已执行: 行{row}, 列{col}, {button}",
                "coordinates": {"row": row, "col": col},
                "button": button,
            }

        except Exception as e:
            error_msg = f"执行格子点击失败: {str(e)}"
            self.logger.error(error_msg)
            return {"success": False, "error": error_msg}

    def _execute_start_new_game(self, difficulty: str = None) -> Dict[str, Any]:
        """执行开始新游戏操作

        Args:
            difficulty: 游戏难度 ("easy", "medium", "hard")，默认使用配置中的 default_difficulty
        """
        if not self.has_control_auth(NewGameCommand):
            return {"success": False, "error": "无权限执行新游戏命令"}

        try:
            # 使用配置中的默认难度
            if difficulty is None:
                difficulty = self.other_info.default_difficulty

            # 难度映射: level 值
            # BEGINNER = 3, INTERMEDIATE = 4, EXPERT = 5
            difficulty_map = {
                "easy": 3,    # 初级
                "medium": 4,  # 中级
                "hard": 5,    # 高级
            }

            level = difficulty_map.get(difficulty, 4)

            # 清空当前棋盘状态
            self._current_board = None

            # 发送新游戏命令（使用 level 字段）
            new_game_cmd = NewGameCommand(level=level)
            self.send_command(new_game_cmd)

            # 获取对应的行列地雷数用于日志
            board_params = {
                "easy": (8, 8, 10),
                "medium": (16, 16, 40),
                "hard": (16, 30, 99),
            }
            rows, cols, mines = board_params.get(difficulty, (16, 16, 40))

            self._widget.log_message(
                f"已开始新游戏，难度: {difficulty} ({rows}x{cols}, {mines}雷)")
            return {
                "success": True,
                "message": f"新游戏已开始，难度: {difficulty}",
                "difficulty": difficulty,
                "level": level,
                "rows": rows,
                "cols": cols,
                "mines": mines,
            }

        except Exception as e:
            error_msg = f"开始新游戏失败: {str(e)}"
            self.logger.error(error_msg)
            return {"success": False, "error": error_msg}

    def _get_game_status_text(self) -> str:
        """获取游戏状态的文字描述"""
        status_map = {
            1: "ready",       # 准备
            2: "playing",     # 游戏中
            3: "win",         # 胜利
            4: "fail",        # 失败
            5: "show",        # 显示概率
            6: "study",       # 研究模式
            7: "display",     # 播放录像
            8: "showdisplay",  # 播放概率
        }
        return status_map.get(self._game_status, "unknown")

    def _get_current_board_state(self) -> Dict[str, Any]:
        """获取当前棋盘状态"""
        if self._current_board:
            result = self._current_board.copy()
            result["game_status"] = self._get_game_status_text()
            return result
        return {
            "rows": 0,
            "cols": 0,
            "cells": [],
            "mines_remaining": 0,
            "game_time": 0.0,
            "game_status": self._get_game_status_text(),
        }

    def _get_local_board(self, col: int, row: int, radius: int = 2) -> Dict[str, Any]:
        """获取局部棋盘区域

        Args:
            col: 中心列索引
            row: 中心行索引
            radius: 半径，默认2（返回5x5区域）

        Returns:
            局部棋盘数据，包含：
            - cells: 局部格子数据
            - center: 中心坐标（相对局部区域）
            - offset: 局部区域在全图的起始偏移
            - size: 局部区域大小
            - full_board_size: 全图大小
        """
        if not self._current_board or not self._current_board.get("cells"):
            return {
                "cells": [],
                "center": {"col": 0, "row": 0},
                "offset": {"col": 0, "row": 0},
                "size": {"rows": 0, "cols": 0},
                "full_board_size": {"rows": 0, "cols": 0},
                "error": "棋盘数据不可用",
            }

        full_cells = self._current_board.get("cells", [])
        full_rows = len(full_cells)
        full_cols = len(full_cells[0]) if full_cells else 0

        if full_rows == 0 or full_cols == 0:
            return {
                "cells": [],
                "center": {"col": 0, "row": 0},
                "offset": {"col": 0, "row": 0},
                "size": {"rows": 0, "cols": 0},
                "full_board_size": {"rows": 0, "cols": 0},
                "error": "棋盘为空",
            }

        # 计算局部区域边界
        start_row = max(0, row - radius)
        end_row = min(full_rows, row + radius + 1)
        start_col = max(0, col - radius)
        end_col = min(full_cols, col + radius + 1)

        # 提取局部格子
        local_cells = []
        for r in range(start_row, end_row):
            local_row = []
            for c in range(start_col, end_col):
                local_row.append(full_cells[r][c])
            local_cells.append(local_row)

        # 计算中心在局部区域中的位置
        center_col = col - start_col
        center_row = row - start_row

        return {
            "cells": local_cells,
            "center": {"col": center_col, "row": center_row},
            "offset": {"col": start_col, "row": start_row},
            "size": {"rows": len(local_cells), "cols": len(local_cells[0]) if local_cells else 0},
            "full_board_size": {"rows": full_rows, "cols": full_cols},
        }

    def _extract_board_data(self, event: BoardUpdateEvent) -> Dict[str, Any]:
        """从事件中提取棋盘数据

        game_board 值含义：
        - 0-8: 已揭开的数字格子
        - 10: 未揭开的格子
        - 11: 标旗的格子
        - 15: 踩到的地雷（红雷），游戏失败
        - 16: 未踩到的地雷（白雷）
        """
        game_board = event.game_board or []

        # 转换为 LLM 友好格式：-1=未揭开, 0-8=数字, F=标旗, M=地雷(踩到), m=地雷(未踩到)
        cells = []
        for row in game_board:
            row_data = []
            for cell in row:
                if cell == 10:  # 未揭开
                    row_data.append(-1)
                elif cell == 11:  # 标旗
                    row_data.append("F")
                elif cell == 15:  # 踩到的地雷（红雷），游戏失败
                    row_data.append("M")
                elif cell == 16:  # 未踩到的地雷（白雷）
                    row_data.append("m")
                else:  # 0-8 数字
                    row_data.append(cell)
            cells.append(row_data)

        return {
            "rows": event.rows,
            "cols": event.cols,
            "cells": cells,
            "mines_remaining": event.mines_remaining,
            "game_time": event.game_time,
        }

    def on_shutdown(self) -> None:
        """插件关闭时停止 Worker"""
        if self._worker and self._worker.isRunning():
            self.logger.info("正在停止 LLM Worker...")
            self._worker.stop()
            self._worker.wait(1)  # 等待最多3秒
        self._worker = None

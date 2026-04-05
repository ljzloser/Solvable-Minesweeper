"""
ZMQ Server 集成模块

提供将 ZMQ Server 集成到扫雷主进程的便捷方法
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from PyQt5.QtCore import QObject, pyqtSignal
from lib_zmq_plugins.server.zmq_server import ZMQServer
from lib_zmq_plugins.shared.base import CommandResponse

from shared_types import EVENT_TYPES, COMMAND_TYPES
from shared_types import (
    GameStartedEvent,
    GameEndedEvent,
    BoardUpdateEvent,
    NewGameCommand,
)

if TYPE_CHECKING:
    from lib_zmq_plugins.log import LogHandler

import loguru
logger = loguru.logger.bind(name="ServerBridge")


class GameServerSignals(QObject):
    """用于跨线程通信的信号"""
    new_game_requested = pyqtSignal(int, int, int)  # rows, cols, mines


class GameServerBridge:
    """游戏服务端桥接器"""
    
    def __init__(
        self,
        game_ui: Any,
        endpoint: str | None = None,
        log_handler: LogHandler | None = None,
    ):
        self._game_ui = game_ui
        self._log = log_handler
        
        # 信号对象，用于跨线程调用
        self._signals = GameServerSignals()
        
        # 默认端点
        if endpoint is None:
            endpoint = "tcp://127.0.0.1:5555"
        
        self._endpoint = endpoint
        self._server = ZMQServer(endpoint=endpoint, log_handler=log_handler)
        
        # 注册类型
        self._server.register_event_types(*EVENT_TYPES)
        self._server.register_command_types(*COMMAND_TYPES)
        
        # 注册指令处理器
        self._server.register_handler(NewGameCommand, self._handle_new_game)
    
    @property
    def endpoint(self) -> str:
        return self._endpoint
    
    @property
    def signals(self) -> GameServerSignals:
        """获取信号对象，用于连接到主线程的槽函数"""
        return self._signals
    
    def start(self) -> None:
        """启动服务"""
        self._server.start()
        logger.info(f"Game server bridge started at {self._endpoint}")
    
    def stop(self) -> None:
        """停止服务"""
        self._server.stop()
        logger.info("Game server bridge stopped")
    
    # ═══════════════════════════════════════════════════════════════════
    # 事件发布
    # ═══════════════════════════════════════════════════════════════════
    
    def publish_game_started(self, rows: int, cols: int, mines: int) -> None:
        """发布游戏开始事件"""
        event = GameStartedEvent(rows=rows, cols=cols, mines=mines)
        self._server.publish(GameStartedEvent, event)
    
    def publish_game_ended(self, is_win: bool, time: float) -> None:
        """发布游戏结束事件"""
        event = GameEndedEvent(is_win=is_win, time=time)
        self._server.publish(GameEndedEvent, event)
    
    def publish_board_update(self, board: list[list[int]]) -> None:
        """发布局面刷新事件"""
        event = BoardUpdateEvent(board=board)
        self._server.publish(BoardUpdateEvent, event)
    
    # ═══════════════════════════════════════════════════════════════════
    # 指令处理
    # ═══════════════════════════════════════════════════════════════════
    
    def _handle_new_game(self, cmd: NewGameCommand) -> CommandResponse:
        """处理新游戏指令（在 ZMQ 后台线程中运行）"""
        try:
            # 通过信号发送到主线程执行
            self._signals.new_game_requested.emit(cmd.rows, cmd.cols, cmd.mines)
            return CommandResponse(request_id=cmd.request_id, success=True)
        except Exception as e:
            logger.error(f"New game error: {e}", exc_info=True)
            return CommandResponse(request_id=cmd.request_id, success=False, error=str(e))

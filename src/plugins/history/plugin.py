"""
历史记录插件主体
"""

from __future__ import annotations

import base64
import sqlite3
from pathlib import Path
from typing import Any

import msgspec
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QWidget

from plugin_sdk import (
    BasePlugin, PluginInfo, make_plugin_icon, WindowMode,
    OtherInfoBase, IntConfig,
)
from shared_types.events import VideoSaveEvent
from plugins.services.history import HistoryService, GameRecord

from .widgets import HistoryMainWidget


class HistoryConfig(OtherInfoBase):
    """历史记录插件配置"""
    
    float_decimals = IntConfig(
        default=2,
        label="小数位数",
        description="查询窗口中浮点数显示的小数位数",
        min_value=0,
        max_value=10,
    )


class HistoryPlugin(BasePlugin):
    """
    历史记录插件

    - 后台：监听 VideoSaveEvent，写入 SQLite
    - 界面：提供筛选、分页、播放/导出功能
    - 服务：提供 HistoryService 接口供其他插件查询历史记录
    """
    video_save_over = pyqtSignal()

    @classmethod
    def plugin_info(cls) -> PluginInfo:
        return PluginInfo(
            name="history",
            description="游戏历史记录（SQLite 持久化）",
            author="ljzloser",
            version="1.0.0",
            icon=make_plugin_icon("#7b1fa2", "\N{SCROLL}"),
            window_mode=WindowMode.TAB,
            other_info=HistoryConfig,
        )

    def __init__(self, info):
        super().__init__(info)

    def _setup_subscriptions(self) -> None:
        self.subscribe(VideoSaveEvent, self._on_video_save)

    def _create_widget(self) -> QWidget:
        db_path = self.data_dir / "history.db"
        config_path = self.data_dir / "history_show_fields.json"
        
        # 获取配置中的小数位数
        float_decimals = 2
        if self.other_info:
            float_decimals = self.other_info.float_decimals
        
        self._widget = HistoryMainWidget(db_path, config_path, float_decimals)
        self.video_save_over.connect(self._widget.query_button.click)
        return self._widget

    def on_initialized(self) -> None:
        self._init_db()
        self.register_service(self, protocol=HistoryService)
        self.logger.info("历史记录插件已初始化，HistoryService 已注册")

    # ── 数据库 ──────────────────────────────────────────────

    def _init_db(self) -> None:
        db_path = self.data_dir / "history.db"
        if db_path.exists():
            return
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE history (
                replay_id         INTEGER PRIMARY KEY AUTOINCREMENT,
                game_board_state  INTEGER,
                rtime            REAL,
                left             INTEGER,
                right            INTEGER,
                double           INTEGER,
                left_s           REAL,
                right_s          REAL,
                double_s         REAL,
                level            INTEGER,
                cl               INTEGER,
                cl_s             REAL,
                ce               REAL,
                ce_s             REAL,
                rce              INTEGER,
                lce              INTEGER,
                dce              INTEGER,
                bbbv             INTEGER,
                bbbv_solved      INTEGER,
                bbbv_s           REAL,
                flag             INTEGER,
                path             REAL,
                etime            INTEGER,
                start_time       INTEGER,
                end_time         INTEGER,
                mode             INTEGER,
                software         TEXT,
                player_identifier   TEXT,
                race_identifier     TEXT,
                uniqueness_identifier TEXT,
                stnb             REAL,
                corr             REAL,
                thrp             REAL,
                ioe              REAL,
                is_official      INTEGER,
                is_fair          INTEGER,
                op               INTEGER,
                isl              INTEGER,
                pluck            REAL,
                raw_data         BLOB
            )
        """
        )
        conn.commit()
        conn.close()
        self.logger.info(f"Database created: {db_path}")

    # ── 事件处理 ──────────────────────────────────────────

    def _on_video_save(self, event: VideoSaveEvent) -> None:
        data: dict[str, Any] = msgspec.structs.asdict(event)
        raw_b64 = data.get("raw_data", "")
        try:
            data["raw_data"] = base64.b64decode(raw_b64) if raw_b64 else None
        except Exception as e:
            self.logger.warning(f"base64 decode failed: {e}")
            data["raw_data"] = None
        del data["timestamp"]
        columns = ", ".join(data.keys())
        placeholders = ", ".join(f":{k}" for k in data.keys())

        db_path = self.data_dir / "history.db"
        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                f"INSERT INTO history ({columns}) VALUES ({placeholders})",
                data,
            )
            conn.commit()
            self.logger.info(
                f"Saved: board_state={event.game_board_state} time={event.rtime:.1f}s"
            )
        finally:
            conn.close()
        self.video_save_over.emit()

    # ═══════════════════════════════════════════════════════════════════
    # HistoryService 接口实现
    # ═══════════════════════════════════════════════════════════════════

    def query_records(
        self,
        limit: int = 100,
        offset: int = 0,
        level: int | None = None,
    ) -> list[GameRecord]:
        """查询游戏记录"""
        db_path = self.data_dir / "history.db"
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            if level is not None:
                cursor.execute(
                    """
                    SELECT * FROM history
                    WHERE level = ?
                    ORDER BY replay_id DESC
                    LIMIT ? OFFSET ?
                    """,
                    (level, limit, offset),
                )
            else:
                cursor.execute(
                    """
                    SELECT * FROM history
                    ORDER BY replay_id DESC
                    LIMIT ? OFFSET ?
                    """,
                    (limit, offset),
                )
            rows = cursor.fetchall()
            return [GameRecord(
                replay_id=row["replay_id"],
                rtime=row["rtime"],
                level=row["level"],
                bbbv=row["bbbv"],
                bbbv_solved=row["bbbv_solved"],
                left=row["left"],
                right=row["right"],
                double=row["double"],
                cl=row["cl"],
                ce=row["ce"],
                flag=row["flag"],
                game_board_state=row["game_board_state"],
                mode=row["mode"],
                software=row["software"] or "",
                start_time=row["start_time"],
                end_time=row["end_time"],
            ) for row in rows]
        finally:
            conn.close()

    def get_record_count(self, level: int | None = None) -> int:
        """获取记录总数"""
        db_path = self.data_dir / "history.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        try:
            if level is not None:
                cursor.execute(
                    "SELECT COUNT(*) FROM history WHERE level = ?", (level,)
                )
            else:
                cursor.execute("SELECT COUNT(*) FROM history")
            return cursor.fetchone()[0]
        finally:
            conn.close()

    def get_last_record(self) -> GameRecord | None:
        """获取最近一条记录"""
        records = self.query_records(limit=1)
        return records[0] if records else None

    def delete_record(self, record_id: int) -> bool:
        """删除指定记录"""
        db_path = self.data_dir / "history.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                "DELETE FROM history WHERE replay_id = ?", (record_id,)
            )
            conn.commit()
            deleted = cursor.rowcount > 0
            if deleted:
                self.logger.info(f"Deleted record: {record_id}")
            return deleted
        finally:
            conn.close()

    def _on_config_changed(self, name: str, value: Any) -> None:
        if name == "float_decimals" and hasattr(self, '_widget'):
            self._widget.set_float_decimals(value)

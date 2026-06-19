"""
历史记录插件主体
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import msgspec
from PyQt5.QtCore import QCoreApplication, pyqtSignal
from PyQt5.QtWidgets import QWidget

_translate = QCoreApplication.translate

from plugin_sdk import (
    BasePlugin, PluginInfo, make_plugin_icon, WindowMode,
    OtherInfoBase, IntConfig, TextConfig, ChoiceConfig,
)
from shared_types.events import GameFinishedEvent, LanguageChangeEvent
from plugins.services.history import HistoryService, GameRecord

from .widgets import HistoryMainWidget


class HistoryConfig(OtherInfoBase):
    """历史记录插件配置"""

    float_decimals = IntConfig(
        default=2,
        label=_translate("Form", "小数位数"),
        description=_translate("Form", "查询窗口中浮点数显示的小数位数"),
        min_value=0,
        max_value=10,
    )

    # 隐藏字段：保存排序和过滤状态
    saved_filter = TextConfig(
        default="[]",
        label="saved_filter",
        visible=False,
    )

    saved_sort = TextConfig(
        default="[]",
        label="saved_sort",
        visible=False,
    )

    saved_show_fields = TextConfig(
        default="[]",
        label="saved_show_fields",
        visible=False,
    )

    page_size = ChoiceConfig(
        default="50",
        label=_translate("Form", "每页条数"),
        choices=[
            ("10", "10"),
            ("20", "20"),
            ("50", "50"),
            ("100", "100"),
            ("200", "200"),
            ("500", "500"),
            ("1000", "1000"),
        ],
    )


class HistoryPlugin(BasePlugin[HistoryConfig]):
    """
    历史记录插件

    - 后台：监听 GameFinishedEvent，写入 SQLite
    - 界面：提供筛选、分页、播放/导出功能
    - 服务：提供 HistoryService 接口供其他插件查询历史记录
    """
    video_save_over = pyqtSignal()
    _widget: HistoryMainWidget

    @classmethod
    def plugin_info(cls) -> PluginInfo:
        return PluginInfo(
            name=_translate("Form", "历史记录"),
            description=_translate("Form", "游戏历史记录（SQLite 持久化）"),
            author="ljzloser",
            version="1.0.0",
            icon=make_plugin_icon("#7b1fa2", "\N{SCROLL}"),
            window_mode=WindowMode.TAB,  # type: ignore
            other_info=HistoryConfig,
        )

    def __init__(self, info):
        super().__init__(info)

    def _setup_subscriptions(self) -> None:
        self.subscribe(GameFinishedEvent, self._on_video_save)
        self.subscribe(LanguageChangeEvent, self._on_language_change)

    def _create_widget(self) -> QWidget:
        db_path = self.data_dir / "history.db"
        config_path = self.data_dir / "history_show_fields.json"

        # 获取配置中的小数位数和每页条数
        float_decimals = 2
        page_size = "50"
        if self.other_info:
            float_decimals = self.other_info.float_decimals
            page_size = self.other_info.page_size

        self._widget = HistoryMainWidget(
            db_path, config_path, float_decimals, page_size)

        # 连接排序和过滤状态变化信号
        self._widget.filter_sort_state_changed.connect(
            self._on_filter_sort_state_changed)

        # 连接列显示配置变化信号
        self._widget.show_fields_changed.connect(
            self._on_show_fields_changed)

        # 恢复保存的排序和过滤状态
        if self.other_info:
            self._widget.set_filter_sort_state(
                self.other_info.saved_filter,
                self.other_info.saved_sort
            )
            # 恢复保存的列显示配置
            self._widget.restore_show_fields(self.other_info.saved_show_fields)

        self.video_save_over.connect(self._widget.query_button.click)
        return self._widget

    def _on_language_change(self, event: LanguageChangeEvent) -> None:
        self.run_on_gui(self._widget.retranslateUi)

    def _on_filter_sort_state_changed(self, filter_json: str, sort_json: str) -> None:
        """保存排序和过滤状态"""
        if self.other_info:
            self.other_info.saved_filter = filter_json
            self.other_info.saved_sort = sort_json
            self.save_config()

    def _on_show_fields_changed(self, show_fields_json: str) -> None:
        """保存列显示配置"""
        if self.other_info:
            self.other_info.saved_show_fields = show_fields_json
            self.save_config()

    def on_initialized(self) -> None:
        self._init_db()
        self.register_service(self, protocol=HistoryService)
        self.logger.info("历史记录插件已初始化，HistoryService 已注册")

    # ── 数据库 ──────────────────────────────────────────────

    def _init_db(self) -> None:
        db_path = self.data_dir / "history.db"
        if db_path.exists():
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(history)")
            cols = {row[1] for row in cursor.fetchall()}
            if "game_state" in cols:
                conn.close()
                return
            self.logger.info("旧 schema，迁移中…")
            cursor.executescript("DROP TABLE IF EXISTS history;")
            conn.commit()
            conn.close()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE history (
                replay_id           INTEGER PRIMARY KEY AUTOINCREMENT,
                game_state          INTEGER,
                nf                  INTEGER,
                row                 INTEGER,
                column              INTEGER,
                mine_num            INTEGER,
                rtime               REAL,
                left                INTEGER,
                right               INTEGER,
                double              INTEGER,
                level               INTEGER,
                cl                  INTEGER,
                ce                  INTEGER,
                rce                 INTEGER,
                lce                 INTEGER,
                dce                 INTEGER,
                bbbv                INTEGER,
                bbbv_solved         INTEGER,
                zini                INTEGER,
                flag                INTEGER,
                path                REAL,
                start_time          INTEGER,
                end_time            INTEGER,
                mode                INTEGER,
                software            TEXT,
                player_identifier   TEXT,
                race_identifier     TEXT,
                unique_identifier   TEXT,
                is_official         INTEGER,
                is_fair             INTEGER,
                op                  INTEGER,
                isl                 INTEGER,
                pluck               REAL,
                board               TEXT,
                raw_data            BLOB
            )
        """
        )
        conn.commit()
        conn.close()
        self.logger.info(f"Database created: {db_path}")

    # ── 事件处理 ──────────────────────────────────────────

    def _on_video_save(self, event: GameFinishedEvent) -> None:
        data: dict[str, Any] = msgspec.structs.asdict(event)
        if isinstance(data.get("board"), list):
            import json
            data["board"] = json.dumps(data["board"], separators=(",", ":"))
        data.pop("timestamp", None)
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
                f"Saved: game_state={event.game_state} time={event.rtime:.1f}s"
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
                game_state=row["game_state"],
                mode=row["mode"],
                software=row["software"] or "",
                start_time=row["start_time"],
                end_time=row["end_time"],
                nf=bool(row["nf"]),
                row=row["row"],
                column=row["column"],
                mine_num=row["mine_num"],
                zini=row["zini"],
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

    def raw_query(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        """
        直接执行 SQL 查询

        Args:
            sql: SQL 查询语句（使用 ? 作为参数占位符）
            params: 参数元组

        Returns:
            字典列表
        """
        db_path = self.data_dir / "history.db"
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def raw_query_one(self, sql: str, params: tuple = ()) -> dict[str, Any] | None:
        """
        执行 SQL 查询并返回单条结果
        """
        results = self.raw_query(sql, params)
        return results[0] if results else None

    def _on_config_changed(self, name: str, value: Any) -> None:
        if name == "float_decimals":
            self._widget.set_float_decimals(value)

"""
QML ↔ Python 数据桥

将 HistoryService 的查询结果暴露给 QML，
通过 QQuickWidget.rootContext().setContextProperty() 注入。
"""

from __future__ import annotations

import json
from typing import Any

from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal, QThread

from shared_types.enums import GameBoardState, GameLevel, GameMode
from plugins.services.history import HistoryService

from .queries import (
    SQL_SUMMARY, SQL_SUMMARY_PARAMS,
    SQL_SUMMARY_BY_LEVEL, SQL_SUMMARY_BY_LEVEL_PARAMS,
    SQL_SUMMARY_FOR_LEVEL, SQL_SUMMARY_FOR_LEVEL_PARAMS,
    SQL_TREND, SQL_TREND_BY_LEVEL,
    SQL_TIME_DISTRIBUTION, SQL_TIME_DISTRIBUTION_BY_LEVEL,
    SQL_LEVEL_DISTRIBUTION,
    SQL_WINRATE_MONTHLY,
    LEVEL_NAMES, MODE_NAMES,
)


class StatsBridge(QObject):
    """
    暴露给 QML 的数据桥

    QML 通过 bridge.xxx() 调用 Python 方法获取数据。
    所有方法返回 JSON 字符串，QML 端用 JSON.parse() 解析。
    """

    dataChanged = pyqtSignal()  # 数据变化时通知 QML 刷新

    def __init__(self, parent=None):
        super().__init__(parent)
        self._history: HistoryService | None = None

    def set_history_service(self, service: HistoryService) -> None:
        self._history = service
        self.dataChanged.emit()

    def _query(self, sql: str, params: tuple = ()) -> str:
        """执行 raw_query 并返回 JSON 字符串"""
        if self._history is None:
            return "[]"
        try:
            rows = self._history.raw_query(sql, params)
            return json.dumps(rows, ensure_ascii=False, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)})

    def _query_one(self, sql: str, params: tuple = ()) -> str:
        """执行 raw_query_one 并返回 JSON 字符串"""
        if self._history is None:
            return "null"
        try:
            row = self._history.raw_query_one(sql, params)
            return json.dumps(row, ensure_ascii=False, default=str) if row else "null"
        except Exception as e:
            return json.dumps({"error": str(e)})

    # ── QML 可调用的槽方法 ────────────────────────────────

    @pyqtSlot(result=str)
    def getSummary(self) -> str:
        """获取总体汇总统计"""
        return self._query_one(SQL_SUMMARY, SQL_SUMMARY_PARAMS)

    @pyqtSlot(int, result=str)
    def getSummaryByLevel(self, level: int) -> str:
        """获取指定难度的汇总统计"""
        return self._query_one(SQL_SUMMARY_FOR_LEVEL, SQL_SUMMARY_FOR_LEVEL_PARAMS + (level,))

    @pyqtSlot(result=str)
    def getLevelSummary(self) -> str:
        """获取按难度分组的汇总"""
        return self._query(SQL_SUMMARY_BY_LEVEL, SQL_SUMMARY_BY_LEVEL_PARAMS)

    @pyqtSlot(int, result=str)
    def getTrend(self, limit: int = 200) -> str:
        """获取最近 N 局趋势数据"""
        return self._query(SQL_TREND, (limit,))

    @pyqtSlot(int, int, result=str)
    def getTrendByLevel(self, level: int, limit: int = 200) -> str:
        """获取指定难度最近 N 局趋势"""
        return self._query(SQL_TREND_BY_LEVEL, (level, limit))

    @pyqtSlot(result=str)
    def getTimeDistribution(self) -> str:
        """获取完成时间分布"""
        return self._query(SQL_TIME_DISTRIBUTION, (GameBoardState.Win.value,))

    @pyqtSlot(int, result=str)
    def getTimeDistributionByLevel(self, level: int) -> str:
        """获取指定难度完成时间分布"""
        return self._query(SQL_TIME_DISTRIBUTION_BY_LEVEL, (GameBoardState.Win.value, level))

    @pyqtSlot(result=str)
    def getLevelDistribution(self) -> str:
        """获取难度分布（饼图）"""
        return self._query(SQL_LEVEL_DISTRIBUTION)

    @pyqtSlot(result=str)
    def getWinrateMonthly(self) -> str:
        """获取月度胜率趋势"""
        return self._query(SQL_WINRATE_MONTHLY, (GameBoardState.Win.value,))

    @pyqtSlot(result=str)
    def getLevelNames(self) -> str:
        """获取难度名称映射"""
        return json.dumps(LEVEL_NAMES, ensure_ascii=False)

    @pyqtSlot(result=str)
    def getModeNames(self) -> str:
        """获取模式名称映射"""
        return json.dumps(MODE_NAMES, ensure_ascii=False)

    @pyqtSlot(result=str)
    def getEnumValues(self) -> str:
        """获取 QML 需要的枚举值，避免硬编码魔数"""
        return json.dumps({
            "gameState": {
                "win": GameBoardState.Win.value,
                "fail": GameBoardState.Fail.value,
                "jowin": GameBoardState.Jowin.value,
                "jofail": GameBoardState.Jofail.value,
            },
            "level": {
                "beginner": GameLevel.BEGINNER.value,
                "intermediate": GameLevel.INTERMEDIATE.value,
                "expert": GameLevel.EXPERT.value,
                "custom": GameLevel.CUSTOM.value,
            },
        }, ensure_ascii=False)

    @pyqtSlot()
    def refresh(self) -> None:
        """通知 QML 刷新数据"""
        self.dataChanged.emit()

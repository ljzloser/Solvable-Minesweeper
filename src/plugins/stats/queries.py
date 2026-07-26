"""
统计插件 SQL 查询封装

所有查询通过 HistoryService.raw_query / raw_query_one 执行，
不直接访问数据库，保持插件间解耦。

枚举值直接使用 shared_types.enums 中的 GameBoardState / GameLevel / GameMode。
"""

from __future__ import annotations

from shared_types.enums import GameBoardState, GameLevel, GameMode


# ── 汇总统计 ──────────────────────────────────────────────

SQL_SUMMARY = """
SELECT
    COUNT(*) AS total,
    SUM(CASE WHEN game_state = ? THEN 1 ELSE 0 END) AS wins,
    SUM(CASE WHEN game_state = ? THEN 1 ELSE 0 END) AS losses,
    SUM(CASE WHEN game_state IN (?, ?) THEN 1 ELSE 0 END) AS total_wins,
    ROUND(AVG(CASE WHEN game_state = ? THEN rtime END), 3) AS avg_win_time,
    ROUND(MIN(CASE WHEN game_state = ? THEN rtime END), 3) AS best_time,
    ROUND(AVG(CASE WHEN game_state = ? AND bbbv > 0
        THEN CAST(bbbv_solved AS FLOAT) / bbbv END), 4) AS avg_bbbv_pct,
    ROUND(AVG(CASE WHEN game_state = ? AND rtime > 0
        THEN CAST(bbbv AS FLOAT) / rtime END), 2) AS avg_3bvs
FROM history
"""

SQL_SUMMARY_PARAMS = (
    GameBoardState.Win.value, GameBoardState.Fail.value,
    GameBoardState.Win.value, GameBoardState.Jowin.value,
    GameBoardState.Win.value, GameBoardState.Win.value,
    GameBoardState.Win.value, GameBoardState.Win.value,
)

SQL_SUMMARY_BY_LEVEL = """
SELECT
    level,
    COUNT(*) AS total,
    SUM(CASE WHEN game_state = ? THEN 1 ELSE 0 END) AS wins,
    SUM(CASE WHEN game_state = ? THEN 1 ELSE 0 END) AS losses,
    ROUND(AVG(CASE WHEN game_state = ? THEN rtime END), 3) AS avg_win_time,
    ROUND(MIN(CASE WHEN game_state = ? THEN rtime END), 3) AS best_time,
    ROUND(AVG(CASE WHEN game_state = ? AND bbbv > 0
        THEN CAST(bbbv_solved AS FLOAT) / bbbv END), 4) AS avg_bbbv_pct,
    ROUND(AVG(CASE WHEN game_state = ? AND rtime > 0
        THEN CAST(bbbv AS FLOAT) / rtime END), 2) AS avg_3bvs
FROM history
GROUP BY level
ORDER BY level
"""

SQL_SUMMARY_BY_LEVEL_PARAMS = (
    GameBoardState.Win.value, GameBoardState.Fail.value,
    GameBoardState.Win.value, GameBoardState.Win.value,
    GameBoardState.Win.value, GameBoardState.Win.value,
)

SQL_SUMMARY_FOR_LEVEL = """
SELECT
    COUNT(*) AS total,
    SUM(CASE WHEN game_state = ? THEN 1 ELSE 0 END) AS wins,
    SUM(CASE WHEN game_state = ? THEN 1 ELSE 0 END) AS losses,
    ROUND(AVG(CASE WHEN game_state = ? THEN rtime END), 3) AS avg_win_time,
    ROUND(MIN(CASE WHEN game_state = ? THEN rtime END), 3) AS best_time,
    ROUND(AVG(CASE WHEN game_state = ? AND bbbv > 0
        THEN CAST(bbbv_solved AS FLOAT) / bbbv END), 4) AS avg_bbbv_pct,
    ROUND(AVG(CASE WHEN game_state = ? AND rtime > 0
        THEN CAST(bbbv AS FLOAT) / rtime END), 2) AS avg_3bvs
FROM history
WHERE level = ?
"""

SQL_SUMMARY_FOR_LEVEL_PARAMS = (
    GameBoardState.Win.value, GameBoardState.Fail.value,
    GameBoardState.Win.value, GameBoardState.Win.value,
    GameBoardState.Win.value, GameBoardState.Win.value,
)


# ── 趋势数据 ──────────────────────────────────────────────

SQL_TREND = """
SELECT
    start_time,
    rtime,
    bbbv,
    bbbv_solved,
    game_state,
    level,
    mode,
    nf,
    CASE WHEN bbbv > 0 AND rtime > 0
        THEN ROUND(CAST(bbbv AS FLOAT) / rtime, 2)
        ELSE 0 END AS bbbv_s
FROM history
ORDER BY start_time DESC
LIMIT ?
"""

SQL_TREND_BY_LEVEL = """
SELECT
    start_time,
    rtime,
    bbbv,
    bbbv_solved,
    game_state,
    level,
    mode,
    nf,
    CASE WHEN bbbv > 0 AND rtime > 0
        THEN ROUND(CAST(bbbv AS FLOAT) / rtime, 2)
        ELSE 0 END AS bbbv_s
FROM history
WHERE level = ?
ORDER BY start_time DESC
LIMIT ?
"""


# ── 分布数据 ──────────────────────────────────────────────

SQL_TIME_DISTRIBUTION = """
SELECT
    ROUND(rtime, 0) AS time_bucket,
    COUNT(*) AS count
FROM history
WHERE game_state = ? AND rtime > 0
GROUP BY ROUND(rtime, 0)
ORDER BY time_bucket
"""

SQL_TIME_DISTRIBUTION_BY_LEVEL = """
SELECT
    ROUND(rtime, 0) AS time_bucket,
    COUNT(*) AS count
FROM history
WHERE game_state = ? AND rtime > 0 AND level = ?
GROUP BY ROUND(rtime, 0)
ORDER BY time_bucket
"""


# ── 难度分布 ──────────────────────────────────────────────

SQL_LEVEL_DISTRIBUTION = """
SELECT
    level,
    COUNT(*) AS count
FROM history
GROUP BY level
ORDER BY level
"""


# ── 胜率趋势（按月）──────────────────────────────────────

SQL_WINRATE_MONTHLY = """
SELECT
    CAST(start_time / 1000000 AS INTEGER) AS ts_sec,
    COUNT(*) AS total,
    SUM(CASE WHEN game_state = ? THEN 1 ELSE 0 END) AS wins
FROM history
GROUP BY CAST(strftime('%Y-%m', datetime(start_time / 1000000, 'unixepoch', 'localtime')) AS TEXT)
ORDER BY ts_sec
"""


# ── 辅助函数 ──────────────────────────────────────────────

LEVEL_NAMES = {m.value: m.display_name for m in GameLevel}
MODE_NAMES = {m.value: m.display_name for m in GameMode}


def level_name(level: int) -> str:
    return LEVEL_NAMES.get(level, f"Level {level}")


def mode_name(mode: int) -> str:
    return MODE_NAMES.get(mode, f"Mode {mode}")

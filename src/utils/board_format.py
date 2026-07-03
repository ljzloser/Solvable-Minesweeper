from typing import List, Tuple
import tempfile
import os
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QUrl, QMimeData


CELL_MINE = -1
CELL_UNOPENED = 10
CELL_FLAGGED = 11
CELL_WRONG_FLAG = 14
CELL_STEPPED_MINE = 15
CELL_UNMARKED_MINE = 16


_GAME_MODE_NAMES = {
    0: "classic",
    4: "win7",
    5: "classic_no_guess",
    6: "strong_no_guess",
    7: "weak_no_guess",
    8: "quasi_no_guess",
    9: "strong_guessable",
    10: "weak_guessable",
    1: "upk",
    2: "cheat",
    3: "density",
}


def _game_mode_str(mode: int) -> str:
    return _GAME_MODE_NAMES.get(mode, str(mode))


def board_to_array_str(real_board: List[List[int]]) -> str:
    rows = []
    for row in real_board:
        rows.append("[" + ", ".join(str(c) for c in row) + "]")
    return "[" + ",\n ".join(rows) + "]"


_EMOJI_VIEW = {
    "U": "⬜",
    "0": "0️⃣",
    "1": "1️⃣",
    "2": "2️⃣",
    "3": "3️⃣",
    "4": "4️⃣",
    "5": "5️⃣",
    "6": "6️⃣",
    "7": "7️⃣",
    "8": "8️⃣",
    "F": "🚩",
    "?": "❓",
    "X": "💥",
    "@": "💣",
    "#": "❌",
    "*": "💣",
}


def _view_char_ascii(cell: int) -> str:
    if cell == CELL_MINE:
        return "*"
    if cell == CELL_UNMARKED_MINE:
        return "@"
    if cell == CELL_UNOPENED or cell == 12:
        return "U"
    if cell == CELL_FLAGGED:
        return "F"
    if cell == CELL_WRONG_FLAG:
        return "#"
    if cell == CELL_STEPPED_MINE:
        return "X"
    return str(cell)


def _view_char_emoji(cell: int) -> str:
    ascii_ch = _view_char_ascii(cell)
    return _EMOJI_VIEW.get(ascii_ch, ascii_ch)


def board_to_board_string(
    real_board: List[List[int]],
    game_board: List[List[int]],
    rows: int,
    cols: int,
    mines: int,
    game_mode: int,
    render: str = "ascii",
) -> str:
    use_emoji = render == "emoji"

    lines = []
    lines.append("# MINESWEEPER-BOARD v0.1")
    lines.append(f"# Render: {render}")
    lines.append("")
    lines.append(f"rows: {rows}")
    lines.append(f"columns: {cols}")
    lines.append(f"mines: {mines}")
    lines.append(f"game_mode: {_game_mode_str(game_mode)}")
    lines.append("")

    if real_board:
        lines.append("[real]")
        for row in real_board:
            line = ""
            for c in row:
                if c == CELL_MINE:
                    line += _EMOJI_VIEW["*"] if use_emoji else "*"
                else:
                    ch = str(c)
                    line += _EMOJI_VIEW.get(ch, ch) if use_emoji else ch
            lines.append(line)
        lines.append("")

    if game_board:
        view_fn = _view_char_emoji if use_emoji else _view_char_ascii
        lines.append("[view]")
        for row in game_board:
            line = "".join(view_fn(c) for c in row)
            lines.append(line)
        lines.append("")

    return "\n".join(lines)


def copy_board_to_clipboard(
    real_board: List[List[int]],
    game_board: List[List[int]],
    rows: int,
    cols: int,
    mines: int,
    game_mode: int,
    copy_format: int,
    render: str = "ascii",
) -> None:
    if copy_format == 0:
        text = board_to_array_str(real_board)
        QApplication.clipboard().setText(text)

    elif copy_format == 1:
        text = board_to_board_string(
            real_board, game_board, rows, cols, mines, game_mode, render
        )
        QApplication.clipboard().setText(text)

    else:
        text = board_to_board_string(
            real_board, game_board, rows, cols, mines, game_mode, render
        )
        fd, path = tempfile.mkstemp(suffix=".board", prefix="board_")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        url = QUrl.fromLocalFile(path)
        mime = QMimeData()
        mime.setUrls([url])
        mime.setText(text)
        QApplication.clipboard().setMimeData(mime)


_EMOJI_TO_ASCII = {
    "\u2b1c": "U",
    "\ud83d\udea9": "F",
    "\u2753": "?",
    "\ud83d\udca5": "X",
    "\ud83d\udca3": "@",
    "\u274c": "#",
}
_EMOJI_DIGIT_SUFFIX = "\ufe0f\u20e3"


def _parse_view_line_ascii(line: str) -> List[int]:
    row = []
    for ch in line:
        if ch == "U":
            row.append(CELL_UNOPENED)
        elif ch == "F":
            row.append(CELL_FLAGGED)
        elif ch == "*":
            row.append(CELL_MINE)
        elif ch == "?":
            row.append(CELL_UNOPENED)
        elif ch == "X":
            row.append(CELL_STEPPED_MINE)
        elif ch == "@":
            row.append(CELL_UNMARKED_MINE)
        elif ch == "#":
            row.append(CELL_WRONG_FLAG)
        else:
            row.append(int(ch))
    return row


def _parse_view_line_emoji(line: str) -> List[int]:
    row = []
    i = 0
    while i < len(line):
        ch = line[i]
        ascii_ch = _EMOJI_TO_ASCII.get(ch)
        if ascii_ch:
            if ascii_ch == "U":
                row.append(CELL_UNOPENED)
            elif ascii_ch == "F":
                row.append(CELL_FLAGGED)
            elif ascii_ch == "?":
                row.append(CELL_UNOPENED)
            elif ascii_ch == "X":
                row.append(CELL_STEPPED_MINE)
            elif ascii_ch == "@":
                row.append(CELL_UNMARKED_MINE)
            elif ascii_ch == "#":
                row.append(CELL_WRONG_FLAG)
            i += 1
        elif ch == "*":
            row.append(CELL_MINE)
            i += 1
        elif ch.isdigit():
            if line[i + 1:i + 3] == _EMOJI_DIGIT_SUFFIX:
                row.append(int(ch))
                i += 3
            else:
                row.append(int(ch))
                i += 1
        else:
            i += 1
    return row


def parse_board_string(text: str) -> dict:
    result = {
        "rows": None,
        "columns": None,
        "mines": None,
        "game_mode": None,
        "render": "ascii",
        "real": None,
        "view": None,
    }
    lines = text.splitlines()
    section = None
    board_rows = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            if "Render:" in stripped:
                _, _, r = stripped.partition("Render:")
                result["render"] = r.strip()
            continue

        if stripped == "[real]":
            section = "real"
            board_rows = []
            continue
        if stripped == "[view]":
            section = "view"
            board_rows = []
            continue

        if ":" in stripped and section is None:
            key, _, value = stripped.partition(":")
            key = key.strip()
            value = value.strip()
            if key == "rows":
                result["rows"] = int(value)
            elif key == "columns":
                result["columns"] = int(value)
            elif key == "mines":
                result["mines"] = int(value)
            elif key == "game_mode":
                result["game_mode"] = value
            continue

        if section in ("real", "view"):
            board_rows.append(stripped)
            result[section] = board_rows

    return result


def board_string_to_game_board(text: str) -> Tuple[List[List[int]], str]:
    parsed = parse_board_string(text)
    if parsed["view"]:
        board_rows = parsed["view"]
        source = "view"
    elif parsed["real"]:
        board_rows = parsed["real"]
        source = "real"
    else:
        return [], ""

    is_emoji = parsed["render"] == "emoji"
    parse_fn = _parse_view_line_emoji if is_emoji else _parse_view_line_ascii

    game_board = [parse_fn(line) for line in board_rows]
    return game_board, source

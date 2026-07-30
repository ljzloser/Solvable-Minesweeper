from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple, Union

from config.constants import CELL_FLAGGED, CELL_UNOPENED


Board = List[List[Any]]
ReplayAnalysisResult = Optional[Union["ReplayEventAnnotation", Iterable["ReplayEventAnnotation"]]]
ReplayAnalysisRule = Callable[["ReplayEventContext"], ReplayAnalysisResult]
ReplayAnalysisProgressCallback = Callable[[int, int], None]


@dataclass(frozen=True)
class ReplayMouseEvent:
    raw: Any
    mouse: str
    x: int
    y: int
    row: Optional[int]
    column: Optional[int]

    def is_mouse(self, *mouse_names: str) -> bool:
        return self.mouse in mouse_names


@dataclass(frozen=True)
class ReplayBoardEvent:
    raw: Any
    board: str
    row: int
    column: int

    @property
    def opens_cell(self) -> bool:
        return is_open_board_event(self.board)

    @property
    def opens_zero_cell(self) -> bool:
        return is_zero_board_event(self.board)


@dataclass(frozen=True)
class ReplayOpenedCell:
    row: int
    column: int
    prior_value: Any
    next_value: Any
    source: str = "board_diff"


@dataclass(frozen=True)
class ReplayEventAnnotation:
    severity: str
    text: str
    key: str = ""
    params: Tuple[Any, ...] = ()
    event_index: Optional[int] = None
    time: Optional[float] = None
    highlight_cells: Tuple[Tuple[int, int], ...] = ()


@dataclass(frozen=True)
class ReplayEventRow:
    time: float
    event_index: int
    annotations: Tuple[ReplayEventAnnotation, ...]

    @property
    def time_ms(self) -> int:
        return int(self.time * 1000)


@dataclass(frozen=True)
class ReplayEventContext:
    video: Any
    records: Sequence[Any]
    index: int
    record: Any
    previous_record: Optional[Any]
    next_record: Optional[Any]
    time: float
    event: Any
    mouse: Optional[ReplayMouseEvent]
    board_event: Optional[ReplayBoardEvent]
    prior_board: Any
    next_board: Any
    useful_level: int
    path: float
    mouse_state: int
    key_dynamic_params: Any
    row_count: int
    column_count: int
    mine_num: int
    pix_size: int

    @property
    def is_mouse_event(self) -> bool:
        return self.mouse is not None

    @property
    def is_board_event(self) -> bool:
        return self.board_event is not None

    def prior_game_board(self) -> Optional[Board]:
        return extract_game_board(self.prior_board)

    def next_game_board(self) -> Optional[Board]:
        return extract_game_board(self.next_board)

    def prior_raw_board(self) -> Optional[Board]:
        return extract_raw_board(self.prior_board)

    def next_raw_board(self) -> Optional[Board]:
        return extract_raw_board(self.next_board)

    def prior_possibility_board(self) -> Optional[Board]:
        return extract_possibility_board(self.prior_board)

    def next_possibility_board(self) -> Optional[Board]:
        return extract_possibility_board(self.next_board)


_REPLAY_ANALYSIS_RULES: List[ReplayAnalysisRule] = []


def register_replay_analysis_rule(rule: ReplayAnalysisRule) -> ReplayAnalysisRule:
    _REPLAY_ANALYSIS_RULES.append(rule)
    return rule


def clear_replay_analysis_rules() -> None:
    _REPLAY_ANALYSIS_RULES.clear()


def get_replay_analysis_rules() -> Tuple[ReplayAnalysisRule, ...]:
    return tuple(_REPLAY_ANALYSIS_RULES)


def analyse_replay_events(
    video: Any,
    rules: Optional[Sequence[ReplayAnalysisRule]] = None,
    progress_callback: Optional[ReplayAnalysisProgressCallback] = None,
) -> List[ReplayEventRow]:
    active_rules = tuple(_REPLAY_ANALYSIS_RULES if rules is None else rules)
    records = list(getattr(video, "events", []) or [])
    total_records = len(records)
    _report_analysis_progress(progress_callback, 0, total_records)
    if not active_rules:
        _report_analysis_progress(progress_callback, total_records, total_records)
        return []

    annotations_by_index: Dict[int, List[ReplayEventAnnotation]] = {}
    time_by_index: Dict[int, float] = {}
    progress_step = max(1, total_records // 100) if total_records else 1

    for context in iter_replay_event_contexts(video, records):
        for rule in active_rules:
            for annotation in _normalise_rule_result(rule(context)):
                event_index = annotation.event_index
                if event_index is None or event_index < 0 or event_index >= len(records):
                    event_index = context.index
                event_time = annotation.time
                if event_time is None:
                    event_time = _record_time(records[event_index])
                time_by_index.setdefault(event_index, event_time)
                annotations_by_index.setdefault(event_index, []).append(annotation)
        current_record = context.index + 1
        if current_record == total_records or current_record % progress_step == 0:
            _report_analysis_progress(progress_callback, current_record, total_records)

    return [
        ReplayEventRow(
            time=time_by_index[event_index],
            event_index=event_index,
            annotations=tuple(annotations_by_index[event_index]),
        )
        for event_index in sorted(annotations_by_index)
    ]


def _report_analysis_progress(
    progress_callback: Optional[ReplayAnalysisProgressCallback],
    current: int,
    total: int,
) -> None:
    if progress_callback is not None:
        progress_callback(current, total)


def iter_replay_event_contexts(
    video: Any,
    records: Optional[Sequence[Any]] = None,
) -> Iterator[ReplayEventContext]:
    if records is None:
        records = list(getattr(video, "events", []) or [])

    row_count = _to_int(getattr(video, "row", 0))
    column_count = _to_int(getattr(video, "column", 0))
    mine_num = _to_int(getattr(video, "mine_num", 0))
    pix_size = _to_int(getattr(video, "pix_size", 0))

    for index, record in enumerate(records):
        event = getattr(record, "event", None)
        yield ReplayEventContext(
            video=video,
            records=records,
            index=index,
            record=record,
            previous_record=records[index - 1] if index > 0 else None,
            next_record=records[index + 1] if index + 1 < len(records) else None,
            time=_record_time(record),
            event=event,
            mouse=unwrap_mouse_event(event, pix_size),
            board_event=unwrap_board_event(event),
            prior_board=getattr(record, "prior_game_board", None),
            next_board=getattr(record, "next_game_board", None),
            useful_level=_to_int(getattr(record, "useful_level", 0)),
            path=_to_float(getattr(record, "path", 0.0)),
            mouse_state=_to_int(getattr(record, "mouse_state", 0)),
            key_dynamic_params=getattr(record, "key_dynamic_params", None),
            row_count=row_count,
            column_count=column_count,
            mine_num=mine_num,
            pix_size=pix_size,
        )


def is_mouse_event(event: Any) -> bool:
    return _bool_member(event, "is_mouse")


def is_board_event(event: Any) -> bool:
    return _bool_member(event, "is_board")


def unwrap_mouse_event(event: Any, pix_size: int = 0) -> Optional[ReplayMouseEvent]:
    if not is_mouse_event(event):
        return None

    try:
        raw_mouse = event.unwrap_mouse()
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return None
    if raw_mouse is None:
        return None

    x = _to_int(getattr(raw_mouse, "x", 0))
    y = _to_int(getattr(raw_mouse, "y", 0))
    row = y // pix_size if pix_size > 0 else None
    column = x // pix_size if pix_size > 0 else None
    return ReplayMouseEvent(
        raw=raw_mouse,
        mouse=str(getattr(raw_mouse, "mouse", "")),
        x=x,
        y=y,
        row=row,
        column=column,
    )


def unwrap_board_event(event: Any) -> Optional[ReplayBoardEvent]:
    if not is_board_event(event):
        return None

    try:
        raw_board = event.unwrap_board()
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return None
    if raw_board is None:
        return None

    return ReplayBoardEvent(
        raw=raw_board,
        board=str(getattr(raw_board, "board", "")),
        row=_to_int(getattr(raw_board, "row_id", 0)),
        column=_to_int(getattr(raw_board, "column_id", 0)),
    )


def opened_cells(context: ReplayEventContext) -> List[ReplayOpenedCell]:
    board_event_cell = _opened_cell_from_board_event(context)
    if context.board_event is not None:
        return [board_event_cell] if board_event_cell is not None else []

    prior_board = context.prior_game_board()
    next_board = context.next_game_board()
    if prior_board is None or next_board is None:
        return []

    row_count = min(board_size(prior_board)[0], board_size(next_board)[0])
    column_count = min(board_size(prior_board)[1], board_size(next_board)[1])
    cells: List[ReplayOpenedCell] = []
    for row in range(row_count):
        for column in range(column_count):
            prior_value = cell_at(prior_board, row, column)
            next_value = cell_at(next_board, row, column)
            if is_closed_cell(prior_value) and is_open_cell(next_value):
                cells.append(ReplayOpenedCell(row, column, prior_value, next_value))
    return cells


def extract_game_board(board_holder: Any) -> Optional[Board]:
    if board_holder is None:
        return None
    return _copy_matrix(getattr(board_holder, "game_board", None))


def extract_raw_board(board_holder: Any) -> Optional[Board]:
    if board_holder is None:
        return None
    return _copy_matrix(getattr(board_holder, "board", None))


def extract_possibility_board(board_holder: Any) -> Optional[Board]:
    if board_holder is None:
        return None
    matrix = getattr(board_holder, "game_board_poss", None)
    if matrix is None:
        matrix = getattr(board_holder, "poss", None)
    return _copy_matrix(matrix)


def cell_at(board: Optional[Board], row: int, column: int, default: Any = None) -> Any:
    if board is None or row < 0 or column < 0:
        return default
    try:
        return board[row][column]
    except (IndexError, TypeError):
        return default


def neighbours(row: int, column: int, row_count: int, column_count: int) -> Iterator[Tuple[int, int]]:
    for row_delta in (-1, 0, 1):
        for column_delta in (-1, 0, 1):
            if row_delta == 0 and column_delta == 0:
                continue
            next_row = row + row_delta
            next_column = column + column_delta
            if 0 <= next_row < row_count and 0 <= next_column < column_count:
                yield next_row, next_column


def board_size(board: Optional[Board]) -> Tuple[int, int]:
    if not board:
        return 0, 0
    return len(board), len(board[0]) if board[0] else 0


def is_closed_cell(value: Any) -> bool:
    return value in (CELL_UNOPENED, CELL_FLAGGED)


def is_open_cell(value: Any) -> bool:
    return value is not None and value not in (CELL_UNOPENED, CELL_FLAGGED)


def is_open_board_event(board_value: str) -> bool:
    board_value = normalise_board_event_value(board_value)
    return board_value.startswith("cell_") or board_value == "blast"


def is_zero_board_event(board_value: str) -> bool:
    return normalise_board_event_value(board_value) == "cell_0"


def records_between_mouse_events(context: ReplayEventContext) -> Iterator[Any]:
    first_index, last_index = _board_event_interval_bounds(context)
    for index in range(first_index, last_index):
        record = context.records[index]
        if unwrap_board_event(getattr(record, "event", None)) is not None:
            yield record


def prior_records_between_mouse_events(context: ReplayEventContext) -> Iterator[Any]:
    first_index, _ = _board_event_interval_bounds(context)
    for index in range(first_index, context.index):
        record = context.records[index]
        if unwrap_board_event(getattr(record, "event", None)) is not None:
            yield record


def normalise_board_event_value(board_value: str) -> str:
    return board_value.strip().lower()


def _board_event_interval_bounds(context: ReplayEventContext) -> Tuple[int, int]:
    previous_mouse_index = _previous_mouse_event_index(context)
    next_mouse_index = _next_mouse_event_index(context)
    return previous_mouse_index + 1, next_mouse_index


def _previous_mouse_event_index(context: ReplayEventContext) -> int:
    start_index = context.index if context.is_mouse_event else context.index - 1
    for index in range(start_index, -1, -1):
        if is_mouse_event(getattr(context.records[index], "event", None)):
            return index
    return -1


def _next_mouse_event_index(context: ReplayEventContext) -> int:
    for index in range(context.index + 1, len(context.records)):
        if is_mouse_event(getattr(context.records[index], "event", None)):
            return index
    return len(context.records)


def _normalise_rule_result(
    result: ReplayAnalysisResult,
) -> Iterator[ReplayEventAnnotation]:
    if result is None:
        return
    if isinstance(result, ReplayEventAnnotation):
        yield result
        return
    yield from result


def _opened_cell_from_board_event(context: ReplayEventContext) -> Optional[ReplayOpenedCell]:
    if context.board_event is None or not context.board_event.opens_cell:
        return None

    prior_board = context.prior_game_board()
    next_board = context.next_game_board()
    row = context.board_event.row
    column = context.board_event.column
    return ReplayOpenedCell(
        row=row,
        column=column,
        prior_value=cell_at(prior_board, row, column),
        next_value=cell_at(next_board, row, column),
        source="board_event",
    )


def _copy_matrix(matrix: Any) -> Optional[Board]:
    if matrix is None:
        return None
    try:
        return [list(row) for row in matrix]
    except TypeError:
        return None


def _bool_member(value: Any, name: str) -> bool:
    member = getattr(value, name, False)
    if callable(member):
        try:
            return bool(member())
        except (RuntimeError, TypeError, ValueError):
            return False
    return bool(member)


def _record_time(record: Any) -> float:
    return _to_float(getattr(record, "time", 0.0))


def _to_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0

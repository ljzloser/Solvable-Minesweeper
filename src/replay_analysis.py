from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple, Union


Board = List[List[Any]]
ReplayAnalysisResult = Optional[Union["ReplayEventAnnotation", Iterable["ReplayEventAnnotation"]]]
ReplayAnalysisRule = Callable[["ReplayEventContext"], ReplayAnalysisResult]


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
class ReplayEventAnnotation:
    severity: str
    text: str
    key: str = ""
    params: Tuple[Any, ...] = ()
    event_index: Optional[int] = None
    time: Optional[float] = None


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
) -> List[ReplayEventRow]:
    active_rules = tuple(_REPLAY_ANALYSIS_RULES if rules is None else rules)
    if not active_rules:
        return []

    records = list(getattr(video, "events", []) or [])
    annotations_by_index: Dict[int, List[ReplayEventAnnotation]] = {}
    time_by_index: Dict[int, float] = {}

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

    return [
        ReplayEventRow(
            time=time_by_index[event_index],
            event_index=event_index,
            annotations=tuple(annotations_by_index[event_index]),
        )
        for event_index in sorted(annotations_by_index)
    ]


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
    return bool(getattr(event, "is_mouse", False))


def unwrap_mouse_event(event: Any, pix_size: int = 0) -> Optional[ReplayMouseEvent]:
    if not is_mouse_event(event):
        return None

    try:
        raw_mouse = event.unwrap_mouse()
    except (AttributeError, RuntimeError, TypeError, ValueError):
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


def _normalise_rule_result(
    result: ReplayAnalysisResult,
) -> Iterator[ReplayEventAnnotation]:
    if result is None:
        return
    if isinstance(result, ReplayEventAnnotation):
        yield result
        return
    yield from result


def _copy_matrix(matrix: Any) -> Optional[Board]:
    if matrix is None:
        return None
    try:
        return [list(row) for row in matrix]
    except TypeError:
        return None


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

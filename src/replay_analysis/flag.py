from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from PyQt5.QtCore import QCoreApplication

from .core import (
    ReplayEvent,
    ReplayEventContext,
    ReplayEventManager,
    is_mouse_event,
    register_replay_event_manager,
    unwrap_mouse_event,
)
from .format import format_number


Cell = Tuple[int, int]
_translate = QCoreApplication.translate


@dataclass
class FlagContribution:
    event_index: int
    time: float
    row: int
    column: int
    dce: float = 0.0
    bbbv_solved: float = 0.0
    dce_cells: Tuple[Cell, ...] = ()


class FlagEvent(ReplayEvent):
    def __init__(self, flag: FlagContribution):
        self.dce = flag.dce
        self.bbbv_solved = flag.bbbv_solved
        self.row = flag.row
        self.column = flag.column
        self.dce_cells = flag.dce_cells
        super().__init__(
            event_index=flag.event_index,
            time=flag.time,
            coordinate=(flag.row, flag.column),
            params=(flag.dce, flag.bbbv_solved),
        )

    def type_text(self) -> str:
        return _translate("ReplayAnalysis", "标雷")

    def detail_text(self) -> str:
        text = _translate("ReplayAnalysis", "双击{dce}次，解决{bbbv}bv")
        return (
            text
            .replace("{dce}", format_number(self.dce))
            .replace("{bbbv}", format_number(self.bbbv_solved))
        )

    def severity(self) -> str:
        return _flag_event_severity(self.dce, self.bbbv_solved)

    def highlight_cells(self) -> Tuple[Tuple[int, int], ...]:
        return ((self.row, self.column), *self.dce_cells)


@register_replay_event_manager
class FlagEventManager(ReplayEventManager):
    def reset(self, _video: Any) -> None:
        self.flags_by_index: Dict[int, FlagContribution] = {}
        self.active_flags: List[Tuple[int, Cell]] = []
        self.previous_mouse_record: Optional[Any] = None

    def handle(self, context: ReplayEventContext) -> Tuple[ReplayEvent, ...]:
        mouse_event = _mouse_event_record(context, context.index)
        if mouse_event is None:
            return ()

        _mouse_name, row, column = mouse_event
        if _counter_delta(self.previous_mouse_record, context.record, "flag") > 0:
            flag = FlagContribution(
                event_index=context.index,
                time=context.time,
                row=row,
                column=column,
            )
            self.flags_by_index[context.index] = flag
            self.active_flags.append((context.index, (row, column)))
        elif _counter_delta(self.previous_mouse_record, context.record, "flag") < 0:
            _remove_active_flag(self.active_flags, row, column)

        dce_delta = _counter_delta(self.previous_mouse_record, context.record, "dce", "double_ce")
        if dce_delta > 0:
            bbbv_delta = _counter_delta(self.previous_mouse_record, context.record, "bbbv_solved")
            nearby_flags = [
                flag_index
                for flag_index, flag_cell in self.active_flags
                if _is_nearby(flag_cell, (row, column))
            ]
            if nearby_flags:
                dce_share = dce_delta / len(nearby_flags)
                bbbv_share = bbbv_delta / len(nearby_flags)
                for flag_index in nearby_flags:
                    flag = self.flags_by_index[flag_index]
                    flag.dce += dce_share
                    flag.bbbv_solved += bbbv_share
                    flag.dce_cells = _append_unique_cell(flag.dce_cells, (row, column))

        self.previous_mouse_record = context.record
        return ()

    def finish(self) -> Tuple[ReplayEvent, ...]:
        return tuple(
            FlagEvent(flag)
            for _, flag in sorted(self.flags_by_index.items())
        )


def _mouse_event_record(
    context: ReplayEventContext,
    index: int,
) -> Optional[Tuple[str, int, int]]:
    record = context.records[index]
    event = getattr(record, "event", None)
    if not is_mouse_event(event):
        return None
    mouse = unwrap_mouse_event(event, context.pix_size)
    if mouse is None or mouse.mouse in {"mv", "mc", "mr"}:
        return None
    return mouse.mouse, mouse.row, mouse.column


def _counter_delta(
    previous_record: Optional[Any],
    current_record: Any,
    *counter_names: str,
) -> int:
    for counter_name in counter_names:
        previous_value = _record_counter(previous_record, counter_name)
        current_value = _record_counter(current_record, counter_name)
        if previous_value is None:
            previous_value = 0
        if current_value is not None:
            return current_value - previous_value
    return 0


def _record_counter(record: Optional[Any], counter_name: str) -> Optional[int]:
    if record is None:
        return None
    key_dynamic_params = getattr(record, "key_dynamic_params", None)
    for source in (key_dynamic_params, record):
        try:
            return int(getattr(source, counter_name))
        except (AttributeError, RuntimeError):
            continue
    return None


def _remove_active_flag(active_flags: List[Tuple[int, Cell]], row: int, column: int) -> None:
    for index in range(len(active_flags) - 1, -1, -1):
        if active_flags[index][1] == (row, column):
            del active_flags[index]
            return


def _is_nearby(left: Cell, right: Cell) -> bool:
    return abs(left[0] - right[0]) <= 1 and abs(left[1] - right[1]) <= 1


def _append_unique_cell(cells: Tuple[Cell, ...], cell: Cell) -> Tuple[Cell, ...]:
    if cell in cells:
        return cells
    return (*cells, cell)


def _flag_event_severity(dce: float, bbbv_solved: float) -> str:
    if bbbv_solved == 0:
        return "error"
    if bbbv_solved > dce + 1:
        return "success"
    if bbbv_solved < dce + 1:
        return "warning"
    return "info"

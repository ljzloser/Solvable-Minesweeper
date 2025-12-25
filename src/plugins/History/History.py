import base64
import sys
import os
import msgspec
import zmq
import sqlite3


if getattr(sys, "frozen", False):  # 检查是否为pyInstaller生成的EXE
    application_path = os.path.dirname(sys.executable)
    sys.path.append(application_path + "/../../")
    print(application_path + "/../../")
else:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../")
from mp_plugins import BasePlugin, BaseConfig
from mp_plugins.base.config import *
from mp_plugins.context import AppContext
from mp_plugins.events import *


class HistoryConfig(BaseConfig):
    pass


class History(BasePlugin):
    def __init__(
        self,
    ) -> None:
        super().__init__()
        self._context: AppContext
        self._config = HistoryConfig()

    def build_plugin_context(self) -> None:
        self._plugin_context.name = "History"
        self._plugin_context.display_name = "历史记录"
        self._plugin_context.version = "1.0.0"
        self._plugin_context.description = "History"
        self._plugin_context.author = "ljzloser"

    @property
    def db_path(self):
        return self.path.parent.parent / "history.db"

    def initialize(self) -> None:
        if not self.db_path.exists():
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
create table history
(
    replay_id        INTEGER primary key,
    game_board_state INTEGER,
    rtime           REAL,
    left            INTEGER,
    right           INTEGER,
    double          INTEGER,
    left_s          REAL,
    right_s         REAL,
    double_s        REAL,
    level           INTEGER,
    cl              INTEGER,
    cl_s            REAL,
    ce              INTEGER,
    ce_s            REAL,
    rce             INTEGER,
    lce             INTEGER,
    dce             INTEGER,
    bbbv            INTEGER,
    bbbv_solved     INTEGER,
    bbbv_s          REAL,
    flag            INTEGER,
    path            REAL,
    etime           INTEGER,
    start_time      INTEGER,
    end_time        INTEGER,
    mode            INTEGER,
    software        TEXT,
    player_identifier TEXT,
    race_identifier   TEXT,
    uniqueness_identifier TEXT,
    stnb            REAL,
    corr            REAL,
    thrp            REAL,
    ioe             REAL,
    is_official     INTEGER,
    is_fair         INTEGER,
    op              INTEGER,
    isl             INTEGER,
    raw_data        BLOB
);
                """
            )
            conn.commit()
            conn.close()
        return super().initialize()

    def shutdown(self) -> None:
        return super().shutdown()

    @BasePlugin.event_handler(GameEndEvent)
    def on_game_end(self, event: GameEndEvent):
        data = msgspec.structs.asdict(event)
        data["raw_data"] = base64.b64decode(s=event.raw_data)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
insert into main.history
(
    game_board_state,
    rtime,
    left,
    right,
    double,
    left_s,
    right_s,
    double_s,
    level,
    cl,
    cl_s,
    ce,
    ce_s,
    rce,
    lce,
    dce,
    bbbv,
    bbbv_solved,
    bbbv_s,
    flag,
    path,
    etime,
    start_time,
    end_time,
    mode,
    software,
    player_identifier,
    race_identifier,
    uniqueness_identifier,
    stnb,
    corr,
    thrp,
    ioe,
    is_official,
    is_fair,
    op,
    isl,
    raw_data
    )
values
(
    :game_board_state,
    :rtime,
    :left,
    :right,
    :double,
    :left_s,
    :right_s,
    :double_s,
    :level,
    :cl,
    :cl_s,
    :ce,
    :ce_s,
    :rce,
    :lce,
    :dce,
    :bbbv,
    :bbbv_solved,
    :bbbv_s,
    :flag,
    :path,
    :etime,
    :start_time,
    :end_time,
    :mode,
    :software,
    :player_identifier,
    :race_identifier,
    :uniqueness_identifier,
    :stnb,
    :corr,
    :thrp,
    :ioe,
    :is_official,
    :is_fair,
    :op,
    :isl,
    :raw_data
    )
        """,
            data)
        conn.commit()
        conn.close()
        return event


if __name__ == "__main__":
    try:
        import sys

        args = sys.argv[1:]
        host = args[0]
        port = int(args[1])
        plugin = History()
        # 捕获退出信号，优雅关闭
        import signal

        def signal_handler(sig, frame):
            plugin.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        plugin.run(host, port)
    except Exception:
        pass

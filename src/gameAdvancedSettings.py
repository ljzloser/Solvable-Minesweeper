from PyQt5.QtWidgets import QCheckBox
from ui.ui_advanced import Ui_Form
from ui.uiComponents import RoundQDialog
from shared_types.commands import COMMAND_TYPES


_COMMAND_LABELS = {
    "mouse_click": "鼠标点击（MouseClickCommand）",
    "new_game": "重开新局（NewGameCommand）",
}


def _get_tag(cmd_type: type) -> str:
    tag = getattr(cmd_type, '__struct_config__', None)
    if tag is not None:
        tag = getattr(tag, 'tag', None)
    return str(tag)


class ui_Form(Ui_Form):
    def __init__(self, mainWindow):
        self.game_setting = mainWindow.game_setting
        self.r_path = mainWindow.r_path
        self.filter_forever = mainWindow.filter_forever

        self.alter = False
        self._denied_controls: set[str] = self._load_denied_controls()

        self.Dialog = RoundQDialog(mainWindow.mainWindow)
        self.setupUi(self.Dialog)

        self.pushButton_yes.clicked.connect(self._on_accept)
        self.pushButton_no.clicked.connect(self.Dialog.close)
        self.btn_open_auth_dialog.clicked.connect(self._open_plugin_auth)

        self._build_allow_ui()
        self.setParameter()

    # ── 允许控制命令 ──────────────────────────────────

    def _load_denied_controls(self) -> set[str]:
        raw = self.game_setting.value('DEFAULT/denied_controls', '', str)
        return set(raw.split(',')) if raw else set()

    def _save_denied_controls(self) -> None:
        raw = ','.join(sorted(self._denied_controls))
        self.game_setting.set_value('DEFAULT/denied_controls', raw)

    def _build_allow_ui(self) -> None:
        for cmd_type in COMMAND_TYPES:
            try:
                tag = _get_tag(cmd_type)
            except (ValueError, TypeError):
                continue

            label = _COMMAND_LABELS.get(tag, tag)
            cb = QCheckBox()
            # 勾选 = 允许（不拒绝），不勾选 = 拒绝
            cb.setChecked(tag not in self._denied_controls)
            cb.setText(f"允许{label}")

            cb.stateChanged.connect(
                lambda checked, t=tag: self._on_allow_toggled(t, bool(checked))
            )
            self.verticalLayout_auth_items.addWidget(cb)

    def _on_allow_toggled(self, tag: str, checked: bool) -> None:
        if checked:
            self._denied_controls.discard(tag)
        else:
            self._denied_controls.add(tag)

    def _open_plugin_auth(self) -> None:
        from shared_types.events import ShowPluginManagerEvent
        from plugin_sdk.server_bridge import GameServerBridge
        GameServerBridge.instance().send_event(ShowPluginManagerEvent())
        self.Dialog.close()

    # ── 基本参数 ────────────────────────────────────────

    def setParameter(self) -> None:
        self.checkBox_filter_forever.setChecked(self.filter_forever)

    def _on_accept(self) -> None:
        self.alter = True

        self.filter_forever = self.checkBox_filter_forever.isChecked()
        self.game_setting.set_value("DEFAULT/filter_forever", self.filter_forever)
        self._save_denied_controls()

        self.game_setting.sync()
        self.Dialog.close()

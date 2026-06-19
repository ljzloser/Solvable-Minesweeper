set HISTORY_PLUGIN=..\plugins\History\plugin.py ..\plugins\History\main_widget.py ..\plugins\History\history_table.py ..\plugins\History\table_views.py ..\plugins\History\table_model.py ..\plugins\History\models.py ..\plugins\History\filter_dialog.py ..\plugins\History\sort_dialog.py ..\plugins\History\columns_dialog.py ..\plugins\History\delegates.py
set LLM_PLUGIN=..\plugins\llm_minesweeper_controller\config.py ..\plugins\llm_minesweeper_controller\widgets.py ..\plugins\llm_minesweeper_controller\plugin.py ..\plugins\llm_minesweeper_controller\api_client.py ..\plugins\llm_minesweeper_controller\function_registry.py
set XIANNI_PLUGIN=..\plugins\XianNiUpgrade\plugin.py ..\plugins\XianNiUpgrade\widgets.py ..\plugins\XianNiUpgrade\models.py

pylupdate5 ui_gameSettings.py ui_main_board.py ui_about.py ui_defined_parameter.py ui_gameSettingShortcuts.py ui_score_board.py ui_record_pop.py ui_advanced.py ui_video_control.py ../videoControl.py ../utils.py %HISTORY_PLUGIN% %LLM_PLUGIN% %XIANNI_PLUGIN% -ts en_US.ts -noobsolete

pylupdate5 ui_gameSettings.py ui_main_board.py ui_about.py ui_defined_parameter.py ui_gameSettingShortcuts.py ui_score_board.py ui_record_pop.py ui_advanced.py ui_video_control.py ../videoControl.py ../utils.py %HISTORY_PLUGIN% %LLM_PLUGIN% %XIANNI_PLUGIN% -ts pl_PL.ts -noobsolete

pylupdate5 ui_gameSettings.py ui_main_board.py ui_about.py ui_defined_parameter.py ui_gameSettingShortcuts.py ui_score_board.py ui_record_pop.py ui_advanced.py ui_video_control.py ../videoControl.py ../utils.py %HISTORY_PLUGIN% %LLM_PLUGIN% %XIANNI_PLUGIN% -ts de_DE.ts -noobsolete

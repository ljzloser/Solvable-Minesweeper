from PyQt5 import QtCore
from PyQt5.QtCore import QTimer, QCoreApplication, Qt, QRect
from PyQt5.QtGui import QPixmap
# from PyQt5.QtWidgets import QLineEdit, QInputDialog, QShortcut
from PyQt5.QtWidgets import QApplication, QFileDialog, QWidget
import gameDefinedParameter
import  videoControl
import ms_toollib as ms
from mineSweeperGUIEvent import MineSweeperGUIEvent

class MineSweeperVideoPlayer(MineSweeperGUIEvent):
    
    # 打开录像文件的回调
    def action_OpenFile(self, openfile_name=None):
        self.setting_path / 'replay'
        
        self.ui_video_control = videoControl.ui_Form(self.r_path, self.game_setting,
                                                     self.mainWindow)
        
        self.unlimit_cursor()
        if not openfile_name:
            openfile_name = QFileDialog.\
                getOpenFileName(self.mainWindow, '打开文件', str(self.setting_path / 'replay'),
                                'All(*.avf *.evf *.rmv *.mvf *.evfs);;Arbiter video(*.avf);;Metasweeper video(*.evf);;Vienna MineSweeper video(*.rmv);;Minesweeper Clone 0.97(*.mvf);;Metasweeper video set(*.evfs)')
            openfile_name = openfile_name[0]
        # 实例化
        if not openfile_name:
            if self.cursor_limit:
                self.limit_cursor()
            return
        self.set_face(14)

        video_set = None
        try:
            if openfile_name[-3:] == "avf":
                video = ms.AvfVideo(openfile_name)
            elif openfile_name[-3:] == "rmv":
                video = ms.RmvVideo(openfile_name)
            elif openfile_name[-3:] == "evf":
                video = ms.EvfVideo(openfile_name)
            elif openfile_name[-3:] == "mvf":
                video = ms.MvfVideo(openfile_name)
            elif openfile_name[-4:] == "evfs":
                video_set = ms.Evfs(openfile_name)
                # 包含对每个evf的parse
                # video_set.parse()
                # video = video_set[0].evf_video
            else:
                return
        except:
            return
        
        
        if video_set:
            # 包含对每个evf的parse
            video_set.parse()
            video_set.analyse()
            video_set.analyse_for_features(["high_risk_guess", "jump_judge", "needless_guess",
                                            "mouse_trace", "vision_transfer", "pluck",
                                            "super_fl_local"])
            self.ui_video_control.add_new_video_set_tab(video_set)
            video = video_set[0].evf_video
        else:
            video.parse_video()
            video.analyse()
            video.analyse_for_features(["high_risk_guess", "jump_judge", "needless_guess",
                                        "mouse_trace", "vision_transfer", "pluck",
                                        "super_fl_local"])
        self.ui_video_control.add_new_video_tab(video)
        self.ui_video_control.videoTabClicked.connect(lambda x: self.play_video(video_set[x].evf_video))
        self.play_video(video)
        

    # 播放新录像，调整局面尺寸等
    # 控制台中，不添加新标签、连接信号。假如关闭就展示
    # 播放AvfVideo、RmvVideo、EvfVideo、MvfVideo或BaseVideo
    def play_video(self, video):
        # if self.game_state == 'display':
        #     self.ui_video_control.QWidget.close()
        # self.game_state = 'display'
        if self.game_state != 'display':
            self.game_state = 'display'

        
        # 检查evf的checksum，其余录像没有鉴定能力
        if isinstance(video, ms.EvfVideo):
            self.score_board_manager.with_namespace({
                "checksum_ok": self.checksum_guard.
                valid_checksum(video.raw_data[:-(len(video.checksum) + 2)], video.checksum),
            })
        else:
            self.score_board_manager.with_namespace({
                "checksum_ok": False,
            })
        self.score_board_manager.with_namespace({
            "is_official": video.is_official,
            "is_fair": video.is_fair,
            "mode": video.mode,
            "row": video.row,
            "column": video.column,
            "minenum": video.mine_num,
        })
        # 调整窗口
        if (video.row, video.column) != (self.row, self.column):
            self.setBoard(video.row, video.column, video.mine_num)
            self.label.paintProbability = False
            self.label.set_rcp(self.row, self.column, self.pixSize)
            # self.label.reloadCellPic(self.pixSize)
            self.label.setMinimumSize(QtCore.QSize(
                self.pixSize*self.column + 8, self.pixSize*self.row + 8))
            self.label.setMaximumSize(QtCore.QSize(
                self.pixSize*self.column + 8, self.pixSize*self.row + 8))
            self.label_2.reloadFace(self.pixSize)
            self.minimumWindow()

        self.timer_video = QTimer()
        self.timer_video.timeout.connect(self.video_playing_step)
        
        self.ui_video_control.pushButton_play.clicked.connect(self.video_play)
        self.ui_video_control.pushButton_replay.clicked.connect(
            self.video_replay)
        self.ui_video_control.videoSetTime.connect(self.video_set_time)
        self.ui_video_control.videoSetTimePeriod.connect(self.video_set_a_time)
        self.ui_video_control.label_speed.wEvent.connect(self.video_set_speed)
        
        self.ui_video_control.QWidget.show()

        self.video_time = video.video_start_time  # 录像当前时间
        self.video_stop_time = video.video_end_time  # 录像停止时间
        self.video_time_step = 0.01  # 录像时间的步长，定时器始终是10毫秒
        self.label.paint_cursor = True
        self.video_playing = True  # 录像正在播放
        # 禁用双击修改指标名称公式
        self.score_board_manager.editing_row = -2

        video.video_playing_pix_size = self.label.pixSize
        self.label.ms_board = video
        # 改成录像的标识
        # print(self.label.ms_board.player_identifier)
        self.label_info.setText(self.label.ms_board.player_identifier)
        # 改成录像的国旗
        self.set_country_flag(self.label.ms_board.country)

        self.timer_video.start(10)

    def video_playing_step(self):
        # 播放录像时定时器的回调
        self.label.ms_board.current_time = self.video_time
        if self.video_time >= self.video_stop_time:
            self.timer_video.stop()
            self.video_playing = False
        self.label.update()
        
        # 回放时修改小黄脸，使用了一个变量做工具箱的补丁
        match self.label.ms_board.mouse_state:
            case 1 | 7:
                self.set_face(14)
            case 2 | 4 | 5 | 6:
                self.set_face(15)
            case 3:
                if self.last_mouse_state_video_playing_step in {5, 6}:
                    self.set_face(14)
                else:
                    self.set_face(15)
        self.last_mouse_state_video_playing_step = self.label.ms_board.mouse_state
        
        self.score_board_manager.show(self.label.ms_board, index_type=3)
        self.video_time += self.video_time_step
        self.showTime(int(self.video_time))
        self.ui_video_control.horizontalSlider_time.blockSignals(True)
        self.ui_video_control.horizontalSlider_time.setValue(
            int(self.video_time * 1000))
        self.ui_video_control.horizontalSlider_time.blockSignals(False)
        self.ui_video_control.doubleSpinBox_time.blockSignals(True)
        self.ui_video_control.doubleSpinBox_time.setValue(
            self.label.ms_board.time)
        self.ui_video_control.doubleSpinBox_time.blockSignals(False)

    def video_play(self):
        # 点播放、暂停键的回调
        if self.video_playing:
            self.video_playing = False
            self.timer_video.stop()
        else:
            self.video_playing = True
            self.timer_video.start(10)
            self.video_stop_time = self.label.ms_board.video_end_time

    def video_replay(self):
        self.video_playing = True
        self.video_time = self.label.ms_board.video_start_time
        self.timer_video.start(10)
        self.video_stop_time = self.label.ms_board.video_end_time

    def video_set_speed(self, speed):
        self.video_time_step = speed * 0.01

    def video_set_time(self, t):
        # 把录像定位到某一个时刻。是拖动进度条的回调
        self.video_time = t / 1000
        self.label.ms_board.current_time = self.video_time
        self.label.update()
        self.score_board_manager.show(self.label.ms_board, index_type=3)

    def video_set_a_time(self, t):
        # 把录像定位到某一段时间，默认前后一秒，自动播放。是点录像事件的回调
        self.video_time = (t - 1000) / 1000
        self.video_stop_time = (t + 1000) / 1000  # 大了也没关系，ms_toollib自动处理
        self.timer_video.start()
        self.video_playing = True

"""
账号详情对话框
用于单个账号的精细化管理：手动选课、单独执行、查看日志
"""
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton,
    QListWidget, QListWidgetItem, QLabel, QTextEdit, QMessageBox,
    QComboBox, QSpinBox, QSplitter, QWidget, QProgressBar
)
from core.api import WeLearnClient
from core.account_manager import Account
from ui.workers import LoginThread, CourseThread, UnitsThread, TimeStudyThread, StudyThread


class AccountDetailDialog(QDialog):
    """
    账号详情对话框
    提供单个账号的完整控制：登录、选课、参数设置、执行任务
    """
    
    # 信号：状态更新（用于通知主界面刷新）
    status_updated = pyqtSignal(str, str, str)  # username, status, progress
    
    def __init__(self, account: Account, parent=None):
        super().__init__(parent)
        self.account = account
        self.client = WeLearnClient()  # 每个账号独立的会话
        
        # 状态数据
        self.is_logged_in = False
        self.courses = []
        self.current_course = None
        self.current_units = []
        self.uid = ""
        self.classid = ""
        
        # 线程
        self.login_thread = None
        self.course_thread = None
        self.units_thread = None
        self.study_thread = None  # 刷作业/刷时长通用
        
        self.init_ui()
        self.setWindowTitle(f"账号管理 - {account.nickname or account.username}")
        self.setMinimumSize(700, 500)
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # ========== 账号信息 ==========
        info_layout = QHBoxLayout()
        info_layout.addWidget(QLabel(f"<b>用户名:</b> {self.account.username}"))
        info_layout.addWidget(QLabel(f"<b>昵称:</b> {self.account.nickname or '无'}"))
        self.status_label = QLabel(f"<b>状态:</b> {self.account.status}")
        info_layout.addWidget(self.status_label)
        info_layout.addStretch()
        
        self.login_btn = QPushButton("🔐 登录")
        self.login_btn.clicked.connect(self.do_login)
        info_layout.addWidget(self.login_btn)
        
        layout.addLayout(info_layout)
        
        # ========== 分割器：左侧课程选择 + 右侧日志 ==========
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧：课程和设置
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # 课程列表
        course_group = QGroupBox("课程列表")
        course_layout = QVBoxLayout(course_group)
        
        self.refresh_courses_btn = QPushButton("刷新课程")
        self.refresh_courses_btn.setEnabled(False)
        self.refresh_courses_btn.clicked.connect(self.refresh_courses)
        course_layout.addWidget(self.refresh_courses_btn)
        
        self.courses_list = QListWidget()
        self.courses_list.itemClicked.connect(self.on_course_selected)
        course_layout.addWidget(self.courses_list)
        
        left_layout.addWidget(course_group)
        
        # 任务设置
        settings_group = QGroupBox("任务设置")
        settings_layout = QVBoxLayout(settings_group)
        
        # 当前选中课程
        course_info_layout = QHBoxLayout()
        course_info_layout.addWidget(QLabel("目标课程:"))
        self.current_course_label = QLabel("未选择")
        self.current_course_label.setStyleSheet("color: #666; font-style: italic;")
        course_info_layout.addWidget(self.current_course_label)
        course_info_layout.addStretch()
        settings_layout.addLayout(course_info_layout)
        
        # 单元选择（复选框列表）
        unit_group = QGroupBox("选择单元")
        unit_group_layout = QVBoxLayout(unit_group)
        
        # 全选/取消全选按钮
        select_btn_layout = QHBoxLayout()
        self.select_all_btn = QPushButton("全选")
        self.select_none_btn = QPushButton("取消全选")
        self.select_all_btn.clicked.connect(self.select_all_units)
        self.select_none_btn.clicked.connect(self.select_none_units)
        select_btn_layout.addWidget(self.select_all_btn)
        select_btn_layout.addWidget(self.select_none_btn)
        select_btn_layout.addStretch()
        unit_group_layout.addLayout(select_btn_layout)
        
        # 单元列表
        self.unit_list = QListWidget()
        self.unit_list.setMaximumHeight(120)
        unit_group_layout.addWidget(self.unit_list)
        
        settings_layout.addWidget(unit_group)
        
        # === 模式选择 ===
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("模式:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["刷作业", "刷时长"])
        self.mode_combo.currentTextChanged.connect(self.on_mode_changed)
        mode_layout.addWidget(self.mode_combo)
        mode_layout.addStretch()
        settings_layout.addLayout(mode_layout)
        
        # === 刷作业设置 ===
        self.homework_widget = QWidget()
        homework_layout = QHBoxLayout(self.homework_widget)
        homework_layout.setContentsMargins(0, 0, 0, 0)
        homework_layout.addWidget(QLabel("正确率:"))
        self.accuracy_spin = QSpinBox()
        self.accuracy_spin.setRange(0, 100)
        self.accuracy_spin.setValue(100)
        self.accuracy_spin.setSuffix("%")
        homework_layout.addWidget(self.accuracy_spin)
        homework_layout.addStretch()
        settings_layout.addWidget(self.homework_widget)
        
        # === 刷时长设置 ===
        self.time_widget = QWidget()
        time_layout = QVBoxLayout(self.time_widget)
        time_layout.setContentsMargins(0, 0, 0, 0)
        
        # 第一行：单元总时长
        time_row1 = QHBoxLayout()
        time_row1.addWidget(QLabel("单元时长:"))
        self.time_spin = QSpinBox()
        self.time_spin.setRange(1, 300)
        self.time_spin.setValue(60)
        self.time_spin.setSuffix(" 分钟")
        self.time_spin.setToolTip("每个单元的总学习时长")
        time_row1.addWidget(self.time_spin)
        time_row1.addWidget(QLabel("  随机扰动:"))
        self.time_random_spin = QSpinBox()
        self.time_random_spin.setRange(0, 30)
        self.time_random_spin.setValue(5)
        self.time_random_spin.setSuffix(" 分钟")
        self.time_random_spin.setToolTip("随机增减范围，如设5则实际时长为 55~65 分钟")
        time_row1.addWidget(self.time_random_spin)
        time_row1.addStretch()
        time_layout.addLayout(time_row1)
        
        # 第二行：并发数
        time_row2 = QHBoxLayout()
        time_row2.addWidget(QLabel("并发数:"))
        self.concurrent_spin = QSpinBox()
        self.concurrent_spin.setRange(1, 100)
        self.concurrent_spin.setValue(10)
        self.concurrent_spin.setToolTip("同时刷多少个课程，越高刷得越快")
        time_row2.addWidget(self.concurrent_spin)
        time_row2.addStretch()
        time_layout.addLayout(time_row2)
        
        settings_layout.addWidget(self.time_widget)
        self.time_widget.hide()  # 默认显示刷作业
        
        left_layout.addWidget(settings_group)
        
        # 控制按钮
        control_layout = QHBoxLayout()
        self.start_btn = QPushButton("▶️ 开始刷作业")
        self.start_btn.setEnabled(False)
        self.start_btn.clicked.connect(self.start_study)
        self.stop_btn = QPushButton("⏹️ 停止")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_study)
        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.stop_btn)
        left_layout.addLayout(control_layout)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        left_layout.addWidget(self.progress_bar)
        
        splitter.addWidget(left_widget)
        
        # 右侧：日志
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        log_group = QGroupBox("运行日志")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("font-family: Consolas, monospace; font-size: 12px;")
        log_layout.addWidget(self.log_text)
        
        clear_log_btn = QPushButton("清空日志")
        clear_log_btn.clicked.connect(lambda: self.log_text.clear())
        log_layout.addWidget(clear_log_btn)
        
        right_layout.addWidget(log_group)
        splitter.addWidget(right_widget)
        
        splitter.setSizes([350, 350])
        layout.addWidget(splitter)
    
    def log(self, message: str):
        """添加日志"""
        self.log_text.append(message)
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )
    
    def update_status(self, status: str, progress: str = ""):
        """更新状态并通知主界面"""
        self.account.status = status
        self.account.progress = progress
        self.status_label.setText(f"<b>状态:</b> {status}")
        self.status_updated.emit(self.account.username, status, progress)
    
    def do_login(self):
        """执行登录"""
        self.login_btn.setEnabled(False)
        self.login_btn.setText("登录中...")
        self.log("正在登录...")
        self.update_status("登录中")
        
        self.login_thread = LoginThread(self.client, self.account.username, self.account.password)
        self.login_thread.login_result.connect(self.on_login_result)
        self.login_thread.start()
    
    def on_login_result(self, success: bool, message: str):
        """登录结果回调"""
        self.login_btn.setEnabled(True)
        
        if success:
            self.is_logged_in = True
            self.login_btn.setText("✅ 已登录")
            self.login_btn.setEnabled(False)
            self.refresh_courses_btn.setEnabled(True)
            self.log(f"✅ 登录成功")
            self.update_status("已登录")
            # 自动刷新课程
            self.refresh_courses()
        else:
            self.login_btn.setText("🔐 登录")
            self.log(f"❌ 登录失败: {message}")
            self.update_status("登录失败", message)
            QMessageBox.warning(self, "登录失败", message)
    
    def refresh_courses(self):
        """刷新课程列表"""
        self.refresh_courses_btn.setEnabled(False)
        self.refresh_courses_btn.setText("获取中...")
        self.log("正在获取课程列表...")
        
        self.course_thread = CourseThread(self.client)
        self.course_thread.course_result.connect(self.on_courses_result)
        self.course_thread.start()
    
    def on_courses_result(self, success: bool, courses: list, message: str):
        """课程列表结果回调"""
        self.refresh_courses_btn.setEnabled(True)
        self.refresh_courses_btn.setText("刷新课程")
        
        if success:
            self.courses = courses
            self.courses_list.clear()
            for course in courses:
                item = QListWidgetItem(f"{course['name']} (进度: {course['per']}%)")
                item.setData(Qt.ItemDataRole.UserRole, course)
                self.courses_list.addItem(item)
            self.log(f"✅ 获取到 {len(courses)} 门课程")
        else:
            self.log(f"❌ 获取课程失败: {message}")
            QMessageBox.warning(self, "失败", message)
    
    def on_course_selected(self, item: QListWidgetItem):
        """选择课程"""
        course = item.data(Qt.ItemDataRole.UserRole)
        self.current_course = course
        self.current_course_label.setText(course['name'])
        self.log(f"选择课程: {course['name']}")
        
        # 获取单元信息
        self.get_units()
    
    def get_units(self):
        """获取单元信息"""
        if not self.current_course:
            return
        
        self.unit_list.clear()
        self.start_btn.setEnabled(False)
        self.log("正在获取单元信息...")
        
        self.units_thread = UnitsThread(self.client, self.current_course['cid'])
        self.units_thread.units_result.connect(self.on_units_result)
        self.units_thread.start()
    
    def on_units_result(self, success: bool, units_data: list, message: str):
        """单元信息结果回调"""
        if success and units_data:
            data = units_data[0]
            self.uid = data['uid']
            self.classid = data['classid']
            self.current_units = data['units']
            
            # 填充复选框列表
            self.unit_list.clear()
            for i, unit in enumerate(self.current_units):
                unit_name = unit.get('name', f'单元 {i+1}')
                item = QListWidgetItem(f"单元 {i+1}: {unit_name}")
                item.setCheckState(Qt.CheckState.Checked)  # 默认全选
                item.setData(Qt.ItemDataRole.UserRole, i)  # 存储索引
                self.unit_list.addItem(item)
            
            self.start_btn.setEnabled(True)
            self.log(f"✅ 获取到 {len(self.current_units)} 个单元")
        else:
            self.log(f"❌ 获取单元失败: {message}")
    
    def select_all_units(self):
        """全选单元"""
        for i in range(self.unit_list.count()):
            self.unit_list.item(i).setCheckState(Qt.CheckState.Checked)
    
    def select_none_units(self):
        """取消全选单元"""
        for i in range(self.unit_list.count()):
            self.unit_list.item(i).setCheckState(Qt.CheckState.Unchecked)
    
    def on_mode_changed(self, mode: str):
        """模式切换"""
        if mode == "刷作业":
            self.homework_widget.show()
            self.time_widget.hide()
            self.start_btn.setText("▶️ 开始刷作业")
        else:
            self.homework_widget.hide()
            self.time_widget.show()
            self.start_btn.setText("▶️ 开始刷时长")
    
    def start_study(self):
        """开始任务"""
        if not self.current_course:
            QMessageBox.warning(self, "警告", "请先选择课程")
            return
        
        # 获取选中的单元
        units_to_process = []
        for i in range(self.unit_list.count()):
            item = self.unit_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                units_to_process.append(item.data(Qt.ItemDataRole.UserRole))
        
        if not units_to_process:
            QMessageBox.warning(self, "警告", "请至少选择一个单元")
            return
        
        mode = self.mode_combo.currentText()
        
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # 不确定进度
        
        if mode == "刷作业":
            accuracy_config = self.accuracy_spin.value()
            self.log(f"开始刷作业 (已选 {len(units_to_process)} 个单元)...")
            self.update_status("运行中")
            
            self.study_thread = StudyThread(
                self.client,
                self.current_course['cid'],
                self.uid,
                self.classid,
                units_to_process,  # 传入单元列表
                accuracy_config,
                self.current_units
            )
        else:
            total_minutes = self.time_spin.value()
            random_range = self.time_random_spin.value()
            concurrent = self.concurrent_spin.value()
            self.log(f"开始刷时长 (已选 {len(units_to_process)} 个单元, 每单元 {total_minutes}±{random_range} 分钟, {concurrent} 并发)...")
            self.update_status("运行中")
            
            self.study_thread = TimeStudyThread(
                self.client,
                self.current_course['cid'],
                self.uid,
                self.classid,
                units_to_process,  # 传入单元列表
                total_minutes,     # 每单元总分钟数
                random_range,      # 随机扰动分钟数
                self.current_units,
                max_concurrent=concurrent
            )
        
        self.study_thread.progress_update.connect(self.on_progress_update)
        self.study_thread.study_finished.connect(self.on_study_finished)
        self.study_thread.start()
    
    def stop_study(self):
        """停止任务"""
        if self.study_thread and self.study_thread.isRunning():
            self.study_thread.quit()
            self.study_thread.wait(2000)
            if self.study_thread.isRunning():
                self.study_thread.terminate()
        
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.log("⏹️ 任务已停止")
        self.update_status("已停止")
    
    def on_progress_update(self, status: str, message: str):
        """进度更新回调"""
        self.log(message)
        self.update_status("运行中", status)
    
    def on_study_finished(self, result: dict):
        """任务完成回调"""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        
        mode = self.mode_combo.currentText()
        if mode == "刷作业":
            msg = f"步骤1成功: {result.get('way1_succeed', 0)}, 失败: {result.get('way1_failed', 0)}\n"
            msg += f"步骤2成功: {result.get('way2_succeed', 0)}, 失败: {result.get('way2_failed', 0)}"
            self.log(f"✅ 刷作业完成！\n{msg}")
        else:
            self.log("✅ 刷时长完成！")
        
        self.update_status("已完成")
        QMessageBox.information(self, "完成", "任务已完成！")
    
    def closeEvent(self, event):
        """关闭窗口时清理线程"""
        # 先发送停止信号
        if self.study_thread:
            if hasattr(self.study_thread, 'stop'):
                self.study_thread.stop()
            if self.study_thread.isRunning():
                self.study_thread.quit()
                self.study_thread.wait(3000)
                if self.study_thread.isRunning():
                    self.study_thread.terminate()
                    self.study_thread.wait(1000)
        event.accept()

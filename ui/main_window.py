"""
WeLearn 自动学习工具 - 主窗口
多用户管理中心
"""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QMainWindow, QVBoxLayout, QWidget, QMenuBar, QMenu, QAction,
    QMessageBox, QStatusBar
)

from ui.account_view import AccountView
from ui.account_detail import AccountDetailDialog
from core.account_manager import Account


class WeLearnUI(QMainWindow):
    """
    主窗口
    现在作为多用户管理中心
    """
    
    def __init__(self):
        super().__init__()
        self.detail_dialogs = {}  # 存储打开的详情对话框
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("WeLearn 自动学习工具 - 多用户版")
        self.setGeometry(100, 100, 900, 600)
        self.setMinimumSize(800, 500)
        
        # 设置样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ddd;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QPushButton {
                background-color: #4CAF50;
                border: none;
                color: white;
                padding: 8px 16px;
                font-size: 13px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
            QTableWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
            }
            QTableWidget::item:selected {
                background-color: #e3f2fd;
                color: black;
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                padding: 8px;
                border: none;
                border-bottom: 1px solid #ddd;
                font-weight: bold;
            }
        """)
        
        # ========== 菜单栏 ==========
        self.create_menu_bar()
        
        # ========== 中心控件：账号视图 ==========
        self.account_view = AccountView()
        self.account_view.open_detail_requested.connect(self.open_account_detail)
        self.setCentralWidget(self.account_view)
        
        # ========== 状态栏 ==========
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪 - 添加账号开始使用")
    
    def create_menu_bar(self):
        """创建菜单栏"""
        menu_bar = self.menuBar()
        
        # 文件菜单
        file_menu = menu_bar.addMenu("文件(&F)")
        
        import_action = QAction("导入账号(&I)", self)
        import_action.setShortcut("Ctrl+I")
        import_action.triggered.connect(lambda: self.account_view.import_accounts())
        file_menu.addAction(import_action)
        
        export_action = QAction("导出账号(&E)", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(lambda: self.account_view.export_accounts())
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("退出(&X)", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 帮助菜单
        help_menu = menu_bar.addMenu("帮助(&H)")
        
        about_action = QAction("关于(&A)", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
        github_action = QAction("GitHub 项目", self)
        github_action.triggered.connect(self.open_github)
        help_menu.addAction(github_action)
    
    def open_account_detail(self, account: Account):
        """打开账号详情对话框"""
        username = account.username  # 先保存用户名
        
        # 如果已经打开了该账号的详情，则激活它
        if username in self.detail_dialogs:
            dialog = self.detail_dialogs[username]
            if dialog.isVisible():
                dialog.raise_()
                dialog.activateWindow()
                return
            else:
                # 对话框已关闭但未从字典移除，先清理
                del self.detail_dialogs[username]
        
        # 创建新的详情对话框
        dialog = AccountDetailDialog(account, self)
        dialog.status_updated.connect(self.on_account_status_updated)
        # 使用默认参数捕获 username 的值，而不是引用
        dialog.finished.connect(lambda result, u=username: self.on_detail_closed(u))
        
        self.detail_dialogs[username] = dialog
        dialog.show()
        self.status_bar.showMessage(f"已打开账号详情: {username}")
    
    def on_account_status_updated(self, username: str, status: str, progress: str):
        """账号状态更新回调"""
        self.account_view.update_account_status(username, status, progress)
    
    def on_detail_closed(self, username: str):
        """详情对话框关闭回调"""
        if username in self.detail_dialogs:
            del self.detail_dialogs[username]
        self.account_view.refresh_table()
    
    def show_about(self):
        """显示关于对话框"""
        QMessageBox.about(
            self,
            "关于 WeLearn 自动学习工具",
            """
            <h3>WeLearn 自动学习工具</h3>
            <p>版本: 2.0 (多用户版)</p>
            <p>作者: jhl337</p>
            <hr>
            <p>本人是一位来自黑大的苦逼学生，因不满校内各种付费代刷课，所以制作了这款软件。</p>
            <p><b>软件仅供学习参考使用，永久免费禁止倒卖</b></p>
            <p>禁止使用软件进行任何代刷牟利，以此造成的任何问题本人不负责任。</p>
            <hr>
            <p>有任何问题欢迎提交 Issue 多多交流</p>
            """
        )
    
    def open_github(self):
        """打开 GitHub 项目页面"""
        import webbrowser
        webbrowser.open("https://github.com/jhl337/Auto_WeLearn/")
    
    def closeEvent(self, event):
        """关闭窗口时清理"""
        # 关闭所有详情对话框
        for dialog in list(self.detail_dialogs.values()):
            dialog.close()
        self.detail_dialogs.clear()
        
        # 强制退出应用
        from PyQt5.QtWidgets import QApplication
        QApplication.quit()
        event.accept()

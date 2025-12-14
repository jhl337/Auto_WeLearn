import sys
import traceback
from PyQt5.QtWidgets import QApplication, QMessageBox
from ui.main_window import WeLearnUI


def exception_hook(exctype, value, tb):
    """全局异常处理，防止程序闪退"""
    error_msg = ''.join(traceback.format_exception(exctype, value, tb))
    print(f"未捕获的异常:\n{error_msg}", file=sys.stderr)
    
    # 显示错误对话框
    msg_box = QMessageBox()
    msg_box.setIcon(QMessageBox.Icon.Critical)
    msg_box.setWindowTitle("程序错误")
    msg_box.setText("程序发生错误，但不会退出")
    msg_box.setDetailedText(error_msg)
    msg_box.exec_()


def main():
    # 安装全局异常处理
    sys.excepthook = exception_hook
    
    app = QApplication(sys.argv)
    window = WeLearnUI()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()

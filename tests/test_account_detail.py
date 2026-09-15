import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QListWidgetItem

from core.account_manager import Account
import ui.account_detail as account_detail


class FakeSignal:
    def connect(self, callback):
        self.callback = callback


class FakeStudyThread:
    instances = []

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.progress_update = FakeSignal()
        self.study_finished = FakeSignal()
        self.__class__.instances.append(self)

    def start(self):
        pass

    def isRunning(self):
        return False


class AccountDetailDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        FakeStudyThread.instances.clear()
        self.original_study_thread = account_detail.StudyThread
        account_detail.StudyThread = FakeStudyThread
        self.dialog = account_detail.AccountDetailDialog(
            Account("demo", "password")
        )
        self.dialog.show()
        self.app.processEvents()

    def tearDown(self):
        self.dialog.close()
        account_detail.StudyThread = self.original_study_thread

    def test_random_accuracy_range_is_passed_to_study_thread(self):
        self.dialog.accuracy_mode_combo.setCurrentText("随机正确率")
        self.dialog.random_accuracy_range = (72, 88)
        self.dialog.random_accuracy_label.setText("72%-88%")

        self.dialog.current_course = {"cid": "course"}
        self.dialog.uid = "uid"
        self.dialog.classid = "class"
        item = QListWidgetItem("unit")
        item.setCheckState(2)
        item.setData(Qt.ItemDataRole.UserRole, 0)
        self.dialog.unit_list.addItem(item)

        self.dialog.start_study()

        self.assertEqual(len(FakeStudyThread.instances), 1)
        self.assertEqual(FakeStudyThread.instances[0].args[5], (72, 88))

    def test_random_accuracy_controls_are_hidden_in_fixed_mode(self):
        self.assertTrue(self.dialog.fixed_accuracy_spin.isVisible())
        self.assertFalse(self.dialog.random_accuracy_btn.isVisible())

        self.dialog.accuracy_mode_combo.setCurrentText("随机正确率")

        self.assertFalse(self.dialog.fixed_accuracy_spin.isVisible())
        self.assertTrue(self.dialog.random_accuracy_btn.isVisible())
        self.assertTrue(self.dialog.random_accuracy_label.isVisible())

    def test_accuracy_range_keeps_minimum_below_or_equal_to_maximum(self):
        dialog = account_detail.AccuracyRangeDialog()

        dialog.min_accuracy.setValue(85)
        self.assertEqual(dialog.max_accuracy.minimum(), 85)

        dialog.max_accuracy.setValue(80)
        self.assertEqual(dialog.max_accuracy.value(), 85)
        self.assertEqual(dialog.get_values(), (85, 85))

        dialog.close()


if __name__ == "__main__":
    unittest.main()

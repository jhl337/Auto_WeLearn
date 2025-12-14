from PyQt5.QtCore import QThread, pyqtSignal
import random
from core.api import WeLearnClient

class LoginThread(QThread):
    """登录线程"""

    login_result = pyqtSignal(bool, str)

    def __init__(self, client: WeLearnClient, username, password):
        super().__init__()
        self.client = client
        self.username = username
        self.password = password

    def run(self):
        success, message = self.client.login(self.username, self.password)
        self.login_result.emit(success, message)


class CourseThread(QThread):
    """获取课程线程"""

    course_result = pyqtSignal(bool, list, str)

    def __init__(self, client: WeLearnClient):
        super().__init__()
        self.client = client

    def run(self):
        success, courses, message = self.client.get_courses()
        self.course_result.emit(success, courses, message)


class UnitsThread(QThread):
    """获取单元线程"""

    units_result = pyqtSignal(bool, list, str)

    def __init__(self, client: WeLearnClient, cid):
        super().__init__()
        self.client = client
        self.cid = cid

    def run(self):
        success, data, message = self.client.get_course_info(self.cid)
        if success:
            self.units_result.emit(True, [data], message)
        else:
            self.units_result.emit(False, [], message)


class StudyThread(QThread):
    """学习线程"""

    progress_update = pyqtSignal(str, str)
    study_finished = pyqtSignal(dict)

    def __init__(
        self, client: WeLearnClient, cid, uid, classid, unit_idx, accuracy_config, current_units
    ):
        super().__init__()
        self.client = client
        self.cid = cid
        self.uid = uid
        self.classid = classid
        self.unit_idx = unit_idx
        self.accuracy_config = accuracy_config
        self.current_units = current_units
        self._stop_flag = False

    def process_unit(self, unit_index):
        way1_succeed, way1_failed, way2_succeed, way2_failed = 0, 0, 0, 0

        try:
            success, leaves, message = self.client.get_sco_leaves(
                self.cid, self.uid, self.classid, unit_index
            )
            if not success:
                 self.progress_update.emit("error", f"获取单元详情失败: {message}")
                 return 0, 0, 0, 0

            for course in leaves:
                if self._stop_flag:
                    break
                    
                course_location = course.get("location", "未知课程")

                if course.get("isvisible") == "false":
                    self.progress_update.emit("skip", f"[跳过] {course_location}")
                    continue

                if "未" in course.get("iscomplete", ""):
                    self.progress_update.emit("start", f"[进行] {course_location}")

                    if isinstance(self.accuracy_config, tuple):
                        accuracy = str(
                            random.randint(
                                self.accuracy_config[0], self.accuracy_config[1]
                            )
                        )
                    else:
                        accuracy = str(self.accuracy_config)

                    w1_s, w1_f, w2_s, w2_f = self.client.submit_course_progress(
                        self.cid, self.uid, self.classid, course["id"], accuracy
                    )
                    
                    way1_succeed += w1_s
                    way1_failed += w1_f
                    way2_succeed += w2_s
                    way2_failed += w2_f

                    status_msg = f"[完成] {course_location} - 正确率: {accuracy}%"
                    status_msg += " (步骤1:成功)" if w1_s else " (步骤1:失败)"
                    status_msg += " (步骤2:成功)" if w2_s else " (步骤2:失败)"

                    self.progress_update.emit("finish", status_msg)
                else:
                    self.progress_update.emit(
                        "completed", f"[已完成] {course_location}"
                    )

        except Exception as e:
            self.progress_update.emit(
                "error", f"处理单元 {unit_index + 1} 时发生错误: {str(e)}"
            )

        return way1_succeed, way1_failed, way2_succeed, way2_failed

    def run(self):
        total_way1_succeed, total_way1_failed = 0, 0
        total_way2_succeed, total_way2_failed = 0, 0
        self._stop_flag = False

        try:
            # unit_idx 现在是一个列表
            unit_indices = self.unit_idx if isinstance(self.unit_idx, list) else [self.unit_idx]
            
            for unit_index in unit_indices:
                if self._stop_flag:
                    break
                self.progress_update.emit(
                    "unit_start", f"\n=== 开始处理第 {unit_index + 1} 单元 ==="
                )
                result = self.process_unit(unit_index)
                total_way1_succeed += result[0]
                total_way1_failed += result[1]
                total_way2_succeed += result[2]
                total_way2_failed += result[3]
                self.progress_update.emit(
                    "unit_finish", f"=== 第 {unit_index + 1} 单元处理完成 ===\n"
                )

            result = {
                "way1_succeed": total_way1_succeed,
                "way1_failed": total_way1_failed,
                "way2_succeed": total_way2_succeed,
                "way2_failed": total_way2_failed,
            }
            self.study_finished.emit(result)

        except Exception as e:
            self.progress_update.emit("error", f"学习过程中发生错误: {str(e)}")
    
    def stop(self):
        """停止学习"""
        self._stop_flag = True


class TimeStudyThread(QThread):
    """刷时长线程 - 支持并发刷多个课程，按单元总时长分配"""

    progress_update = pyqtSignal(str, str)
    study_finished = pyqtSignal(dict)

    def __init__(
        self, client: WeLearnClient, cid, uid, classid, unit_idx, 
        total_minutes, random_range, current_units, max_concurrent=10
    ):
        super().__init__()
        self.client = client
        self.cid = cid
        self.uid = uid
        self.classid = classid
        self.unit_idx = unit_idx
        self.total_minutes = total_minutes  # 每单元总分钟数
        self.random_range = random_range    # 随机扰动分钟数
        self.current_units = current_units
        self.max_concurrent = max_concurrent
        self._stop_flag = False
        self.per_course_time = 0  # 每课程秒数，在处理单元时计算

    def calculate_unit_time(self, course_count):
        """计算单元总时间和每课程时间"""
        # 添加随机扰动
        actual_minutes = self.total_minutes + random.randint(-self.random_range, self.random_range)
        actual_minutes = max(1, actual_minutes)  # 确保至少1分钟
        total_seconds = actual_minutes * 60
        
        # 平分到每个课程
        self.per_course_time = total_seconds // course_count if course_count > 0 else total_seconds
        return actual_minutes, self.per_course_time

    def study_single_course(self, chapter):
        """刷单个课程的时长"""
        if self._stop_flag:
            return False
        
        course_location = chapter.get("location", "未知课程")
        learning_time = self.per_course_time
        
        self.progress_update.emit(
            "start", f"[并发刷时长] {course_location} - {learning_time}秒"
        )
        
        success = self.client.simulate_time(self.cid, self.uid, chapter["id"], learning_time)
        
        if success:
            self.progress_update.emit(
                "finish", f"[完成] {course_location} - {learning_time}秒"
            )
        else:
            self.progress_update.emit("error", f"[失败] {course_location}")
        
        return success

    def process_unit_concurrent(self, unit_index):
        """并发处理一个单元的所有课程"""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        success_count, fail_count = 0, 0

        try:
            success, leaves, message = self.client.get_sco_leaves(
                self.cid, self.uid, self.classid, unit_index
            )
            if not success:
                self.progress_update.emit("error", f"获取单元详情失败: {message}")
                return 0, 0

            # 过滤可见的课程
            visible_chapters = [
                ch for ch in leaves 
                if ch.get("isvisible") != "false"
            ]
            
            if not visible_chapters:
                self.progress_update.emit("skip", "该单元没有可刷的课程")
                return 0, 0
            
            # 计算每课程时间
            actual_minutes, per_course_seconds = self.calculate_unit_time(len(visible_chapters))
            
            self.progress_update.emit(
                "info", f"发现 {len(visible_chapters)} 个课程，单元总时长 {actual_minutes} 分钟，每课程 {per_course_seconds} 秒，{self.max_concurrent} 并发"
            )

            # 使用线程池并发刷
            with ThreadPoolExecutor(max_workers=self.max_concurrent) as executor:
                futures = {
                    executor.submit(self.study_single_course, ch): ch 
                    for ch in visible_chapters
                }
                
                for future in as_completed(futures):
                    if self._stop_flag:
                        executor.shutdown(wait=False, cancel_futures=True)
                        break
                    
                    if future.result():
                        success_count += 1
                    else:
                        fail_count += 1

        except Exception as e:
            self.progress_update.emit(
                "error", f"处理单元 {unit_index + 1} 时发生错误: {str(e)}"
            )

        return success_count, fail_count

    def run(self):
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        total_success, total_fail = 0, 0
        self._stop_flag = False

        try:
            # unit_idx 现在是一个列表
            unit_indices = self.unit_idx if isinstance(self.unit_idx, list) else [self.unit_idx]
            
            # 第一步：收集所有单元的所有课程
            all_chapters = []
            self.progress_update.emit("info", f"正在收集 {len(unit_indices)} 个单元的课程信息...")
            
            for unit_index in unit_indices:
                if self._stop_flag:
                    break
                    
                success, leaves, message = self.client.get_sco_leaves(
                    self.cid, self.uid, self.classid, unit_index
                )
                
                if success:
                    visible = [ch for ch in leaves if ch.get("isvisible") != "false"]
                    all_chapters.extend(visible)
                    self.progress_update.emit("info", f"单元 {unit_index + 1}: 发现 {len(visible)} 个课程")
                else:
                    self.progress_update.emit("error", f"单元 {unit_index + 1}: 获取失败 - {message}")
            
            if not all_chapters:
                self.progress_update.emit("error", "没有找到可刷的课程")
                return
            
            # 第二步：计算每课程时间
            actual_minutes, per_course_seconds = self.calculate_unit_time(len(all_chapters))
            self.progress_update.emit(
                "info", 
                f"总共 {len(all_chapters)} 个课程，总时长 {actual_minutes} 分钟，每课程 {per_course_seconds} 秒"
            )
            self.progress_update.emit(
                "info", 
                f"开始并发刷时长 (并发数: {self.max_concurrent})..."
            )
            
            # 第三步：并发处理所有课程
            with ThreadPoolExecutor(max_workers=self.max_concurrent) as executor:
                futures = {
                    executor.submit(self.study_single_course, ch): ch 
                    for ch in all_chapters
                }
                
                for future in as_completed(futures):
                    if self._stop_flag:
                        executor.shutdown(wait=False, cancel_futures=True)
                        break
                    
                    if future.result():
                        total_success += 1
                    else:
                        total_fail += 1

            result = {
                "way1_succeed": total_success,
                "way1_failed": total_fail,
                "way2_succeed": total_success,
                "way2_failed": total_fail,
            }
            self.study_finished.emit(result)

        except Exception as e:
            self.progress_update.emit("error", f"刷时长过程中发生错误: {str(e)}")
    
    def stop(self):
        """停止刷时长"""
        self._stop_flag = True


"""
批量任务管理器
管理多个账号的并发刷时长任务
"""
from queue import Queue
from threading import Thread, Lock, current_thread
from typing import Dict, Callable, Optional
from core.account_manager import Account


class BatchTaskManager:
    """批量任务管理器"""
    
    def __init__(self, max_workers: int = 4):
        """
        初始化批量任务管理器
        
        Args:
            max_workers: 最大并发worker数量
        """
        self.max_workers = max_workers
        self.task_queue = Queue()
        self.workers = []
        self.running = False
        self.lock = Lock()
        
        # 回调函数
        self.on_task_start: Optional[Callable] = None
        self.on_task_progress: Optional[Callable] = None
        self.on_task_complete: Optional[Callable] = None
        self.on_all_complete: Optional[Callable] = None
    
    def add_task(self, account: Account, task_func: Callable, *args, **kwargs):
        """
        添加任务到队列
        
        Args:
            account: 账号对象
            task_func: 要执行的任务函数
            *args, **kwargs: 传递给任务函数的参数
        """
        self.task_queue.put((account, task_func, args, kwargs))
    
    def start(self):
        """启动批量任务"""
        if self.running:
            return
        
        self.running = True
        
        # 创建worker线程
        for i in range(self.max_workers):
            worker = Thread(target=self._worker, name=f"Worker-{i+1}", daemon=True)
            worker.start()
            self.workers.append(worker)
    
    def stop(self):
        """停止所有任务"""
        self.running = False
        
        # 清空队列
        while not self.task_queue.empty():
            try:
                self.task_queue.get_nowait()
            except:
                break
        
        # 等待所有worker完成
        for worker in self.workers:
            if worker.is_alive():
                worker.join(timeout=1)
        
        self.workers.clear()
    
    def _worker(self):
        """Worker线程函数"""
        while self.running:
            try:
                # 从队列获取任务（带超时）
                task = self.task_queue.get(timeout=1)
                if task is None:
                    break
                
                account, task_func, args, kwargs = task
                
                # 通知任务开始
                if self.on_task_start:
                    self.on_task_start(account)
                
                try:
                    # 执行任务
                    task_func(account, *args, **kwargs)
                    
                    # 通知任务完成
                    if self.on_task_complete:
                        self.on_task_complete(account, True, "")
                
                except Exception as e:
                    # 通知任务失败
                    if self.on_task_complete:
                        self.on_task_complete(account, False, str(e))
                
                finally:
                    self.task_queue.task_done()
            
            except:
                # 超时或其他异常，继续循环
                continue
        
        # Worker退出时检查是否所有任务完成
        with self.lock:
            if self.task_queue.empty() and all(not w.is_alive() or w == current_thread() for w in self.workers):
                if self.on_all_complete:
                    self.on_all_complete()
    
    def is_running(self) -> bool:
        """检查是否正在运行"""
        return self.running and any(w.is_alive() for w in self.workers)
    
    def get_pending_count(self) -> int:
        """获取待处理任务数"""
        return self.task_queue.qsize()
    
    def wait_completion(self, timeout: Optional[float] = None):
        """等待所有任务完成"""
        self.task_queue.join()
        
        for worker in self.workers:
            worker.join(timeout=timeout)

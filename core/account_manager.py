"""
账号管理器
管理多个WeLearn账号的增删改查和导入导出
"""
import json
import csv
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict


@dataclass
class Account:
    """账号数据结构"""
    username: str
    password: str
    nickname: str = ""  # 可选的昵称
    status: str = "待处理"  # 待处理/登录中/运行中/已完成/失败
    progress: str = ""  # 进度信息
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @staticmethod
    def from_dict(data: dict) -> 'Account':
        return Account(**data)


class AccountManager:
    """账号管理器"""
    
    def __init__(self):
        self.accounts: List[Account] = []
    
    def add_account(self, username: str, password: str, nickname: str = "") -> bool:
        """添加账号"""
        # 检查是否已存在
        if any(acc.username == username for acc in self.accounts):
            return False
        
        self.accounts.append(Account(username, password, nickname))
        return True
    
    def remove_account(self, username: str) -> bool:
        """删除账号"""
        for i, acc in enumerate(self.accounts):
            if acc.username == username:
                self.accounts.pop(i)
                return True
        return False
    
    def clear_accounts(self):
        """清空所有账号"""
        self.accounts.clear()
    
    def get_account(self, username: str) -> Optional[Account]:
        """获取账号"""
        for acc in self.accounts:
            if acc.username == username:
                return acc
        return None
    
    def get_all_accounts(self) -> List[Account]:
        """获取所有账号"""
        return self.accounts.copy()
    
    def update_status(self, username: str, status: str, progress: str = ""):
        """更新账号状态"""
        acc = self.get_account(username)
        if acc:
            acc.status = status
            acc.progress = progress
    
    def import_from_file(self, filepath: str) -> tuple[int, str]:
        """
        从文件导入账号
        支持格式：
        - CSV: username,password,nickname
        - TXT: username,password 每行一个
        
        返回: (成功导入数量, 错误信息)
        """
        try:
            imported_count = 0
            
            if filepath.endswith('.csv'):
                with open(filepath, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    for row in reader:
                        if len(row) >= 2:
                            username = row[0].strip()
                            password = row[1].strip()
                            nickname = row[2].strip() if len(row) > 2 else ""
                            
                            if self.add_account(username, password, nickname):
                                imported_count += 1
            
            elif filepath.endswith('.txt'):
                with open(filepath, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                        
                        parts = line.split(',')
                        if len(parts) >= 2:
                            username = parts[0].strip()
                            password = parts[1].strip()
                            nickname = parts[2].strip() if len(parts) > 2 else ""
                            
                            if self.add_account(username, password, nickname):
                                imported_count += 1
            
            else:
                return 0, "不支持的文件格式，请使用 .csv 或 .txt"
            
            return imported_count, ""
        
        except Exception as e:
            return 0, f"导入失败: {str(e)}"
    
    def export_to_file(self, filepath: str) -> tuple[bool, str]:
        """
        导出账号到文件
        
        返回: (是否成功, 错误信息)
        """
        try:
            if filepath.endswith('.csv'):
                with open(filepath, 'w', encoding='utf-8', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['用户名', '密码', '昵称'])
                    for acc in self.accounts:
                        writer.writerow([acc.username, acc.password, acc.nickname])
            
            elif filepath.endswith('.txt'):
                with open(filepath, 'w', encoding='utf-8') as f:
                    for acc in self.accounts:
                        f.write(f"{acc.username},{acc.password},{acc.nickname}\n")
            
            else:
                return False, "不支持的文件格式，请使用 .csv 或 .txt"
            
            return True, ""
        
        except Exception as e:
            return False, f"导出失败: {str(e)}"
    
    def reset_all_status(self):
        """重置所有账号状态"""
        for acc in self.accounts:
            acc.status = "待处理"
            acc.progress = ""
    
    def get_account_count(self) -> int:
        """获取账号数量"""
        return len(self.accounts)

# WeLearn 自动学习工具

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![PyQt5](https://img.shields.io/badge/PyQt5-5.15+-green.svg)](https://pypi.org/project/PyQt5/)
[![License](https://img.shields.io/badge/License-Free-orange.svg)]()

## 项目简介

本人是一位来自黑大的苦逼学生，因不满校内各种付费代刷课，所以制作了这款软件。

这是一个基于 Python 和 PyQt5 开发的 WeLearn 平台自动学习工具，支持自动完成课程作业和刷学习时长功能。

通过直接发送提交包完成每节课的学习，后续还会写自动刷知到、学习通等软件。

## 免责声明

**重要声明**：

- 软件仅供学习参考使用，永久免费禁止倒卖
- 禁止使用软件进行任何代刷牟利行为
- 使用本软件造成的任何问题本人不负责任
- 请合理使用，遵守学校相关规定

## 安装与运行

### 环境要求

- Python 3.12+
- Windows / macOS / Linux

### 方式一：使用 uv（推荐）

[uv](https://github.com/astral-sh/uv) 是一个超快的 Python 包管理器，比 pip 快 10-100 倍。

```bash
# 安装 uv（如果还没有）
# Windows (PowerShell)
irm https://astral.sh/uv/install.ps1 | iex
# 或使用 pip
pip install uv

# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# 克隆项目
git clone https://github.com/jhl337/Auto_WeLearn.git
cd Auto_WeLearn

# 安装依赖并运行
uv sync
uv run python main.py
```

### 方式二：使用 pip

```bash
# 克隆项目
git clone https://github.com/jhl337/Auto_WeLearn.git
cd Auto_WeLearn

# 创建虚拟环境（推荐）
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
# 或使用 pyproject.toml
pip install -e .

# 运行程序
python main.py
```

## 功能特点

### 刷作业模式

| 功能         | 描述                           |
| ------------ | ------------------------------ |
| 自动完成作业 | 自动提交课程作业答案           |
| 正确率设置   | 支持固定正确率和随机正确率区间 |
| 单元选择     | 可选择特定单元或全部单元       |
| 进度显示     | 实时显示学习进度和统计信息     |

### 刷时长模式

| 功能       | 描述                             |
| ---------- | -------------------------------- |
| 自动刷时长 | 自动增加课程学习时长             |
| 时长设置   | 支持固定时长和随机时长区间       |
| 心跳模拟   | 发送心跳包模拟真实学习行为       |
| 并发控制   | 可设置并发数量，多课程同时刷时长 |

### 多账号管理

| 功能       | 描述                              |
| ---------- | --------------------------------- |
| 多账号支持 | 同时管理多个 WeLearn 账号         |
| 导入/导出  | 支持 CSV/TXT 格式批量导入导出账号 |
| 独立窗口   | 每个账号独立的详情窗口，互不干扰  |
| 状态追踪   | 实时显示每个账号的运行状态和进度  |
| 批量操作   | 支持批量刷时长任务                |

## 项目结构

```
Auto_WeLearn/
├── main.py                  # 程序入口（多账号版）
├── WeLearn.py               # 原始单文件版本（保留兼容）
│
├── core/                    # 核心功能模块
│   ├── __init__.py
│   ├── api.py               # WeLearn API 封装（登录、获取课程、提交进度）
│   ├── crypto.py            # 密码加密算法（DES 加密）
│   ├── account_manager.py   # 账号管理（增删改查、导入导出）
│   └── batch_manager.py     # 批量任务管理器（并发控制、任务调度）
│
├── ui/                      # 用户界面模块
│   ├── __init__.py
│   ├── main_window.py       # 主窗口（菜单栏、多账号管理中心）
│   ├── account_view.py      # 账号列表视图（账号表格、添加/删除）
│   ├── account_detail.py    # 账号详情对话框（选课、参数设置、执行任务）
│   └── workers.py           # 后台工作线程（登录、获取课程、刷作业、刷时长）
│
├── pyproject.toml           # 项目配置（uv/pip 依赖）
├── requirements.txt         # pip 依赖列表
├── uv.lock                  # uv 依赖锁定文件
├── .gitignore               # Git 忽略规则
└── README.md                # 项目说明
```

## 使用说明

### 多账号版

1. `uv`安装用户使用`uv run main.py`运行程序, `pip`安装用户使用 `python main.py` 运行程序
2. 点击「添加账号」输入 WeLearn 账号密码
3. 或使用「文件 → 导入账号」批量导入（支持 CSV/TXT）
4. 双击账号打开详情窗口
5. 在详情窗口中：
   - 点击「登录」登录账号
   - 选择课程，加载单元列表
   - 勾选要处理的单元
   - 设置刷作业正确率或刷时长参数
   - 点击「开始」执行任务

### 账号导入格式

**CSV 格式**：

```csv
用户名,密码,昵称
student1,password1,张三
student2,password2,李四
```

**TXT 格式**：

```
student1,password1,昵称1
student2,password2
# 以 # 开头的行会被忽略
```

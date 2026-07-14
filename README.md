# 📚 GetScore — 成绩查询与监控系统

自动监控g1x2n3u4教务系统成绩变化，登录 → 抓取 → 解析 → 存储 → 通知的全流程自动化工具。

## 功能特性

- 🔐 **自动登录** — CAS 统一认证 + RSA 密码加密，会话过期自动重登
- 🔄 **定时轮询** — 可配置的间隔轮询，后台持续监控成绩变化
- 📊 **差异检测** — 新增/更新的成绩自动识别，精确到每门课程
- ⚠️ **挂科提醒** — 自动判断挂科、缺考、作弊等异常状态
- 🔔 **消息推送** — 成绩变化时通过 [Server酱 Turbo](https://sct.ftqq.com/) 推送微信通知
- 💾 **本地存储** — SQLite 持久化存储所有成绩数据，支持历史回溯
- 🏷️ **学期过滤** — 支持按学期查询，灵活控制查询范围

## 快速开始

### 环境要求

- Python 3.8+
- [uv](https://docs.astral.sh/uv/)（推荐）或 pip

### 安装与配置

```bash
# 1. 克隆项目
git clone <repo-url> && cd GetScore

# 2. 初始化环境并安装依赖
bash scripts/setup.sh

# 3. 配置账号信息
cp .env.example .env
# 编辑 .env，填入你的学号和密码
```

`.env` 配置说明：

```ini
# CAS 登录信息（必填）
STUDENT_ID=你的学号
PASSWORD=你的密码

# 通知配置（可选，不配则仅控制台输出）
SERVER_CHAN_KEY=你的Server酱SendKey

# 轮询间隔，单位分钟（默认 30）
POLL_INTERVAL_MINUTES=30
```

### 使用方式

```bash
# 单次查询全部学期成绩
bash scripts/run.sh

# 查看本地已存储的成绩（表格形式，按学期分组，含统计信息）
bash scripts/view.sh

# 或直接使用 python
python main.py once                           # 查询全部学期
python main.py once --semester 2025-2026-2    # 查询指定学期
python main.py schedule                       # 启动定时轮询（后台持续运行）
python main.py view                           # 查看本地已存储的成绩
python main.py view --semester 2025-2026-2    # 查看指定学期的成绩
python main.py test                           # 测试通知推送通道
```

Windows 用户也可以直接双击 `getscore.bat`，一键完成查询并展示最新成绩。

学期格式：`2025-2026-1`（第一学期）或 `2025-2026-2`（第二学期）。

## 项目结构

```
GetScore/
├── main.py                 # 主入口，CLI 命令分发
├── pyproject.toml          # 项目元数据与依赖声明
├── .env.example            # 配置文件模板
├── scripts/
│   ├── setup.sh            # 环境初始化脚本
│   ├── run.sh              # 单次查询脚本
│   ├── schedule.sh         # 定时轮询脚本
│   ├── view.sh             # 查看本地成绩脚本
│   └── test.sh             # 通知测试脚本
├── src/
│   ├── models.py           # 数据模型（ScoreItem / ScoreChange / SemesterStats）
│   ├── config.py           # 配置管理（环境变量读取）
│   ├── auth.py             # CAS 登录认证 + RSA 加密
│   ├── fetcher.py          # 教务系统 API 调用与分页抓取
│   ├── parser.py           # 成绩解析与挂科判断
│   ├── database.py         # SQLite 存储、差异检测与统计
│   ├── notifier.py         # 消息推送（Server酱 / 控制台）
│   ├── viewer.py           # 本地成绩的表格化展示
│   └── scheduler.py        # APScheduler 定时轮询编排
├── data/
│   └── scores.db           # SQLite 数据库（自动生成）
├── logs/
│   └── app.log             # 应用日志（自动生成）
└── discuss/
    └── architecture.md     # 架构设计文档
```

## 数据流

```
定时触发 / 手动执行
      │
      ▼
  ┌────────┐    CAS 登录     ┌──────────────┐
  │  auth  │ ──────────────► │ 提取 execution │
  │        │ ◄────────────── │ RSA 加密密码   │
  └────────┘   登录 Cookie   └──────────────┘
      │
      ▼
  ┌─────────┐   分页请求     ┌────────────────┐
  │ fetcher │ ─────────────► │ 成绩查询 API    │
  └─────────┘ ◄───────────── │ JSON 原始数据  │
      │
      ▼
  ┌────────┐   解析判断     ┌──────────────┐
  │ parser │ ─────────────► │ ScoreItem 对象 │
  └────────┘                └──────────────┘
      │
      ▼
  ┌──────────┐  差异对比    ┌────────────┐
  │ database │ ───────────► │ SQLite 存储  │
  └──────────┘   upsert     └────────────┘
      │
      ▼  (有新成绩时)
  ┌──────────┐  消息推送    ┌──────────────┐
  │ notifier │ ───────────► │ Server酱/控制台│
  └──────────┘              └──────────────┘
```

## 挂科判断规则

满足以下**任一条件**即判定为挂科：

1. 成绩状态为 `不及格` / `缺考` / `作弊` / `取消资格` / `违纪`（优先级最高）
2. 综合成绩（zhcj）为有效数字且 < 60
3. 绩点（jd）为 0 且综合成绩 < 60

## 技术栈

| 组件 | 技术选型 |
|------|---------|
| 语言 | Python 3.8+ |
| 包管理 | uv |
| HTTP 请求 | requests |
| RSA 加密 | pycryptodome |
| 数据存储 | SQLite |
| 定时调度 | APScheduler |
| 消息推送 | Server酱 Turbo |
| 配置管理 | python-dotenv |

## 安全注意事项

- `.env` 文件包含明文密码，已加入 `.gitignore`，切勿提交到版本控制
- 教务系统 Cookie 有效期约 2-4 小时，调度器会自动重新登录
- RSA 公钥可能随时间过期，登录失败时需重新抓包获取
- Server酱 SendKey 属于敏感信息，不要提交到版本控制
- 本工具仅供个人学习与合法使用，请勿滥用

## 许可证

MIT License

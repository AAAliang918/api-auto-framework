# 基于 Python + requests + pytest 的接口自动化测试框架

数据驱动的接口自动化测试项目：统一请求封装（超时 / 鉴权 / 重试 / 日志）、JSON 用例管理、
Allure 可视化报告，覆盖登录与权限两类业务场景。

## 功能特性

- **请求统一封装**：`base_url`、超时、Bearer 鉴权、异常捕获集中在 `RequestUtil` 一处，改一处全局生效
- **自动鉴权**：登录获取 token；收到 401 时清空旧 token、重新登录并只重试一次（用标记位防递归死循环）
- **限流处理**：收到 429 时读取 `Retry-After` 等待后重试，且只对 GET/HEAD/PUT/DELETE/OPTIONS 等幂等接口生效
- **数据驱动**：用例写在 `data/cases.json`，新增同类用例不需要改代码
- **断言封装**：一次校验 HTTP 状态码、业务 code 与点号路径字段（如 `data.token`），失败信息带完整响应
- **身份隔离**：每个测试账号一个独立会话，token 不会互相覆盖
- **报告与日志**：Allure 报告按接口分组展示，请求与异常信息落盘到 `logs/run.log`

## 技术栈

| 类别 | 选型 |
|---|---|
| 语言 | Python 3.14 |
| 请求库 | requests 2.32 |
| 测试框架 | pytest 9.1 |
| 数据驱动 | JSON + pytest.mark.parametrize |
| 报告 | Allure |
| 日志 | logging |

## 目录结构

```
api_auto/
├── common/
│   ├── config.py          # 环境配置：base_url、超时、测试账号
│   ├── request_util.py    # 请求封装：鉴权 / 超时 / 重试 / 日志
│   ├── assert_util.py     # 断言封装：状态码 / 业务码 / 点号路径字段
│   └── case_loader.py     # 读取 data 下的用例文件
├── data/
│   └── cases.json         # 测试用例数据（按接口分组）
├── testcases/
│   ├── test_login.py      # 登录接口用例（数据驱动）
│   └── test_permission.py # 权限控制用例（数据驱动）
├── conftest.py            # 公共 fixture：会话 / token / 请求头 / 日志配置
├── mock_server.py         # 本地 mock 服务（鉴权 / 403 / 429 / 超时）
├── pytest.ini             # pytest 配置（用例路径、标记、allure 输出）
├── requirements.txt
└── notes/                 # 开发日志与待办
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动 mock 服务（保持这个窗口运行）

```bash
python mock_server.py
```

服务地址 `http://127.0.0.1:5000`。这是一个常驻进程，测试期间不要关掉终端。

### 3. 执行测试

另开一个终端：

```bash
python -m pytest
```

### 4. 查看 Allure 报告

```bash
allure generate reports/allure-results -o reports/allure-report --clean
allure open reports/allure-report
```

`pytest.ini` 中已配置 `--alluredir`，执行用例时会自动把结果写入 `reports/allure-results`。
运行以上命令需要本机安装 allure 命令行工具与 Java。

## 测试账号

| 账号 | 密码 | 角色 | 用途 |
|---|---|---|---|
| admin | 123456 | admin | 正常业务与高权限场景 |
| tester | 123456 | qa | 构造 403 无权限场景 |
| （不带 token） | — | 游客 | 构造 401 未认证场景 |

## 用例覆盖

| 分组 | 条数 | 覆盖场景 |
|---|---|---|
| 登录 login | 3 | 登录成功 200、密码错误 401、用户名为空 400 |
| 权限 permission | 3 | admin 访问 200、tester 无权限 403、未携带 token 401 |

当前共 6 条用例，全部通过；订单、用户、超时场景在计划中（见「后续计划」）。

## mock 接口清单

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/login` | json 登录，返回 token |
| GET | `/user/info` | 需 Bearer token，返回当前用户信息 |
| GET | `/admin/users` | 需 admin 角色，普通用户返回 403 |
| GET | `/orders?page=N` | 需 token，返回订单列表 |
| GET | `/limited` | 前 2 次返回 429（带 Retry-After），第 3 次成功 |
| GET | `/slow?delay=N` | 延迟返回，用于超时用例 |
| GET/POST | `/echo` | 回显请求，用于确认实际发送内容 |

## 设计说明

### 为什么把请求封装成唯一出口

所有请求都走 `RequestUtil.request()`，`base_url`、超时、鉴权、日志、重试只在这一处实现。
以后要给全部请求加统一请求头，或更换请求库，只改一个文件，不用动几十条用例。

### 为什么 token 用 session 级 fixture，而每个账号独立客户端

登录是相对昂贵的操作，整个测试会话只做一次，因此用 session 级 fixture 复用。
但 token 存在 `RequestUtil` 的实例属性上：如果多个账号共用一个实例，后登录的会覆盖前一个的 token，
导致用例之间互相污染。所以按账号各建一个客户端（`clients` fixture），身份互不干扰。

### 为什么 401 只重试一次

401 分支里重新登录后递归调用自身，并把 `_retry_auth` 置为 `False`。
第二次再收到 401 时条件不成立，直接返回响应，避免 token 始终无效时无限递归把测试卡死。

### 为什么 429 只对幂等接口重试

GET/HEAD/PUT/DELETE/OPTIONS 重复执行结果一致，重试是安全的；
POST 不幂等，重试可能导致重复下单、重复扣款，因此宁可直接把 429 交给用例判断。

### 为什么用例数据放在 JSON 里

新增用例只修改 `data/cases.json`，测试代码不动。用例文件里除了请求参数和预期结果，
还包含 `user` 字段指定调用身份，因此同一个测试函数可以覆盖 admin 有权、tester 403、游客 401 三种情况。

## 踩坑记录

- **登录成功后忘了把 token 写进 headers**：第一次请求空手发出、收到 401、又触发一次重新登录。
  日志里出现「一次多余的 401 + 两次登录」才定位到问题，修复方式是把鉴权逻辑统一放到发请求之前。
- **断言工具里误用 `resp.status`**：`requests.Response` 只有 `status_code`，报错是 `AttributeError`
  而不是「状态码不符」，排查时被误导。断言失败信息补上期望值和响应体后，定位效率明显提高。
- **点号路径校验未处理 `expect_fields=None`**：默认值直接用于 `for` 循环会抛
  `TypeError: 'NoneType' is not iterable`，改为 `expect_fields or []`。

## 后续计划

- [ ] 补充订单、用户、超时场景用例（目标 12 条）
- [ ] `cases.json` 增加 `story` 字段，报告按「正常 / 异常」分组展示
- [ ] 接入 GitHub Actions，实现提交即跑用例
- [ ] 增加数据库校验（需要真实 MySQL 环境）

# 开发日志

记录做接口自动化项目（api_auto）的过程。每件事三行：做了什么 / 为什么 / 踩了什么坑。

## 请求封装 + 断言工具 + 数据驱动登录用例（pytest 3 passed）

### [fixture] api_client
- 做了什么：session 级夹具，创建 RequestUtil，yield 出去，全部用例跑完再 close()。
- 为什么：连接和登录 token 都是昂贵又只读的资源，整个会话建一次就够；用 yield 是"交出对象 + 记得收尾"。
- 坑：一开始以为 scope 越大越好，后来明白可变状态（比如按不同用户登录）就不能共用，否则用例之间互相污染。

### [fixture] token
- 做了什么：session 级，调用 api_client.login()，断言成功，返回 token。
- 为什么：几十条用例都要 token，登录一次就够；它依赖 api_client，正好把"登录"这件事收在一处。
- 坑：如果改成 function 级，每条用例都重新登录，速度慢、日志也乱。

### [fixture] auth_headers
- 做了什么：function 级，返回 {"Authorization": "Bearer " + token}。
- 为什么：每次新建一个 dict，某条用例改了 header 不会影响下一条。

### [RequestUtil.__init__]
- 做了什么：存 base_url（rstrip 掉结尾的 /）和 timeout，建 session，token / username / password 先设 None。
- 为什么：这几个值要给 get、post、request、login 共用，只能挂在 self 上。
- 坑：忘了初始化 username / password，第一次带鉴权的请求直接 AttributeError。

### [RequestUtil.get / post]
- 做了什么：一行转发给 request("GET" / "POST", path, **kwargs)。
- 为什么：方法名写死，调用方不可能传错；同时保证所有请求只有一个出口，以后加日志、加超时只改一处。
- 坑：一开始忘了写 return，调用方拿到 None。

### [RequestUtil.request]
- 做了什么：拼 url → setdefault 超时 → 处理 headers 和 Bearer token → 发请求前后各打一条日志 → 捕获三类异常返回 None → 401 重登一次 → 429 按 Retry-After 等待重试（只对幂等方法）。
- 为什么：
  - timeout 用 setdefault：默认值只兜底，慢接口要让调用方能覆盖。
  - 401 只重试一次：递归调自己时传 _retry_auth=False，第二次再 401 就直接返回，防死循环。
  - 429 只对 GET / HEAD / PUT / DELETE / OPTIONS 重试：这些是幂等的；POST 重试可能重复下单。
  - 重试那层要写 return：不写的话重试结果被扔掉，外面拿到的还是那个 401。
- 坑：
  - kwargs.pop('headers' or {}) 少了个逗号，实际等于 pop('headers')，调用方没传 headers 就 KeyError。正确写法是 pop('headers', {}) or {}。
  - 登录成功后忘了往 headers 里写 Authorization，结果第一次请求空手发出去 → 401 → 又重登一次，日志里能看到一次多余的 401 和两次登录。
  - "Bearer" + token 少了空格，服务端认的是 "Bearer xxx"。
  - --> 日志一开始打在响应之后，请求异常时反而看不到当时发了什么；改成发请求前一条、收到响应后一条。

### [RequestUtil.login]
- 做了什么：POST /login，依次检查响应不为 None、状态码 200、业务 code 为 0、token 非空，最后存进 self.token。
- 为什么：登录有四层失败可能，每层都要给出能看懂的日志，否则最后只会得到一个看不懂的 TypeError（"Bearer " + None）。
- 坑：不能传 authorized=True，否则 login 里又要触发登录，直接无限递归。

### [assert_response]
- 做了什么：先断言 resp 不为 None，再断言状态码、业务码，最后按点号路径逐个校验字段存在且非空，失败信息里带完整响应。
- 为什么：
  - 先判 None：否则下一行 resp.status_code 直接 AttributeError，看不到"超时"这个真正原因。
  - 点号路径：用例数据写在 json / yaml 里，只能写字符串，写不了 body["data"]["token"]，所以约定 data.token 这种写法，让代码去翻译。
  - 失败信息带响应：报错时直接看到服务端返回了什么，不用再手动复现。
- 坑：
  - 写成 resp.status（没这个属性），报出来是 AttributeError 而不是"状态码不符"。
  - 忘了 expect_fields or []，不传字段列表时报 TypeError: 'NoneType' is not iterable。
  - 断言写反成 assert resp is None，等于把"超时"当成正确结果。

### [test_login] 数据驱动
- 做了什么：用 parametrize 读 cases.json，一条用例一个 dict，测试函数只做"发请求 + 断言"，期望值全部来自数据文件。
- 为什么：加用例只改 json、不改代码，这是练习脚本和工作项目的分界线。
- 坑：缩进多打了 4 个空格，PyCharm 标红，运行报 IndentationError。

### [接入] conftest 换成 RequestUtil
- 做了什么：api_client 返回 RequestUtil，token fixture 改成 api_client.login() 后取 self.token，用例里的 BASE_URL 去掉。
- 为什么：用例不该知道服务器地址，换环境只改 common/config.py 一处。
- 结果：python -m pytest -v 跑出 3 passed。

## 其他踩过的坑

- pytest 只收集 test_ 开头的函数；顶层脚本用 pytest 跑会 collected 0 items，但顶层 print 照样执行，看着像"通过了"。
- no tests ran 时 pytest 退出码是 5 而不是 0，接 Jenkins 会被判失败。
- PyCharm 会自动补一些用不上的 import（比如 from PIL.ImageCms import Flags），别人没装 Pillow 就 ImportError，提交前一定要清。
- PyCharm 里灰色小字 msg:、*args: 是参数名提示，不是要敲进代码的。

## 30 秒项目串讲（面试用）

"我用 Python + requests + pytest 搭了一套接口自动化：把请求封装成 RequestUtil 类，统一处理 base_url、超时、Bearer 鉴权和日志。401 会自动重新登录并只重试一次，429 会按 Retry-After 等待后重试，而且只对幂等接口重试。用例数据放在 json 文件里，用 pytest 的 parametrize 做数据驱动，代码里没有写死的账号和参数。断言封装成 assert_response，支持点号路径校验嵌套字段，失败信息里带完整响应。token 用 session 级 fixture 只登录一次，供所有用例复用。目前 3 条登录用例全部通过，正向和逆向场景都有覆盖。"

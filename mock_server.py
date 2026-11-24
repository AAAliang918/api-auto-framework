"""本地 mock 接口服务（只依赖标准库）。

启动：python mock_server.py
地址：http://127.0.0.1:5000

接口清单：
  POST /login             json 登录 -> {"code":0,"data":{"token":...}}
  GET  /user/info         需要 Bearer token
  GET  /admin/users       需要 admin 角色，普通用户 403
  GET  /orders?page=N     需要 Bearer token
  GET  /limited           前 2 次返回 429 + Retry-After: 1，之后返回 200
  GET  /slow?delay=3      延迟返回，用来练超时
  GET/POST /echo          原样回显请求，用来确认自己发了什么
"""
import json
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

USERS = {"admin": "123456", "tester": "123456"}
TOKENS = {}
LIMIT_COUNTER = {}
LOCK = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _send(self, code, payload, extra_headers=None):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        for k, v in (extra_headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(n) if n else b""

    def _json(self):
        try:
            return json.loads(self._body() or b"{}")
        except json.JSONDecodeError:
            return {}

    def _token(self):
        auth = self.headers.get("Authorization", "")
        return auth[7:] if auth.lower().startswith("bearer ") else self.headers.get("token")

    def _require_token(self):
        tk = self._token()
        if not tk:
            self._send(401, {"code": 1002, "msg": "未携带token"})
            return None
        if tk not in TOKENS:
            self._send(401, {"code": 1002, "msg": "token无效或已过期"})
            return None
        return tk

    def do_GET(self):
        parsed = urlparse(self.path)
        path, query = parsed.path, parse_qs(parsed.query)

        if path == "/echo":
            return self._send(200, {"method": "GET", "path": path,
                                    "query": {k: v[0] for k, v in query.items()},
                                    "headers": dict(self.headers)})

        if path == "/slow":
            time.sleep(float(query.get("delay", ["3"])[0]))
            return self._send(200, {"code": 0, "msg": "slow ok"})

        if path == "/limited":
            tk = self._token() or "anonymous"
            with LOCK:
                LIMIT_COUNTER[tk] = LIMIT_COUNTER.get(tk, 0) + 1
                hits = LIMIT_COUNTER[tk]
            if hits <= 2:
                return self._send(429, {"code": 4290, "msg": "请求太频繁，请稍后再试"},
                                  {"Retry-After": "1"})
            return self._send(200, {"code": 0, "msg": "ok after retry"})

        if path == "/user/info":
            if not self._require_token():
                return
            user = TOKENS[self._token()]
            return self._send(200, {"code": 0, "data": {
                "id": 1001 if user == "admin" else 1002,
                "username": user,
                "role": "admin" if user == "admin" else "qa"}})

        if path == "/orders":
            if not self._require_token():
                return
            page = int(query.get("page", ["1"])[0])
            if page<1:
                return self._send(400,{'code':1000,'msg':"page必须大于等于1"})
            items=[]if page>1 else [
                {"orderId": "A1001", "amount": 99.0},
                {"orderId": "A1002", "amount": 199.0}
            ]
            return self._send(200, {"code": 0, "data": {
                "page": page, "total": 2,
                "list": items }})

        if path == "/admin/users":
            tk = self._require_token()
            if not tk:
                return
            if TOKENS[tk] != "admin":
                return self._send(403, {"code": 1003, "msg": "无权访问：需要 admin 角色"})
            return self._send(200, {"code": 0, "data": {"list": ["admin", "tester"]}})

        return self._send(404, {"code": 404, "msg": "接口不存在: " + path})

    def do_POST(self):
        path = urlparse(self.path).path
        ctype = self.headers.get("Content-Type", "")

        if path == "/echo":
            raw = self._body().decode("utf-8", "ignore")
            if "json" in ctype:
                body = self._json()
            elif "x-www-form-urlencoded" in ctype:
                body = {k: v[0] for k, v in parse_qs(raw).items()}
            else:
                body = raw
            return self._send(200, {"method": "POST", "path": path,
                                    "contentType": ctype, "body": body})

        if path == "/login":
            data = self._json()
            username, password = data.get("username"), data.get("password")
            if not username or not password:
                return self._send(400, {"code": 1000, "msg": "用户名或密码不能为空"})
            if USERS.get(username) != password:
                return self._send(401, {"code": 1001, "msg": "用户名或密码错误"})
            tk = secrets.token_hex(8)
            TOKENS[tk] = username
            return self._send(200, {"code": 0, "msg": "登录成功",
                                    "data": {"token": tk, "expires_in": 3600}})

        return self._send(404, {"code": 404, "msg": "接口不存在: " + path})

    def log_message(self, fmt, *args):
        print("[mock] " + fmt % args)


if __name__ == "__main__":
    print("mock server 已启动: http://127.0.0.1:5000  (Ctrl+C 退出)")
    ThreadingHTTPServer(("127.0.0.1", 5000), Handler).serve_forever()
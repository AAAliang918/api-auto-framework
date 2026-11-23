# 待办清单

## 上传 GitHub 前必须做

- [ ] 修 RequestUtil 里的耗时公式：三处都是 `perf_counter() - start*1000`，要改成 `(time.perf_counter() - start) * 1000`
- [ ] 补成功响应的日志：`<-- 状态码=xx 耗时=xxms`（现在只有异常分支才有 `<--`）
- [ ] 写 README：设计说明、踩坑记录、快速开始
- [ ] git init + 分 6~8 次有意义的提交（不要一次性 push）
- [ ] 确认 .gitignore 已排除 reports/ logs/ .idea/ __pycache__

## 待补用例（6 条，补完共 12 条）

- [ ] order_001  默认第 1 页返回列表        200  fields: data.list / data.total
- [ ] order_002  page=0 参数非法            400  （mock 需要先加 page 校验）
- [ ] order_003  page=999 返回空列表        200  fields: data.list
- [ ] user_001   admin 查询 /user/info     200  fields: data.role
- [ ] user_002   tester 查询 /user/info    200  fields: data.role
- [ ] token_001  非法 token 访问 /admin/users  401  code 1002

## 之后（不影响先上传）

- [ ] cases.json 每条加 "story" 字段，报告按 正常/异常 分组
- [ ] pymysql 数据库校验（需要真装 MySQL，没环境就别写进简历）
- [ ] GitHub Actions 自动跑用例（选做，能讲 CI 概念）

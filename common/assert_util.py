def assert_response(resp, expected_status=200, expected_code=0, expect_fields=None):
    assert resp is not None,'请求未拿到响应（超时/连接失败）'
    assert resp.status_code == expected_status, (
        f'状态码不符：期望{expected_status}，实际{resp.status_code}，响应={resp.text[:300]}')
    body = resp.json()
    if expected_code is not None:
        actual_code=body.get('code')
        assert actual_code == expected_code,f'业务码不符：期望{expected_code},实际{actual_code}，响应{body}'
    for path in expect_fields or []:
        value = body
        for key in path.split('.'):
            assert isinstance(value,dict) and key in value,f'字段缺失：{path}里的{key}不存在，响应={body}'
            value = value[key]
        assert value not in(None,{},'',[]),f'字段为空：{path}，实际值={value!r},响应={body}'



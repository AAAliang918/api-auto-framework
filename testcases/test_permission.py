"""权限类用例：数据驱动版本。

数据在 data/cases.json 的 permission 分组，user 字段决定用哪个身份：
admin  -> 有权限
tester -> 登录了但没有 admin 角色
guest  -> 完全不带 token
"""
import allure
import pytest

from common.assert_util import assert_response
from common.case_loader import load_cases

CASES = load_cases()["permission"]


@allure.feature("权限控制")
@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_permission(clients, case):
    allure.dynamic.title(case["title"])
    allure.dynamic.story(case["user"])

    client = clients[case["user"]]
    resp = client.get(case["path"], authorized=case["user"] != "guest")

    expected = case["expected"]
    assert_response(resp, expected_status=expected["status"],
                    expected_code=expected["code"],
                    expect_fields=expected["fields"])

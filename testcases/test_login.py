import allure
import pytest

from common.assert_util import assert_response
from common.case_loader import load_cases

CASES = load_cases()["login"]


@allure.feature("登录接口")
@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_login(api_client, case):
    allure.dynamic.title(case["title"])
    allure.dynamic.story(case["id"])

    resp = api_client.post(case["path"], json=case["json"])

    expected = case["expected"]
    assert_response(resp, expected_status=expected["status"],
                    expected_code=expected["code"],
                    expect_fields=expected["fields"])

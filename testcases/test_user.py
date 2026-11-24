import allure
import pytest

from common.assert_util import assert_response
from common.case_loader import load_cases

CASES = load_cases()["user_info"]


@allure.feature("个人信息")
@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_user_info(clients, case):
    allure.dynamic.title(case["title"])

    client = clients[case["user"]]
    resp = client.get(case["path"], authorized=True)

    expected = case["expected"]
    assert_response(
        resp,
        expected_status=expected["status"],
        expected_code=expected["code"],
        expect_fields=expected["fields"],
        expect_values=expected["values"]
    )
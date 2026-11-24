import allure
import pytest

from common.assert_util import assert_response
from common.case_loader import load_cases

CASES = load_cases()['orders']


@allure.feature("订单接口")
@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_orders(api_client, case):
    allure.dynamic.title(case["title"])

    resp = api_client.get(
        case["path"],
        params=case.get("params"),
        authorized=True,
    )

    expected = case["expected"]
    assert_response(
        resp,
        expected_status=expected["status"],
        expected_code=expected["code"],
        expect_fields=expected["fields"],
        expect_values=expected["values"]
    )
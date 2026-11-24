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
TOKEN_CASES = load_cases()["token"]


@allure.feature("权限控制")
@pytest.mark.parametrize("case", TOKEN_CASES, ids=[c["id"] for c in TOKEN_CASES])
def test_invalid_token(clients, case):
    allure.dynamic.title(case["title"])

    resp = clients["guest"].get(
        case["path"],
        headers={"Authorization": "Bearer " + case["token"]},
    )

    expected = case["expected"]
    assert_response(
        resp,
        expected_status=expected["status"],
        expected_code=expected["code"],
        expect_fields=expected["fields"],
        expect_values=expected["values"]
    )
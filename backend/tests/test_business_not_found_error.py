import pytest

from app.exceptions import BusinessNotFoundError


def test_business_not_found_error_type_and_message():
    with pytest.raises(BusinessNotFoundError) as exc_info:
        raise BusinessNotFoundError()

    assert exc_info.value.args == ("Business not found",)

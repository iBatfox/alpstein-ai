import pytest

from app.exceptions import TenantContextError


def test_tenant_context_error_type_and_message():
    with pytest.raises(TenantContextError) as exc_info:
        raise TenantContextError("business does not belong to tenant")

    assert exc_info.value.args == ("business does not belong to tenant",)

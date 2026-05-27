import uuid
from types import SimpleNamespace

import pytest

from app.exceptions import TenantContextError
from app.services.tenant_context_validator import validate_tenant_context


def _entities(
    *,
    tenant_id: uuid.UUID | None = None,
    business_tenant_id: uuid.UUID | None = None,
    conversation_tenant_id: uuid.UUID | None = None,
    conversation_business_id: uuid.UUID | None = None,
    customer_tenant_id: uuid.UUID | None = None,
    customer_business_id: uuid.UUID | None = None,
    conversation_customer_id: uuid.UUID | None = None,
):
    tenant_id = tenant_id or uuid.uuid4()
    business_id = uuid.uuid4()
    customer_id = uuid.uuid4()

    business = SimpleNamespace(
        id=business_id,
        tenant_id=business_tenant_id if business_tenant_id is not None else tenant_id,
    )
    conversation = SimpleNamespace(
        tenant_id=conversation_tenant_id
        if conversation_tenant_id is not None
        else tenant_id,
        business_id=conversation_business_id
        if conversation_business_id is not None
        else business_id,
        customer_id=conversation_customer_id
        if conversation_customer_id is not None
        else customer_id,
    )
    customer = SimpleNamespace(
        id=customer_id,
        tenant_id=customer_tenant_id if customer_tenant_id is not None else tenant_id,
        business_id=customer_business_id
        if customer_business_id is not None
        else business_id,
    )
    return tenant_id, business, conversation, customer


def test_validate_tenant_context_success_without_customer():
    tenant_id, business, conversation, _ = _entities()

    validate_tenant_context(
        tenant_id=tenant_id,
        business=business,
        conversation=conversation,
    )


def test_validate_tenant_context_success_with_customer():
    tenant_id, business, conversation, customer = _entities()

    validate_tenant_context(
        tenant_id=tenant_id,
        business=business,
        conversation=conversation,
        customer=customer,
    )


def test_validate_tenant_context_business_tenant_mismatch():
    tenant_id, business, conversation, _ = _entities()
    business.tenant_id = uuid.uuid4()

    with pytest.raises(TenantContextError, match="business does not belong to tenant"):
        validate_tenant_context(
            tenant_id=tenant_id,
            business=business,
            conversation=conversation,
        )


def test_validate_tenant_context_conversation_tenant_mismatch():
    tenant_id, business, conversation, _ = _entities()
    conversation.tenant_id = uuid.uuid4()

    with pytest.raises(TenantContextError, match="conversation does not belong to tenant"):
        validate_tenant_context(
            tenant_id=tenant_id,
            business=business,
            conversation=conversation,
        )


def test_validate_tenant_context_conversation_business_mismatch():
    tenant_id, business, conversation, _ = _entities()
    conversation.business_id = uuid.uuid4()

    with pytest.raises(TenantContextError, match="conversation does not belong to business"):
        validate_tenant_context(
            tenant_id=tenant_id,
            business=business,
            conversation=conversation,
        )


def test_validate_tenant_context_customer_tenant_mismatch():
    tenant_id, business, conversation, customer = _entities()
    customer.tenant_id = uuid.uuid4()

    with pytest.raises(TenantContextError, match="customer does not belong to tenant"):
        validate_tenant_context(
            tenant_id=tenant_id,
            business=business,
            conversation=conversation,
            customer=customer,
        )


def test_validate_tenant_context_customer_business_mismatch():
    tenant_id, business, conversation, customer = _entities()
    customer.business_id = uuid.uuid4()

    with pytest.raises(TenantContextError, match="customer does not belong to business"):
        validate_tenant_context(
            tenant_id=tenant_id,
            business=business,
            conversation=conversation,
            customer=customer,
        )


def test_validate_tenant_context_conversation_customer_mismatch():
    tenant_id, business, conversation, customer = _entities()
    conversation.customer_id = uuid.uuid4()

    with pytest.raises(TenantContextError, match="conversation does not belong to customer"):
        validate_tenant_context(
            tenant_id=tenant_id,
            business=business,
            conversation=conversation,
            customer=customer,
        )

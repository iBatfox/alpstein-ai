import uuid

from app.exceptions import TenantContextError


def validate_tenant_context(
    *,
    tenant_id: uuid.UUID,
    business: object,
    conversation: object,
    customer: object | None = None,
) -> None:
    """Ensure tenant, business, conversation, and optional customer references align."""
    if business.tenant_id != tenant_id:
        raise TenantContextError("business does not belong to tenant")

    if conversation.tenant_id != tenant_id:
        raise TenantContextError("conversation does not belong to tenant")

    if conversation.business_id != business.id:
        raise TenantContextError("conversation does not belong to business")

    if customer is None:
        return

    if customer.tenant_id != tenant_id:
        raise TenantContextError("customer does not belong to tenant")

    if customer.business_id != business.id:
        raise TenantContextError("customer does not belong to business")

    if conversation.customer_id != customer.id:
        raise TenantContextError("conversation does not belong to customer")

class TenantContextError(Exception):
    """Raised when tenant, business, customer, or conversation references are inconsistent."""

    def __init__(self, message: str = "Tenant context is inconsistent") -> None:
        super().__init__(message)


class BusinessNotFoundError(Exception):
    """Raised when no business exists for the given external_id."""

    def __init__(self, message: str = "Business not found") -> None:
        super().__init__(message)


class PromptTemplateNotFoundError(Exception):
    """Raised when no active platform prompt template exists for the given key."""

    def __init__(self, template_key: str) -> None:
        self.template_key = template_key
        super().__init__(f"Active prompt template not found: {template_key!r}")

class TenantContextError(Exception):
    """Raised when tenant, business, customer, or conversation references are inconsistent."""

    def __init__(self, message: str = "Tenant context is inconsistent") -> None:
        super().__init__(message)


class BusinessNotFoundError(Exception):
    """Raised when no business exists for the given external_id."""

    def __init__(self, message: str = "Business not found") -> None:
        super().__init__(message)


class FlowNotFoundError(Exception):
    """Raised when no flow exists for the given business and flow_key."""

    def __init__(
        self,
        message: str = "Flow not found",
        *,
        flow_key: str | None = None,
    ) -> None:
        self.flow_key = flow_key
        super().__init__(message)


class MessageTraceNotFoundError(Exception):
    """Raised when no message trace exists for the scoped lookup."""

    def __init__(self, message: str = "Message trace not found") -> None:
        super().__init__(message)


class PromptTemplateNotFoundError(Exception):
    """Raised when no active platform prompt template exists for the given key."""

    def __init__(self, template_key: str) -> None:
        self.template_key = template_key
        super().__init__(f"Active prompt template not found: {template_key!r}")


class AdapterIngressContainedError(Exception):
    """Raised when optional ingress containment rejects adapter traffic (E3.4c)."""

    def __init__(self, channel: str) -> None:
        self.channel = channel
        super().__init__(f"Ingress temporarily not accepted for adapter: {channel}")

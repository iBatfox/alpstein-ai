"""Shared Business Context Builder interview constants."""

STEP_COMPANY_INFORMATION = "company_information"
STEP_BUSINESS_DESCRIPTION = "business_description"
STEP_TARGET_CUSTOMERS = "target_customers"
STEP_PRODUCTS_SERVICES = "products_services"
STEP_SALES_PROCESS = "sales_process"
STEP_COMMUNICATION_STYLE = "communication_style"
STEP_COMPLETED = "completed"

INTERVIEW_STEPS = [
    STEP_COMPANY_INFORMATION,
    STEP_BUSINESS_DESCRIPTION,
    STEP_TARGET_CUSTOMERS,
    STEP_PRODUCTS_SERVICES,
    STEP_SALES_PROCESS,
    STEP_COMMUNICATION_STYLE,
]
ALLOWED_STEPS = frozenset([*INTERVIEW_STEPS, STEP_COMPLETED])

STATIC_QUESTIONS = {
    STEP_COMPANY_INFORMATION: (
        "Hello. I will help you create a draft Business Context. "
        "What is the name of your company?"
    ),
    STEP_BUSINESS_DESCRIPTION: "What does your company do?",
    STEP_TARGET_CUSTOMERS: "Who are your target customers?",
    STEP_PRODUCTS_SERVICES: "What are your main products or services?",
    STEP_SALES_PROCESS: "How does your sales or booking process work?",
    STEP_COMMUNICATION_STYLE: "What communication style should the assistant use?",
}

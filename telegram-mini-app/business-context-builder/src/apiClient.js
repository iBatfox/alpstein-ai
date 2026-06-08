const STEPS = [
  "company_information",
  "business_description",
  "target_customers",
  "products_services",
  "sales_process",
  "communication_style"
];

const STEP_QUESTIONS = {
  company_information:
    "Hello. I will help you create a draft Business Context. What is the name of your company?",
  business_description: "What does your company do?",
  target_customers: "Who are your target customers?",
  products_services: "What are your main products or services?",
  sales_process: "How does your sales or booking process work?",
  communication_style: "What communication style should the assistant use?"
};

export function createBusinessContextBuilderClient(config = {}) {
  const mode = config.mode || "mock";
  if (mode === "backend") {
    return createBackendPlaceholderClient();
  }
  return createMockClient();
}

function createBackendPlaceholderClient() {
  async function blocked() {
    throw new Error(
      "Direct backend calls are disabled in Phase 1. Phase 2 must add a secure Telegram auth bridge."
    );
  }

  return {
    createSession: blocked,
    sendMessage: blocked,
    getSession: blocked,
    completeSession: blocked,
    listContexts: blocked
  };
}

function createMockClient() {
  const state = {
    sessions: new Map(),
    contexts: []
  };

  return {
    async createSession({ tenantId, businessId }) {
      const now = timestamp();
      const session = {
        id: createId(),
        tenant_id: tenantId,
        business_id: businessId,
        status: "active",
        current_step: STEPS[0],
        created_at: now,
        updated_at: now,
        completed_at: null
      };
      const message = createMessage(session.id, "assistant", STEP_QUESTIONS[STEPS[0]]);
      state.sessions.set(session.id, {
        session,
        messages: [message],
        result: null
      });
      return { session, message };
    },

    async sendMessage({ sessionId, content }) {
      const record = requireSession(state, sessionId);
      const userMessage = createMessage(sessionId, "user", content);
      const currentIndex = Math.max(0, STEPS.indexOf(record.session.current_step));
      const nextStep = STEPS[Math.min(currentIndex + 1, STEPS.length - 1)];
      record.session.current_step = nextStep;
      record.session.updated_at = timestamp();
      const assistantMessage = createMessage(
        sessionId,
        "assistant",
        STEP_QUESTIONS[nextStep] ||
          "Thank you. You can continue adding details or complete the draft context."
      );
      record.messages.push(userMessage, assistantMessage);
      return {
        session: record.session,
        user_message: userMessage,
        assistant_message: assistantMessage
      };
    },

    async getSession({ sessionId }) {
      const record = requireSession(state, sessionId);
      return {
        session: record.session,
        messages: record.messages,
        result: record.result
      };
    },

    async completeSession({ sessionId }) {
      const record = requireSession(state, sessionId);
      const userMessages = record.messages
        .filter((message) => message.role === "user")
        .map((message) => message.content);
      const now = timestamp();
      record.session.status = "completed";
      record.session.current_step = "completed";
      record.session.completed_at = now;
      record.session.updated_at = now;
      const result = {
        id: createId(),
        session_id: sessionId,
        tenant_id: record.session.tenant_id,
        business_id: record.session.business_id,
        structured_context: {
          company_overview: userMessages[0] || "Unknown or not provided.",
          business_description: userMessages[1] || "Unknown or not provided.",
          target_customers: userMessages[2] || "Unknown or not provided.",
          products_services: "Unknown or not provided.",
          sales_process: "Unknown or not provided.",
          communication_style: userMessages[userMessages.length - 1] || "Unknown or not provided.",
          missing_information: ["products_services", "sales_process"],
          generation_metadata: {
            generation_mode: "fallback",
            fallback_used: true,
            prompt_version: "1.0",
            provider: null,
            model: null
          }
        },
        generated_prompt:
          "Mock draft result for UI preview. Phase 2 will call the backend through a secure auth bridge.",
        context_file_path: null,
        context_file_url: null,
        created_at: now,
        updated_at: now
      };
      record.result = result;
      state.contexts.unshift(result);
      return {
        session: record.session,
        result
      };
    },

    async listContexts({ limit = 20, offset = 0 } = {}) {
      return {
        items: state.contexts.slice(offset, offset + limit),
        limit,
        offset
      };
    }
  };
}

function requireSession(state, sessionId) {
  const record = state.sessions.get(sessionId);
  if (!record) {
    throw new Error("Session not found");
  }
  return record;
}

function createMessage(sessionId, role, content) {
  return {
    id: createId(),
    session_id: sessionId,
    role,
    content,
    created_at: timestamp()
  };
}

function createId() {
  if (window.crypto && typeof window.crypto.randomUUID === "function") {
    return window.crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function timestamp() {
  return new Date().toISOString();
}

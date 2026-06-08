const STEPS = [
  "company_information",
  "business_description",
  "target_customers",
  "products_services",
  "sales_process",
  "communication_style"
];

const STEP_QUESTIONS = {
  en: {
    company_information:
      "Hello. I will help you create a draft Business Context. What is the name of your company?",
    business_description: "What does your company do?",
    target_customers: "Who are your target customers?",
    products_services: "What are your main products or services?",
    sales_process: "How does your sales or booking process work?",
    communication_style: "What communication style should the assistant use?"
  },
  de: {
    company_information:
      "Hallo. Ich helfe dir, einen Business Context Entwurf zu erstellen. Wie heisst dein Unternehmen?",
    business_description: "Was macht dein Unternehmen?",
    target_customers: "Wer sind deine Zielkunden?",
    products_services: "Was sind deine wichtigsten Produkte oder Dienstleistungen?",
    sales_process: "Wie funktioniert dein Verkaufs- oder Buchungsprozess?",
    communication_style: "Welchen Kommunikationsstil soll der Assistent verwenden?"
  },
  fr: {
    company_information:
      "Bonjour. Je vais vous aider a creer un brouillon de Business Context. Quel est le nom de votre entreprise ?",
    business_description: "Que fait votre entreprise ?",
    target_customers: "Qui sont vos clients cibles ?",
    products_services: "Quels sont vos principaux produits ou services ?",
    sales_process: "Comment fonctionne votre processus de vente ou de reservation ?",
    communication_style: "Quel style de communication l'assistant doit-il utiliser ?"
  },
  uk: {
    company_information:
      "Вітаю. Я допоможу створити чернетку Business Context. Як називається ваша компанія?",
    business_description: "Чим займається ваша компанія?",
    target_customers: "Хто ваші цільові клієнти?",
    products_services: "Які ваші основні продукти або послуги?",
    sales_process: "Як працює процес продажів або бронювання?",
    communication_style: "Який стиль спілкування має використовувати асистент?"
  }
};

const MOCK_TENANT_ID = "00000000-0000-4000-8000-000000000001";
const MOCK_BUSINESS_ID = "00000000-0000-4000-8000-000000000002";

export function createBusinessContextBuilderClient(config = {}) {
  const mode = config.mode || "bridge";
  if (mode === "bridge") {
    return createBridgeClient({
      baseUrl: config.baseUrl || "",
      initData: config.initData || ""
    });
  }
  if (mode === "mock") {
    if (!isLocalDevelopmentHost()) {
      return createBridgeClient({
        baseUrl: config.baseUrl || "",
        initData: config.initData || ""
      });
    }
    return createMockClient({ language: config.language || "en" });
  }
  if (mode === "backend") {
    return createDirectBackendBlockedClient();
  }
  return createBridgeClient({
    baseUrl: config.baseUrl || "",
    initData: config.initData || ""
  });
}

function isLocalDevelopmentHost() {
  return ["localhost", "127.0.0.1"].includes(window.location.hostname);
}

function createDirectBackendBlockedClient() {
  async function blocked() {
    throw createClientError(
      "Direct backend calls are disabled. Use api_mode=bridge so Telegram initData is validated server-side.",
      "DIRECT_BACKEND_DISABLED"
    );
  }

  return {
    authSession: blocked,
    verifyAccess: blocked,
    createSession: blocked,
    sendMessage: blocked,
    getSession: blocked,
    completeSession: blocked,
    listContexts: blocked,
    listBots: blocked
  };
}

function createBridgeClient({ baseUrl, initData }) {
  const bridgeBase = `${baseUrl}/api/v1/telegram-mini-app/business-context-builder`;

  async function request(path, { method = "GET", body } = {}) {
    if (!initData) {
      throw createClientError(
        "Telegram initData is unavailable. Use mock mode for browser preview.",
        "TELEGRAM_INIT_DATA_UNAVAILABLE"
      );
    }

    const response = await fetch(`${bridgeBase}${path}`, {
      method,
      headers: {
        "Content-Type": "application/json",
        "X-Telegram-Init-Data": initData
      },
      body: body === undefined ? undefined : JSON.stringify(body)
    });
    const payload = await response.json();
    if (!response.ok || payload.success === false) {
      throw createClientError(
        (payload.error && payload.error.message) ||
          `Business Context Builder request failed with ${response.status}`,
        payload.error && payload.error.code,
        response.status
      );
    }
    return payload.data;
  }

  return {
    async authSession() {
      return this.verifyAccess();
    },

    async verifyAccess() {
      return request("/verify-access", {
        method: "POST",
        body: { init_data: initData }
      });
    },

    async createSession() {
      return request("/sessions", {
        method: "POST",
        body: {}
      });
    },

    async sendMessage({ sessionId, content }) {
      return request(`/sessions/${encodeURIComponent(sessionId)}/messages`, {
        method: "POST",
        body: { content }
      });
    },

    async getSession({ sessionId }) {
      return request(`/sessions/${encodeURIComponent(sessionId)}`);
    },

    async completeSession({ sessionId }) {
      return request(`/sessions/${encodeURIComponent(sessionId)}/complete`, {
        method: "POST",
        body: {}
      });
    },

    async listContexts({ limit = 20, offset = 0 } = {}) {
      const params = new URLSearchParams({
        limit: String(limit),
        offset: String(offset)
      });
      return request(`/contexts?${params.toString()}`);
    },

    async listBots() {
      throw createClientError(
        "Bots listing is not implemented in the backend bridge yet.",
        "BOTS_API_NOT_IMPLEMENTED",
        501
      );
    }
  };
}

function createMockClient({ language }) {
  const state = {
    language,
    sessions: new Map(),
    contexts: [],
    bots: [
      {
        id: "mock-instagram-sales",
        name: "Instagram Lead Assistant",
        source: "Instagram",
        context_title: "Demo service context",
        context_id: "mock-context-001",
        status: "draft",
        updated_at: timestamp()
      },
      {
        id: "mock-website-chat",
        name: "Website Chat Qualification",
        source: "Website",
        context_title: null,
        context_id: null,
        status: "paused",
        updated_at: timestamp()
      }
    ]
  };

  return {
    async authSession() {
      return this.verifyAccess();
    },

    async verifyAccess() {
      return {
        allowed: true,
        user: {
          telegram_user_id: 0,
          display_name: "Browser preview",
          company_name: "Mock Company",
          alpstein_business_id: "alpstein-ai",
          status: "active"
        },
        company_name: "Mock Company",
        alpstein_business_id: "alpstein-ai",
        integrations: [
          {
            id: "mock-telegram-1",
            alpstein_business_id: "alpstein-ai",
            channel_type: "telegram",
            display_name: "Telegram Bot 1",
            status: "connected",
            external_channel_id: "telegram_bot_1",
            provider: "telegram",
            workflow_name: "Telegram customer ingress 1",
            workflow_id: "placeholder",
            backend_route: "/api/v1/webhook/telegram",
            notes: "Local preview integration"
          },
          {
            id: "mock-telegram-2",
            alpstein_business_id: "alpstein-ai",
            channel_type: "telegram",
            display_name: "Telegram Bot 2",
            status: "connected",
            external_channel_id: "telegram_bot_2",
            provider: "telegram",
            workflow_name: "Telegram customer ingress 2",
            workflow_id: "placeholder",
            backend_route: "/api/v1/webhook/telegram",
            notes: "Local preview integration"
          },
          {
            id: "mock-instagram",
            alpstein_business_id: "alpstein-ai",
            channel_type: "instagram",
            display_name: "Instagram",
            status: "connected",
            external_channel_id: "instagram_account",
            provider: "meta",
            workflow_name: "Instagram unified customer ingress",
            workflow_id: "placeholder",
            backend_route: "/api/v1/webhook/meta",
            notes: "Local preview integration"
          }
        ],
        telegram_user: {
          id: 0,
          first_name: "Browser preview"
        },
      };
    },

    async createSession({ tenantId = MOCK_TENANT_ID, businessId = MOCK_BUSINESS_ID } = {}) {
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
      const message = createMessage(session.id, "assistant", questionFor(state.language, STEPS[0]));
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
        questionFor(state.language, nextStep)
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
          "Mock draft result for UI preview. Backend language-aware generation is not implemented yet.",
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
    },

    async listBots() {
      return {
        items: state.bots
      };
    }
  };
}

function requireSession(state, sessionId) {
  const record = state.sessions.get(sessionId);
  if (!record) {
    throw createClientError("Session not found", "SESSION_NOT_FOUND", 404);
  }
  return record;
}

function questionFor(language, step) {
  const questions = STEP_QUESTIONS[language] || STEP_QUESTIONS.en;
  return (
    questions[step] ||
    "Thank you. You can continue adding details or complete the draft context."
  );
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

function createClientError(message, code = "REQUEST_FAILED", status = 0) {
  const error = new Error(message);
  error.code = code;
  error.status = status;
  return error;
}

const screens = Array.from(document.querySelectorAll(".screen"));
const bottomNav = document.getElementById("bottomNav");
const loginForm = document.getElementById("loginForm");
const botGrid = document.getElementById("botGrid");
const stepLabel = document.getElementById("stepLabel");
const progressFill = document.getElementById("progressFill");
const wizardQuestion = document.getElementById("wizardQuestion");
const wizardAnswer = document.getElementById("wizardAnswer");
const wizardContinue = document.getElementById("wizardContinue");
const answerStack = document.getElementById("answerStack");
const channelBack = document.getElementById("channelBack");
const channelTitle = document.getElementById("channelTitle");
const channelStatus = document.getElementById("channelStatus");
const channelStats = document.getElementById("channelStats");
const channelConnection = document.getElementById("channelConnection");
const accessDeniedMessage = document.getElementById("accessDeniedMessage");

const accessMessage =
  "Access is not enabled for your account yet. Please contact Alpstein AI.";
const apiMode = getConfigValue("api_mode", "bridge");
const apiBaseUrl = getConfigValue("api_base_url", "");
const localMockAllowed = isLocalDevelopmentHost();

const wizardSteps = [
  "What is your company name?",
  "What do you sell?",
  "Who are your customers?",
  "How should the assistant communicate?",
  "What questions do customers ask most often?"
];

const answers = [];
let integrations = [];
let currentStep = 0;

renderIntegrations();
renderWizard();
verifyStartupAccess();

loginForm.addEventListener("submit", (event) => {
  event.preventDefault();
  if (apiMode !== "mock" || !localMockAllowed) return;
  integrations = getMockIntegrations();
  renderIntegrations();
  bottomNav.hidden = false;
  showScreen("bots");
});

bottomNav.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-nav]");
  if (!button) return;
  showScreen(button.dataset.nav);
});

channelBack.addEventListener("click", () => {
  showScreen("bots");
});

wizardContinue.addEventListener("click", () => {
  const answer = wizardAnswer.value.trim();
  answers[currentStep] = answer || "Prototype answer not entered yet.";
  wizardAnswer.value = "";

  if (currentStep < wizardSteps.length - 1) {
    currentStep += 1;
    renderWizard();
    return;
  }

  renderGeneratedContext();
  showScreen("context");
});

function showScreen(screenName) {
  screens.forEach((screen) => {
    screen.classList.toggle("screen-active", screen.dataset.screen === screenName);
  });

  bottomNav.querySelectorAll("button[data-nav]").forEach((button) => {
    button.classList.toggle("active", button.dataset.nav === screenName);
  });
}

async function verifyStartupAccess() {
  bottomNav.hidden = true;

  if (apiMode === "mock" && localMockAllowed) {
    integrations = getMockIntegrations();
    renderIntegrations();
    showScreen("login");
    return;
  }

  showScreen("verifying");

  try {
    const access = await requestAccessVerification();
    integrations = Array.isArray(access.integrations) ? access.integrations : [];
    renderIntegrations();
    bottomNav.hidden = false;
    showScreen("bots");
  } catch (_error) {
    showAccessDenied();
  }
}

async function requestAccessVerification() {
  const initData = getTelegramInitData();
  if (!initData) {
    throw new Error("Telegram initData is required");
  }

  const response = await fetch(
    `${apiBaseUrl}/api/v1/telegram-mini-app/business-context-builder/verify-access`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        init_data: initData
      })
    }
  );

  if (!response.ok) {
    throw new Error("Access verification failed");
  }

  const payload = await response.json();
  if (!payload.success || payload.data?.allowed !== true) {
    throw new Error("Access denied");
  }

  return payload.data;
}

function getTelegramInitData() {
  const webApp = window.Telegram?.WebApp;
  webApp?.ready?.();
  return webApp?.initData || "";
}

function getConfigValue(key, fallback) {
  const params = new URLSearchParams(window.location.search);
  const value = params.get(key);
  return value === null || value === "" ? fallback : value;
}

function isLocalDevelopmentHost() {
  return ["localhost", "127.0.0.1"].includes(window.location.hostname);
}

function showAccessDenied() {
  if (accessDeniedMessage) {
    accessDeniedMessage.textContent = accessMessage;
  }
  bottomNav.hidden = true;
  showScreen("access-denied");
}

function renderIntegrations() {
  if (integrations.length === 0) {
    const empty = document.createElement("article");
    empty.className = "shared-context-note";
    empty.textContent =
      "No channels are connected for this business yet. Channels are connected by Alpstein AI after setup.";
    botGrid.replaceChildren(empty);
    return;
  }

  botGrid.replaceChildren(
    ...integrations.map((integration) => {
      const card = document.createElement("article");
      const icon = document.createElement("div");
      const content = document.createElement("div");
      const title = document.createElement("h3");
      const status = document.createElement("p");
      const workflow = document.createElement("p");
      const button = document.createElement("button");
      card.className = "bot-card";
      icon.className = "channel-icon";
      icon.setAttribute("aria-hidden", "true");
      icon.textContent = integrationIcon(integration.channel_type);
      title.textContent = integration.display_name;
      status.textContent = [
        formatStatus(integration.status),
        integration.provider || null
      ].filter(Boolean).join(" · ");
      workflow.textContent = integration.workflow_name
        ? `Workflow: ${integration.workflow_name}`
        : "Managed by Alpstein AI";
      button.className = "secondary-button compact";
      button.type = "button";
      button.textContent = "Open channel";
      button.addEventListener("click", () => openChannelDetail(integration.id));
      content.append(title, status, workflow);
      card.append(icon, content, button);
      card.addEventListener("click", (event) => {
        if (event.target.closest("button")) return;
        openChannelDetail(integration.id);
      });
      return card;
    })
  );
}

function openChannelDetail(integrationId) {
  const integration = integrations.find((item) => item.id === integrationId);
  if (!integration) return;
  channelTitle.textContent = integration.display_name;
  channelStatus.textContent = formatStatus(integration.status);
  renderChannelStats(mockStatsForIntegration(integration));
  renderChannelConnection(integration);
  showScreen("channel-detail");
}

function renderChannelStats(stats) {
  const rows = [
    ["Messages today", stats.messagesToday],
    ["Leads created", stats.leadsCreated],
    ["Last message time", stats.lastMessageTime],
    ["Failed replies", stats.failedReplies],
    ["Conversion rate", stats.conversionRate]
  ];
  channelStats.replaceChildren(...rows.map(([label, value]) => createMetricCard(label, value)));
}

function renderChannelConnection(integration) {
  const rows = [
    ["Channel type", integration.channel_type],
    ["External channel ID", integration.external_channel_id || "Not provided"],
    ["Provider", integration.provider || "Not provided"],
    ["Workflow name", integration.workflow_name || "Not provided"],
    ["Workflow ID", integration.workflow_id || "Not provided"],
    ["Backend route", integration.backend_route || "Not provided"],
    ["Notes", integration.notes || "No notes"]
  ];
  channelConnection.replaceChildren(
    ...rows.map(([label, value]) => {
      const row = document.createElement("article");
      const key = document.createElement("span");
      const val = document.createElement("strong");
      row.className = "connection-row";
      key.textContent = label;
      val.textContent = value;
      row.append(key, val);
      return row;
    })
  );
}

function integrationIcon(channelType) {
  const icons = {
    telegram: "TG",
    instagram: "IG",
    whatsapp: "WA",
    website: "Web"
  };
  return icons[channelType] || "Ch";
}

function formatStatus(status) {
  return (status || "unknown")
    .split("_")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function mockStatsForIntegration(integration) {
  const base = {
    messagesToday: "0",
    leadsCreated: "0",
    lastMessageTime: "No messages today",
    failedReplies: "0",
    conversionRate: "0%"
  };
  if (integration.channel_type === "telegram") {
    return {
      ...base,
      messagesToday: "18",
      leadsCreated: "3",
      lastMessageTime: "13:58",
      conversionRate: "17%"
    };
  }
  if (integration.channel_type === "instagram") {
    return {
      ...base,
      messagesToday: "42",
      leadsCreated: "6",
      lastMessageTime: "14:32",
      failedReplies: "1",
      conversionRate: "14%"
    };
  }
  return base;
}

function getMockIntegrations() {
  return [
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
  ];
}

function createMetricCard(labelText, valueText) {
  const card = document.createElement("article");
  const label = document.createElement("span");
  const value = document.createElement("strong");
  card.className = "metric-card";
  label.textContent = labelText;
  value.textContent = valueText;
  card.append(label, value);
  return card;
}

function renderWizard() {
  stepLabel.textContent = `Step ${currentStep + 1} of ${wizardSteps.length}`;
  progressFill.style.width = `${((currentStep + 1) / wizardSteps.length) * 100}%`;
  wizardQuestion.textContent = wizardSteps[currentStep];
  wizardContinue.textContent =
    currentStep === wizardSteps.length - 1 ? "Generate Business Context" : "Continue";
  renderAnswers();
}

function renderAnswers() {
  answerStack.replaceChildren(
    ...answers.map((answer, index) => {
      const card = document.createElement("article");
      const label = document.createElement("span");
      const text = document.createElement("p");
      card.className = "answer-card";
      label.textContent = `Step ${index + 1}`;
      text.textContent = answer;
      card.append(label, text);
      return card;
    })
  );
}

function renderGeneratedContext() {
  const fields = Array.from(document.querySelectorAll(".knowledge-card input, .knowledge-card textarea"));
  const generatedValues = [
    answers[0],
    `${answers[0]} serves ${answers[2] || "customers"} with a clear, helpful AI assistant.`,
    answers[1],
    "Customer support, qualification, and handoff.",
    answers[4],
    "Use the preferred owner contact details.",
    "Business hours to be confirmed.",
    answers[3]
  ];

  fields.forEach((field, index) => {
    if (generatedValues[index]) {
      field.value = generatedValues[index];
    }
  });
}

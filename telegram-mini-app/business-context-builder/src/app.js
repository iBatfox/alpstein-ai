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

const bots = [
  {
    id: "instagram",
    name: "Instagram Bot",
    icon: "IG",
    source: "Instagram",
    status: "Connected",
    stats: {
      messagesToday: "42",
      leadsCreated: "6",
      lastMessageTime: "14:32",
      failedReplies: "1",
      conversionRate: "14%"
    },
    connection: {
      channelId: "ig_demo_channel_001",
      webhookStatus: "Receiving events",
      connectedBackend: "BCB bridge placeholder",
      crmSyncStatus: "Not connected"
    }
  },
  {
    id: "telegram",
    name: "Telegram Bot",
    icon: "TG",
    source: "Telegram",
    status: "Draft setup",
    stats: {
      messagesToday: "18",
      leadsCreated: "3",
      lastMessageTime: "13:58",
      failedReplies: "0",
      conversionRate: "17%"
    },
    connection: {
      channelId: "tg_demo_channel_001",
      webhookStatus: "Setup pending",
      connectedBackend: "BCB bridge placeholder",
      crmSyncStatus: "Not connected"
    }
  },
  {
    id: "whatsapp",
    name: "WhatsApp Bot",
    icon: "WA",
    source: "WhatsApp",
    status: "Ready for review",
    stats: {
      messagesToday: "9",
      leadsCreated: "2",
      lastMessageTime: "11:20",
      failedReplies: "0",
      conversionRate: "22%"
    },
    connection: {
      channelId: "wa_demo_channel_001",
      webhookStatus: "Review required",
      connectedBackend: "BCB bridge placeholder",
      crmSyncStatus: "Not connected"
    }
  },
  {
    id: "website",
    name: "Website Bot",
    icon: "Web",
    source: "Website Chat",
    status: "Disabled",
    stats: {
      messagesToday: "0",
      leadsCreated: "0",
      lastMessageTime: "No messages today",
      failedReplies: "0",
      conversionRate: "0%"
    },
    connection: {
      channelId: "web_demo_channel_001",
      webhookStatus: "Disabled",
      connectedBackend: "BCB bridge placeholder",
      crmSyncStatus: "Not connected"
    }
  }
];

const wizardSteps = [
  "What is your company name?",
  "What do you sell?",
  "Who are your customers?",
  "How should the assistant communicate?",
  "What questions do customers ask most often?"
];

const answers = [];
let currentStep = 0;

renderBots();
renderWizard();
verifyStartupAccess();

loginForm.addEventListener("submit", (event) => {
  event.preventDefault();
  if (apiMode !== "mock" || !localMockAllowed) return;
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
    showScreen("login");
    return;
  }

  showScreen("verifying");

  try {
    await requestAccessVerification();
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

function renderBots() {
  botGrid.replaceChildren(
    ...bots.map((bot) => {
      const card = document.createElement("article");
      const icon = document.createElement("div");
      const content = document.createElement("div");
      const title = document.createElement("h3");
      const status = document.createElement("p");
      const button = document.createElement("button");
      card.className = "bot-card";
      icon.className = "channel-icon";
      icon.setAttribute("aria-hidden", "true");
      icon.textContent = bot.icon;
      title.textContent = bot.name;
      status.textContent = bot.status;
      button.className = "secondary-button compact";
      button.type = "button";
      button.textContent = "Open channel";
      button.addEventListener("click", () => openChannelDetail(bot.id));
      content.append(title, status);
      card.append(icon, content, button);
      card.addEventListener("click", (event) => {
        if (event.target.closest("button")) return;
        openChannelDetail(bot.id);
      });
      return card;
    })
  );
}

function openChannelDetail(channelId) {
  const channel = bots.find((bot) => bot.id === channelId);
  if (!channel) return;
  channelTitle.textContent = channel.name;
  channelStatus.textContent = channel.status;
  renderChannelStats(channel.stats);
  renderChannelConnection(channel.connection);
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

function renderChannelConnection(connection) {
  const rows = [
    ["Channel ID", connection.channelId],
    ["Webhook status", connection.webhookStatus],
    ["Connected backend", connection.connectedBackend],
    ["CRM/ERP sync status", connection.crmSyncStatus]
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

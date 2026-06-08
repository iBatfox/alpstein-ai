import { createBusinessContextBuilderClient } from "./apiClient.js";

const apiMode = getConfigValue("api_mode", "mock");
const apiBaseUrl = getConfigValue("api_base_url", "");
const client = createBusinessContextBuilderClient({
  mode: apiMode,
  baseUrl: apiBaseUrl,
  initData: getTelegramInitData()
});

const INTERVIEW_STEPS = [
  "company_information",
  "business_description",
  "target_customers",
  "products_services",
  "sales_process",
  "communication_style"
];

const ACTIVE_SESSION_STORAGE_KEY = "bcb.activeSessionId";

const appState = {
  activeScreen: "contexts",
  session: null,
  messages: [],
  result: null,
  contexts: [],
  unfinishedSession: null,
  contextsError: "",
  unfinishedError: "",
  isBusy: false,
  limit: 20,
  offset: 0
};

const elements = {
  telegramStatus: document.getElementById("telegramStatus"),
  headerMenuButton: document.getElementById("headerMenuButton"),
  headerMenuPanel: document.getElementById("headerMenuPanel"),
  startInterviewButton: document.getElementById("startInterviewButton"),
  interviewBackButton: document.getElementById("interviewBackButton"),
  completeInterviewButton: document.getElementById("completeInterviewButton"),
  backToContextsButton: document.getElementById("backToContextsButton"),
  startAnotherContextButton: document.getElementById("startAnotherContextButton"),
  previousPageButton: document.getElementById("previousPageButton"),
  nextPageButton: document.getElementById("nextPageButton"),
  messageForm: document.getElementById("messageForm"),
  messageInput: document.getElementById("messageInput"),
  messageList: document.getElementById("messageList"),
  currentStepCount: document.getElementById("currentStepCount"),
  currentStepLabel: document.getElementById("currentStepLabel"),
  interviewStatus: document.getElementById("interviewStatus"),
  progressFill: document.getElementById("progressFill"),
  progressDots: document.getElementById("progressDots"),
  resultOutput: document.getElementById("resultOutput"),
  metadataGrid: document.getElementById("metadataGrid"),
  unfinishedSessionList: document.getElementById("unfinishedSessionList"),
  contextList: document.getElementById("contextList"),
  pageIndicator: document.getElementById("pageIndicator"),
  messageTemplate: document.getElementById("messageTemplate"),
  contextTemplate: document.getElementById("contextTemplate")
};

initializeTelegram();
bindEvents();
initializeApp();

function initializeTelegram() {
  const webApp = getTelegramWebApp();
  if (!webApp) {
    elements.telegramStatus.textContent = "Browser preview";
    return;
  }

  document.body.classList.add("telegram-themed");
  webApp.ready();
  webApp.expand();
  elements.telegramStatus.textContent = "Telegram";
}

function getTelegramWebApp() {
  return window.Telegram && window.Telegram.WebApp;
}

function getTelegramInitData() {
  const webApp = getTelegramWebApp();
  return (webApp && webApp.initData) || "";
}

function bindEvents() {
  elements.startInterviewButton.addEventListener("click", startInterview);
  elements.headerMenuButton.addEventListener("click", toggleHeaderMenu);
  elements.headerMenuPanel.addEventListener("click", handleHeaderMenuClick);
  document.addEventListener("click", handleDocumentClick);
  elements.interviewBackButton.addEventListener("click", openContexts);
  elements.completeInterviewButton.addEventListener("click", completeInterview);
  elements.backToContextsButton.addEventListener("click", openContexts);
  elements.startAnotherContextButton.addEventListener("click", startInterview);
  elements.previousPageButton.addEventListener("click", previousPage);
  elements.nextPageButton.addEventListener("click", nextPage);
  elements.messageForm.addEventListener("submit", sendMessage);
  elements.messageInput.addEventListener("keydown", handleComposerKeydown);
  elements.messageInput.addEventListener("input", renderControls);
}

async function initializeApp() {
  showScreen("contexts");
  await refreshContextsMenu();
  render();
}

async function startInterview() {
  closeHeaderMenu();
  setBusy(true);
  try {
    const data = await client.createSession();
    appState.session = data.session;
    appState.messages = [data.message];
    appState.result = null;
    appState.unfinishedSession = data.session;
    saveActiveSessionId(data.session.id);
    showScreen("interview");
  } catch (error) {
    pushSystemMessage(error.message);
    showScreen("interview");
  } finally {
    setBusy(false);
    render();
  }
}

async function continueSession(sessionId = getActiveSessionId()) {
  closeHeaderMenu();
  if (!sessionId) {
    appState.unfinishedError = "No unfinished interview is available.";
    showScreen("contexts");
    render();
    return;
  }
  setBusy(true);
  try {
    const data = await client.getSession({ sessionId });
    appState.session = data.session;
    appState.messages = data.messages || [];
    appState.result = data.result;
    if (isOpenSession(data.session)) {
      appState.unfinishedSession = data.session;
      saveActiveSessionId(data.session.id);
    } else {
      clearActiveSessionId();
      appState.unfinishedSession = null;
    }
    showScreen(data.result ? "result" : "interview");
  } catch (error) {
    clearActiveSessionId();
    appState.unfinishedSession = null;
    appState.unfinishedError =
      "The saved unfinished interview could not be loaded and was removed.";
    appState.messages = [];
    showScreen("contexts");
  } finally {
    setBusy(false);
    await refreshContexts();
    render();
  }
}

async function sendMessage(event) {
  event.preventDefault();
  if (!appState.session) return;
  const content = elements.messageInput.value.trim();
  if (!content) return;

  elements.messageInput.value = "";
  setBusy(true);
  renderControls();
  try {
    const data = await client.sendMessage({
      sessionId: appState.session.id,
      content
    });
    appState.session = data.session;
    appState.unfinishedSession = data.session;
    saveActiveSessionId(data.session.id);
    appState.messages.push(data.user_message, data.assistant_message);
  } catch (error) {
    pushSystemMessage(error.message);
  } finally {
    setBusy(false);
    render();
  }
}

async function completeInterview() {
  if (!appState.session) return;
  setBusy(true);
  try {
    const data = await client.completeSession({
      sessionId: appState.session.id
    });
    appState.session = data.session;
    appState.result = data.result;
    clearActiveSessionId();
    appState.unfinishedSession = null;
    await refreshContextsMenu();
    showScreen("result");
  } catch (error) {
    pushSystemMessage(error.message);
  } finally {
    setBusy(false);
    render();
  }
}

async function openContexts() {
  closeHeaderMenu();
  await refreshContextsMenu();
  showScreen("contexts");
  render();
}

async function refreshContextsMenu() {
  await Promise.all([refreshUnfinishedSession(), refreshContexts()]);
}

async function refreshUnfinishedSession() {
  const sessionId = getActiveSessionId();
  appState.unfinishedError = "";
  if (!sessionId) {
    appState.unfinishedSession = null;
    return;
  }

  try {
    const data = await client.getSession({ sessionId });
    if (isOpenSession(data.session)) {
      appState.unfinishedSession = data.session;
      return;
    }
    clearActiveSessionId();
    appState.unfinishedSession = null;
  } catch (error) {
    clearActiveSessionId();
    appState.unfinishedSession = null;
    appState.unfinishedError =
      "The saved unfinished interview could not be loaded and was removed.";
  }
}

async function refreshContexts() {
  appState.contextsError = "";
  try {
    const data = await client.listContexts({
      limit: appState.limit,
      offset: appState.offset
    });
    appState.contexts = data.items || [];
  } catch (error) {
    appState.contexts = [];
    appState.contextsError = error.message;
  }
}

async function previousPage() {
  appState.offset = Math.max(0, appState.offset - appState.limit);
  await openContexts();
}

async function nextPage() {
  appState.offset += appState.limit;
  await openContexts();
}

function showScreen(screenName) {
  appState.activeScreen = screenName;
  document.querySelectorAll(".screen").forEach((screen) => {
    screen.classList.toggle("screen-active", screen.dataset.screen === screenName);
  });
}

function render() {
  renderStep();
  renderMessages();
  renderResult();
  renderUnfinishedSession();
  renderContexts();
  renderControls();
}

function renderStep() {
  const step = appState.session && appState.session.current_step;
  const stepIndex = getStepIndex(step);
  const stepNumber = stepIndex + 1;
  const totalSteps = INTERVIEW_STEPS.length;
  const progressPercent = Math.round((stepNumber / totalSteps) * 100);

  elements.currentStepLabel.textContent = step ? formatStep(step) : "Company information";
  elements.currentStepCount.textContent = `Step ${stepNumber} of ${totalSteps}`;
  elements.interviewStatus.textContent = appState.isBusy ? "Assistant responding" : "Interview";
  elements.progressFill.style.width = `${progressPercent}%`;
  elements.progressDots.style.gridTemplateColumns = `repeat(${totalSteps}, minmax(0, 1fr))`;
  elements.progressDots.replaceChildren(
    ...INTERVIEW_STEPS.map((_, index) => {
      const dot = document.createElement("span");
      dot.className = "progress-dot";
      dot.classList.toggle("progress-dot-active", index <= stepIndex);
      return dot;
    })
  );
}

function renderMessages() {
  elements.messageList.replaceChildren();
  appState.messages.forEach((message) => {
    const node = elements.messageTemplate.content.firstElementChild.cloneNode(true);
    node.classList.add(`message-${message.role}`);
    node.querySelector(".message-avatar").textContent = getAvatarLabel(message.role);
    node.querySelector(".message-role").textContent = formatRole(message.role);
    node.querySelector(".message-text").textContent = message.content;
    elements.messageList.appendChild(node);
  });
  requestAnimationFrame(() => {
    elements.messageList.scrollTop = elements.messageList.scrollHeight;
  });
}

function renderResult() {
  if (!appState.result) {
    elements.resultOutput.textContent = "";
    elements.metadataGrid.replaceChildren();
    return;
  }

  elements.resultOutput.textContent = JSON.stringify(
    appState.result.structured_context,
    null,
    2
  );
  const metadata =
    (appState.result.structured_context &&
      appState.result.structured_context.generation_metadata) ||
    {};
  const rows = [
    ["generation_mode", metadata.generation_mode],
    ["fallback_used", stringifyValue(metadata.fallback_used)],
    ["prompt_version", metadata.prompt_version],
    ["provider", metadata.provider],
    ["model", metadata.model]
  ];
  elements.metadataGrid.replaceChildren(
    ...rows.map(([label, value]) => createMetadataItem(label, value || "Not available"))
  );
}

function renderContexts() {
  elements.contextList.replaceChildren();
  if (appState.contextsError) {
    const error = document.createElement("p");
    error.className = "empty-state";
    error.textContent = appState.contextsError;
    elements.contextList.appendChild(error);
  } else if (appState.contexts.length === 0) {
    const empty = document.createElement("p");
    empty.className = "empty-state";
    empty.textContent =
      "No draft contexts yet. Start an interview to create the first saved draft.";
    elements.contextList.appendChild(empty);
  } else {
    appState.contexts.forEach((context) => {
      const node = elements.contextTemplate.content.firstElementChild.cloneNode(true);
      node.querySelector("h3").textContent = getContextTitle(context);
      node.querySelector(".context-summary").textContent =
        context.generated_prompt || "Generated draft context.";
      renderContextMeta(node.querySelector(".context-meta"), context);
      node.querySelector("button").addEventListener("click", () => {
        appState.result = context;
        showScreen("result");
        render();
      });
      elements.contextList.appendChild(node);
    });
  }

  const page = Math.floor(appState.offset / appState.limit) + 1;
  elements.pageIndicator.textContent = `Page ${page}`;
  elements.previousPageButton.disabled = appState.offset === 0;
  elements.nextPageButton.disabled = appState.contexts.length < appState.limit;
}

function renderUnfinishedSession() {
  elements.unfinishedSessionList.replaceChildren();
  if (appState.unfinishedError) {
    const error = document.createElement("p");
    error.className = "empty-state";
    error.textContent = appState.unfinishedError;
    elements.unfinishedSessionList.appendChild(error);
    return;
  }

  if (!appState.unfinishedSession) {
    const empty = document.createElement("p");
    empty.className = "empty-state";
    empty.textContent = "No unfinished interview on this device.";
    elements.unfinishedSessionList.appendChild(empty);
    return;
  }

  const item = document.createElement("article");
  item.className = "unfinished-item";
  const content = document.createElement("div");
  const title = document.createElement("h3");
  const summary = document.createElement("p");
  const button = document.createElement("button");
  title.textContent = formatStep(appState.unfinishedSession.current_step || "company_information");
  summary.textContent = formatSessionSummary(appState.unfinishedSession);
  button.className = "secondary-button compact";
  button.type = "button";
  button.textContent = "Continue";
  button.addEventListener("click", () => continueSession(appState.unfinishedSession.id));
  content.append(title, summary);
  item.append(content, button);
  elements.unfinishedSessionList.appendChild(item);
}

function renderControls() {
  const sessionCanContinue = isOpenSession(appState.session);
  const canSend =
    sessionCanContinue && !appState.isBusy && elements.messageInput.value.trim().length > 0;
  const canComplete = sessionCanContinue && !appState.isBusy && hasUserMessage();

  elements.headerMenuPanel
    .querySelector('[data-menu-action="current"]')
    .toggleAttribute("disabled", !getActiveSessionId() && !isOpenSession(appState.session));
  elements.messageInput.disabled = !sessionCanContinue || appState.isBusy;
  elements.messageForm.querySelector(".send-button").disabled = !canSend;
  elements.completeInterviewButton.disabled = !canComplete;
  elements.completeInterviewButton.classList.toggle("complete-button-visible", canComplete);
}

function createMetadataItem(label, value) {
  const wrapper = document.createElement("div");
  const key = document.createElement("dt");
  const val = document.createElement("dd");
  key.textContent = label;
  val.textContent = value;
  wrapper.append(key, val);
  return wrapper;
}

function pushSystemMessage(content) {
  appState.messages.push({
    id: String(Date.now()),
    session_id: appState.session ? appState.session.id : "",
    role: "system",
    content,
    created_at: new Date().toISOString()
  });
}

function setBusy(isBusy) {
  appState.isBusy = isBusy;
  document.body.classList.toggle("is-busy", isBusy);
  document.querySelectorAll("button, textarea").forEach((element) => {
    if (element.dataset.staticDisabled === "true") return;
    element.disabled = isBusy;
  });
  renderStep();
}

function toggleHeaderMenu(event) {
  event.stopPropagation();
  const isOpen = !elements.headerMenuPanel.hidden;
  if (isOpen) {
    closeHeaderMenu();
    return;
  }
  elements.headerMenuPanel.hidden = false;
  elements.headerMenuButton.setAttribute("aria-expanded", "true");
}

function closeHeaderMenu() {
  elements.headerMenuPanel.hidden = true;
  elements.headerMenuButton.setAttribute("aria-expanded", "false");
}

function handleDocumentClick(event) {
  if (
    elements.headerMenuPanel.hidden ||
    elements.headerMenuPanel.contains(event.target) ||
    elements.headerMenuButton.contains(event.target)
  ) {
    return;
  }
  closeHeaderMenu();
}

function handleHeaderMenuClick(event) {
  const button = event.target.closest("button[data-menu-action]");
  if (!button || button.disabled) return;
  const action = button.dataset.menuAction;
  if (action === "contexts") {
    openContexts();
  } else if (action === "new") {
    startInterview();
  } else if (action === "current") {
    if (isOpenSession(appState.session)) {
      closeHeaderMenu();
      showScreen("interview");
      render();
    } else {
      continueSession();
    }
  }
}

function handleComposerKeydown(event) {
  if (event.key !== "Enter" || event.shiftKey || event.isComposing) return;
  event.preventDefault();
  elements.messageForm.requestSubmit();
}

function getConfigValue(name, fallback) {
  const params = new URLSearchParams(window.location.search);
  return params.get(name) || fallback;
}

function saveActiveSessionId(sessionId) {
  if (!sessionId) return;
  window.localStorage.setItem(ACTIVE_SESSION_STORAGE_KEY, sessionId);
}

function getActiveSessionId() {
  return window.localStorage.getItem(ACTIVE_SESSION_STORAGE_KEY) || "";
}

function clearActiveSessionId() {
  window.localStorage.removeItem(ACTIVE_SESSION_STORAGE_KEY);
}

function formatStep(step) {
  return step
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function formatRole(role) {
  if (role === "assistant") return "Assistant";
  if (role === "user") return "You";
  return "System";
}

function getAvatarLabel(role) {
  if (role === "assistant") return "AI";
  if (role === "system") return "!";
  return "";
}

function getStepIndex(step) {
  const index = INTERVIEW_STEPS.indexOf(step);
  if (index >= 0) return index;
  if (step === "completed") return INTERVIEW_STEPS.length - 1;
  return 0;
}

function isOpenSession(session) {
  return Boolean(
    session && ["active", "in_progress", "created"].includes(String(session.status))
  );
}

function hasUserMessage() {
  return appState.messages.some((message) => message.role === "user");
}

function stringifyValue(value) {
  if (value === true) return "true";
  if (value === false) return "false";
  return value == null ? "" : String(value);
}

function getContextTitle(context) {
  const structured = context.structured_context || {};
  const company = structured.company || {};
  return (
    structured.company_name ||
    structured.company_overview ||
    company.name ||
    context.company_name ||
    context.title ||
    "Draft context"
  );
}

function renderContextMeta(container, context) {
  const structured = context.structured_context || {};
  const metadata = structured.generation_metadata || context.generation_metadata || {};
  const chips = [
    context.status || "Draft",
    formatDate(context.updated_at || context.created_at),
    metadata.generation_mode,
    metadata.fallback_used === true ? "Fallback" : ""
  ].filter(Boolean);

  container.replaceChildren(
    ...chips.map((chip) => {
      const node = document.createElement("span");
      node.className = "meta-chip";
      node.textContent = chip;
      return node;
    })
  );
}

function formatDate(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric"
  }).format(date);
}

function formatSessionSummary(session) {
  const updated = formatDate(session.updated_at || session.created_at);
  const status = session.status || "in progress";
  return updated ? `${formatStep(status)} · Updated ${updated}` : formatStep(status);
}

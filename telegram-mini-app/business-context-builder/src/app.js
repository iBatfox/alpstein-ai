import { createBusinessContextBuilderClient } from "./apiClient.js";

const tenantId = getConfigValue("tenant_id", "00000000-0000-4000-8000-000000000001");
const businessId = getConfigValue("business_id", "00000000-0000-4000-8000-000000000002");
const apiMode = getConfigValue("api_mode", "mock");
const client = createBusinessContextBuilderClient({ mode: apiMode });

const appState = {
  activeScreen: "start",
  session: null,
  messages: [],
  result: null,
  contexts: [],
  limit: 20,
  offset: 0
};

const elements = {
  telegramStatus: document.getElementById("telegramStatus"),
  startInterviewButton: document.getElementById("startInterviewButton"),
  continueSessionButton: document.getElementById("continueSessionButton"),
  completeInterviewButton: document.getElementById("completeInterviewButton"),
  backToContextsButton: document.getElementById("backToContextsButton"),
  newContextButton: document.getElementById("newContextButton"),
  previousPageButton: document.getElementById("previousPageButton"),
  nextPageButton: document.getElementById("nextPageButton"),
  messageForm: document.getElementById("messageForm"),
  messageInput: document.getElementById("messageInput"),
  messageList: document.getElementById("messageList"),
  currentStepLabel: document.getElementById("currentStepLabel"),
  resultOutput: document.getElementById("resultOutput"),
  metadataGrid: document.getElementById("metadataGrid"),
  contextList: document.getElementById("contextList"),
  pageIndicator: document.getElementById("pageIndicator"),
  messageTemplate: document.getElementById("messageTemplate"),
  contextTemplate: document.getElementById("contextTemplate")
};

initializeTelegram();
bindEvents();
render();

function initializeTelegram() {
  const webApp = window.Telegram && window.Telegram.WebApp;
  if (!webApp) {
    elements.telegramStatus.textContent = "Browser preview";
    return;
  }

  document.body.classList.add("telegram-themed");
  webApp.ready();
  webApp.expand();
  elements.telegramStatus.textContent = "Telegram";
}

function bindEvents() {
  elements.startInterviewButton.addEventListener("click", startInterview);
  elements.continueSessionButton.addEventListener("click", continueSession);
  elements.completeInterviewButton.addEventListener("click", completeInterview);
  elements.backToContextsButton.addEventListener("click", openContexts);
  elements.newContextButton.addEventListener("click", () => showScreen("start"));
  elements.previousPageButton.addEventListener("click", previousPage);
  elements.nextPageButton.addEventListener("click", nextPage);
  elements.messageForm.addEventListener("submit", sendMessage);
}

async function startInterview() {
  setBusy(true);
  try {
    const data = await client.createSession({ tenantId, businessId });
    appState.session = data.session;
    appState.messages = [data.message];
    appState.result = null;
    showScreen("interview");
  } catch (error) {
    pushSystemMessage(error.message);
    showScreen("interview");
  } finally {
    setBusy(false);
    render();
  }
}

async function continueSession() {
  if (!appState.session) {
    await startInterview();
    return;
  }
  setBusy(true);
  try {
    const data = await client.getSession({ sessionId: appState.session.id });
    appState.session = data.session;
    appState.messages = data.messages;
    appState.result = data.result;
    showScreen(data.result ? "result" : "interview");
  } catch (error) {
    pushSystemMessage(error.message);
    showScreen("interview");
  } finally {
    setBusy(false);
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
  try {
    const data = await client.sendMessage({
      sessionId: appState.session.id,
      tenantId,
      businessId,
      content
    });
    appState.session = data.session;
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
      sessionId: appState.session.id,
      tenantId,
      businessId
    });
    appState.session = data.session;
    appState.result = data.result;
    await refreshContexts();
    showScreen("result");
  } catch (error) {
    pushSystemMessage(error.message);
  } finally {
    setBusy(false);
    render();
  }
}

async function openContexts() {
  await refreshContexts();
  showScreen("contexts");
  render();
}

async function refreshContexts() {
  const data = await client.listContexts({
    tenantId,
    businessId,
    limit: appState.limit,
    offset: appState.offset
  });
  appState.contexts = data.items;
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
  renderContexts();
  renderControls();
}

function renderStep() {
  const step = appState.session && appState.session.current_step;
  elements.currentStepLabel.textContent = step ? formatStep(step) : "Company information";
}

function renderMessages() {
  elements.messageList.replaceChildren();
  appState.messages.forEach((message) => {
    const node = elements.messageTemplate.content.firstElementChild.cloneNode(true);
    node.classList.add(`message-${message.role}`);
    node.querySelector(".message-role").textContent = formatRole(message.role);
    node.querySelector(".message-text").textContent = message.content;
    elements.messageList.appendChild(node);
  });
  elements.messageList.scrollTop = elements.messageList.scrollHeight;
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
  if (appState.contexts.length === 0) {
    const empty = document.createElement("p");
    empty.className = "empty-state";
    empty.textContent = "No draft contexts yet.";
    elements.contextList.appendChild(empty);
  } else {
    appState.contexts.forEach((context) => {
      const node = elements.contextTemplate.content.firstElementChild.cloneNode(true);
      node.querySelector("h3").textContent =
        context.structured_context.company_overview || "Draft context";
      node.querySelector("p").textContent = context.generated_prompt;
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

function renderControls() {
  elements.continueSessionButton.disabled =
    !appState.session || appState.session.status !== "active";
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
  document.querySelectorAll("button, textarea").forEach((element) => {
    element.disabled = isBusy;
  });
}

function getConfigValue(name, fallback) {
  const params = new URLSearchParams(window.location.search);
  return params.get(name) || fallback;
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

function stringifyValue(value) {
  if (value === true) return "true";
  if (value === false) return "false";
  return value == null ? "" : String(value);
}

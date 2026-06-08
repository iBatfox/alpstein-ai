import { createBusinessContextBuilderClient } from "./apiClient.js";

const INTERVIEW_STEPS = [
  "company_information",
  "business_description",
  "target_customers",
  "products_services",
  "sales_process",
  "communication_style"
];

const ACTIVE_SESSION_STORAGE_KEY = "bcb.activeSessionId";
const LANGUAGE_STORAGE_KEY = "bcb_language";
const SUPPORTED_LANGUAGES = [
  { code: "en", label: "English" },
  { code: "de", label: "Deutsch" },
  { code: "fr", label: "Français" },
  { code: "uk", label: "Українська" }
];

const TEXT = {
  en: {
    appTitle: "Business Context Builder",
    browserPreview: "Browser preview",
    telegram: "Telegram",
    language: "Language",
    contexts: "Contexts",
    interview: "Interview",
    bots: "Bots",
    more: "More",
    contextsTitle: "Business Contexts",
    contextsIntro: "Create and review draft business contexts from guided interviews.",
    createNewContext: "Create new context",
    continueInterview: "Continue interview",
    continueUnfinished: "Continue unfinished",
    currentInterview: "Current interview",
    draftContexts: "Draft contexts",
    savedDrafts: "Saved drafts",
    previous: "Previous",
    next: "Next",
    page: "Page",
    noDrafts: "No draft contexts yet. Start an interview to create the first saved draft.",
    noUnfinished: "No unfinished interview on this device.",
    noActiveInterview: "No active interview",
    noActiveInterviewCopy: "Create a context to start the guided interview.",
    createContext: "Create context",
    step: "Step",
    of: "of",
    assistantResponding: "Assistant responding",
    messagePlaceholder: "Type an answer",
    completeInterview: "Complete interview",
    draftResult: "Draft result",
    generatedContext: "Generated context",
    viewResult: "View result",
    backToContexts: "Back to contexts",
    startAnotherContext: "Start another context",
    chooseLanguage: "Choose language",
    botsTitle: "Bots and workflows",
    botsIntro: "UI foundation for owner-created bots and linked business contexts.",
    createBot: "Create bot",
    viewBot: "View bot",
    linkContext: "Link context",
    botPlaceholder: "Bot details are a placeholder until backend bot APIs exist.",
    noBots: "No bots available yet.",
    settings: "Settings",
    mode: "Mode",
    access: "Access",
    ownerOnly: "Owner only in bridge mode",
    backendLanguage: "Backend language",
    backendLanguageGap: "Not implemented yet",
    restrictedTitle: "Access is restricted.",
    restrictedCopy: "This Mini App is available only to allowed Telegram users.",
    notAvailable: "Not available",
    continue: "Continue",
    updated: "Updated",
    current: "Current",
    linkedContext: "Linked context",
    noLinkedContext: "No linked context",
    lastUpdated: "Last updated",
    comingSoon: "coming soon"
  },
  de: {
    appTitle: "Business Context Builder",
    browserPreview: "Browser Vorschau",
    telegram: "Telegram",
    language: "Sprache",
    contexts: "Kontexte",
    interview: "Interview",
    bots: "Bots",
    more: "Mehr",
    contextsTitle: "Business Kontexte",
    contextsIntro: "Erstelle und pruefe Kontextentwuerfe aus gefuehrten Interviews.",
    createNewContext: "Neuen Kontext erstellen",
    continueInterview: "Interview fortsetzen",
    continueUnfinished: "Offen fortsetzen",
    currentInterview: "Aktuelles Interview",
    draftContexts: "Kontextentwuerfe",
    savedDrafts: "Gespeicherte Entwuerfe",
    previous: "Zurueck",
    next: "Weiter",
    page: "Seite",
    noDrafts: "Noch keine Kontextentwuerfe. Starte ein Interview.",
    noUnfinished: "Kein offenes Interview auf diesem Geraet.",
    noActiveInterview: "Kein aktives Interview",
    noActiveInterviewCopy: "Erstelle einen Kontext, um das Interview zu starten.",
    createContext: "Kontext erstellen",
    step: "Schritt",
    of: "von",
    assistantResponding: "Assistent antwortet",
    messagePlaceholder: "Antwort eingeben",
    completeInterview: "Interview abschliessen",
    draftResult: "Entwurf",
    generatedContext: "Generierter Kontext",
    viewResult: "Entwurf ansehen",
    backToContexts: "Zurueck zu Kontexten",
    startAnotherContext: "Weiteren Kontext starten",
    chooseLanguage: "Sprache waehlen",
    botsTitle: "Bots und Workflows",
    botsIntro: "UI Grundlage fuer Bots des Owners und verknuepfte Business Kontexte.",
    createBot: "Bot erstellen",
    viewBot: "Bot ansehen",
    linkContext: "Kontext verknuepfen",
    botPlaceholder: "Bot Details sind Platzhalter, bis Backend APIs existieren.",
    noBots: "Noch keine Bots verfuegbar.",
    settings: "Einstellungen",
    mode: "Modus",
    access: "Zugriff",
    ownerOnly: "Nur Owner im Bridge Modus",
    backendLanguage: "Backend Sprache",
    backendLanguageGap: "Noch nicht implementiert",
    restrictedTitle: "Zugriff eingeschraenkt.",
    restrictedCopy: "Diese Mini App ist nur fuer erlaubte Telegram Nutzer verfuegbar.",
    notAvailable: "Nicht verfuegbar",
    continue: "Fortsetzen",
    updated: "Aktualisiert",
    current: "Aktuell",
    linkedContext: "Verknuepfter Kontext",
    noLinkedContext: "Kein verknuepfter Kontext",
    lastUpdated: "Zuletzt aktualisiert",
    comingSoon: "kommt spaeter"
  },
  fr: {
    appTitle: "Business Context Builder",
    browserPreview: "Apercu navigateur",
    telegram: "Telegram",
    language: "Langue",
    contexts: "Contextes",
    interview: "Entretien",
    bots: "Bots",
    more: "Plus",
    contextsTitle: "Contextes business",
    contextsIntro: "Creez et relisez des brouillons de contexte via des entretiens guides.",
    createNewContext: "Creer un contexte",
    continueInterview: "Continuer l'entretien",
    continueUnfinished: "Continuer",
    currentInterview: "Entretien actuel",
    draftContexts: "Brouillons",
    savedDrafts: "Brouillons sauvegardes",
    previous: "Precedent",
    next: "Suivant",
    page: "Page",
    noDrafts: "Aucun brouillon pour le moment. Lancez un entretien.",
    noUnfinished: "Aucun entretien inacheve sur cet appareil.",
    noActiveInterview: "Aucun entretien actif",
    noActiveInterviewCopy: "Creez un contexte pour commencer l'entretien guide.",
    createContext: "Creer un contexte",
    step: "Etape",
    of: "sur",
    assistantResponding: "L'assistant repond",
    messagePlaceholder: "Tapez une reponse",
    completeInterview: "Terminer l'entretien",
    draftResult: "Brouillon",
    generatedContext: "Contexte genere",
    viewResult: "Voir le resultat",
    backToContexts: "Retour aux contextes",
    startAnotherContext: "Creer un autre contexte",
    chooseLanguage: "Choisir la langue",
    botsTitle: "Bots et workflows",
    botsIntro: "Base UI pour les bots du proprietaire et les contextes lies.",
    createBot: "Creer un bot",
    viewBot: "Voir le bot",
    linkContext: "Lier contexte",
    botPlaceholder: "Les details du bot sont provisoires jusqu'aux APIs backend.",
    noBots: "Aucun bot disponible.",
    settings: "Parametres",
    mode: "Mode",
    access: "Acces",
    ownerOnly: "Proprietaire uniquement en mode bridge",
    backendLanguage: "Langue backend",
    backendLanguageGap: "Pas encore implemente",
    restrictedTitle: "Acces restreint.",
    restrictedCopy: "Cette Mini App est reservee aux utilisateurs Telegram autorises.",
    notAvailable: "Non disponible",
    continue: "Continuer",
    updated: "Mis a jour",
    current: "Actuel",
    linkedContext: "Contexte lie",
    noLinkedContext: "Aucun contexte lie",
    lastUpdated: "Derniere mise a jour",
    comingSoon: "bientot"
  },
  uk: {
    appTitle: "Business Context Builder",
    browserPreview: "Перегляд у браузері",
    telegram: "Telegram",
    language: "Мова",
    contexts: "Контексти",
    interview: "Інтерв'ю",
    bots: "Боти",
    more: "Ще",
    contextsTitle: "Бізнес-контексти",
    contextsIntro: "Створюйте та переглядайте чернетки бізнес-контекстів з інтерв'ю.",
    createNewContext: "Створити контекст",
    continueInterview: "Продовжити інтерв'ю",
    continueUnfinished: "Продовжити",
    currentInterview: "Поточне інтерв'ю",
    draftContexts: "Чернетки",
    savedDrafts: "Збережені чернетки",
    previous: "Назад",
    next: "Далі",
    page: "Сторінка",
    noDrafts: "Чернеток ще немає. Почніть інтерв'ю.",
    noUnfinished: "На цьому пристрої немає незавершеного інтерв'ю.",
    noActiveInterview: "Немає активного інтерв'ю",
    noActiveInterviewCopy: "Створіть контекст, щоб почати інтерв'ю.",
    createContext: "Створити контекст",
    step: "Крок",
    of: "з",
    assistantResponding: "Асистент відповідає",
    messagePlaceholder: "Введіть відповідь",
    completeInterview: "Завершити інтерв'ю",
    draftResult: "Чернетка",
    generatedContext: "Згенерований контекст",
    viewResult: "Переглянути результат",
    backToContexts: "До контекстів",
    startAnotherContext: "Створити ще один",
    chooseLanguage: "Оберіть мову",
    botsTitle: "Боти та workflow",
    botsIntro: "UI-основа для ботів власника та пов'язаних бізнес-контекстів.",
    createBot: "Створити бота",
    viewBot: "Переглянути бота",
    linkContext: "Пов'язати контекст",
    botPlaceholder: "Дані бота є заглушкою, доки немає backend API.",
    noBots: "Ботів ще немає.",
    settings: "Налаштування",
    mode: "Режим",
    access: "Доступ",
    ownerOnly: "Лише власник у bridge режимі",
    backendLanguage: "Мова backend",
    backendLanguageGap: "Ще не реалізовано",
    restrictedTitle: "Доступ обмежено.",
    restrictedCopy: "Ця Mini App доступна лише дозволеним користувачам Telegram.",
    notAvailable: "Недоступно",
    continue: "Продовжити",
    updated: "Оновлено",
    current: "Поточна",
    linkedContext: "Пов'язаний контекст",
    noLinkedContext: "Немає пов'язаного контексту",
    lastUpdated: "Останнє оновлення",
    comingSoon: "скоро"
  }
};

const apiMode = getConfigValue("api_mode", "mock");
const apiBaseUrl = getConfigValue("api_base_url", "");

let selectedLanguage = getStoredLanguage();
let client = createClient();

const appState = {
  activeScreen: "contexts",
  activeTab: "contexts",
  accessRestricted: false,
  session: null,
  messages: [],
  result: null,
  contexts: [],
  bots: [],
  unfinishedSession: null,
  contextsError: "",
  botsError: "",
  unfinishedError: "",
  isBusy: false,
  limit: 20,
  offset: 0
};

const elements = {
  telegramStatus: document.getElementById("telegramStatus"),
  bottomNav: document.getElementById("bottomNav"),
  startInterviewButton: document.getElementById("startInterviewButton"),
  continueInterviewButton: document.getElementById("continueInterviewButton"),
  interviewCreateButton: document.getElementById("interviewCreateButton"),
  completeInterviewButton: document.getElementById("completeInterviewButton"),
  backToContextsButton: document.getElementById("backToContextsButton"),
  startAnotherContextButton: document.getElementById("startAnotherContextButton"),
  previousPageButton: document.getElementById("previousPageButton"),
  nextPageButton: document.getElementById("nextPageButton"),
  createBotButton: document.getElementById("createBotButton"),
  messageForm: document.getElementById("messageForm"),
  messageInput: document.getElementById("messageInput"),
  messageList: document.getElementById("messageList"),
  currentStepCount: document.getElementById("currentStepCount"),
  currentStepLabel: document.getElementById("currentStepLabel"),
  interviewStatus: document.getElementById("interviewStatus"),
  progressFill: document.getElementById("progressFill"),
  progressDots: document.getElementById("progressDots"),
  interviewEmptyState: document.getElementById("interviewEmptyState"),
  interviewActiveState: document.getElementById("interviewActiveState"),
  resultOutput: document.getElementById("resultOutput"),
  metadataGrid: document.getElementById("metadataGrid"),
  unfinishedSessionList: document.getElementById("unfinishedSessionList"),
  contextList: document.getElementById("contextList"),
  languageList: document.getElementById("languageList"),
  botList: document.getElementById("botList"),
  pageIndicator: document.getElementById("pageIndicator"),
  modeValue: document.getElementById("modeValue"),
  messageTemplate: document.getElementById("messageTemplate"),
  contextTemplate: document.getElementById("contextTemplate"),
  botTemplate: document.getElementById("botTemplate")
};

initializeTelegram();
bindEvents();
initializeApp();

function createClient() {
  return createBusinessContextBuilderClient({
    mode: apiMode,
    baseUrl: apiBaseUrl,
    initData: getTelegramInitData(),
    language: selectedLanguage
  });
}

function initializeTelegram() {
  const webApp = getTelegramWebApp();
  if (!webApp) {
    elements.telegramStatus.textContent = t("browserPreview");
    return;
  }

  document.body.classList.add("telegram-themed");
  webApp.ready();
  webApp.expand();
  elements.telegramStatus.textContent = t("telegram");
}

function getTelegramWebApp() {
  return window.Telegram && window.Telegram.WebApp;
}

function getTelegramInitData() {
  const webApp = getTelegramWebApp();
  return (webApp && webApp.initData) || "";
}

function bindEvents() {
  elements.bottomNav.addEventListener("click", handleBottomNavClick);
  elements.startInterviewButton.addEventListener("click", startInterview);
  elements.continueInterviewButton.addEventListener("click", () => continueSession());
  elements.interviewCreateButton.addEventListener("click", startInterview);
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
  applyTranslations();
  renderLanguageOptions();
  renderBottomNav();
  if (apiMode === "bridge") {
    try {
      await client.authSession();
    } catch (error) {
      if (isAccessRestrictedError(error)) {
        showRestricted();
        return;
      }
    }
  }
  await refreshContextsMenu();
  await refreshBots();
  showScreen("contexts");
  render();
}

async function startInterview() {
  if (appState.accessRestricted) return;
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
    handleError(error, "messages");
  } finally {
    setBusy(false);
    render();
  }
}

async function continueSession(sessionId = getActiveSessionId()) {
  if (appState.accessRestricted) return;
  if (!sessionId) {
    showScreen("interview");
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
    if (handleError(error)) return;
    clearActiveSessionId();
    appState.unfinishedSession = null;
    appState.unfinishedError =
      "The saved unfinished interview could not be loaded and was removed.";
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
    handleError(error, "messages");
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
    handleError(error, "messages");
  } finally {
    setBusy(false);
    render();
  }
}

async function openContexts() {
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
    if (isAccessRestrictedError(error)) {
      showRestricted();
      return;
    }
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
    if (isAccessRestrictedError(error)) {
      showRestricted();
      return;
    }
    appState.contexts = [];
    appState.contextsError = error.message;
  }
}

async function refreshBots() {
  appState.botsError = "";
  try {
    const data = await client.listBots();
    appState.bots = data.items || [];
  } catch (error) {
    if (isAccessRestrictedError(error)) {
      showRestricted();
      return;
    }
    appState.bots = [];
    appState.botsError = error.message;
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

function handleBottomNavClick(event) {
  const button = event.target.closest("button[data-tab]");
  if (!button || appState.accessRestricted) return;
  const tab = button.dataset.tab;
  if (tab === "interview" && !isOpenSession(appState.session)) {
    showScreen("interview");
  } else if (tab === "contexts") {
    openContexts();
    return;
  } else if (tab === "bots") {
    refreshBots().then(() => {
      showScreen("bots");
      render();
    });
    return;
  } else {
    showScreen(tab);
  }
  render();
}

function showScreen(screenName) {
  appState.activeScreen = screenName;
  appState.activeTab = screenName === "result" ? "contexts" : screenName;
  document.querySelectorAll(".screen").forEach((screen) => {
    screen.classList.toggle("screen-active", screen.dataset.screen === screenName);
  });
  renderBottomNav();
}

function showRestricted() {
  appState.accessRestricted = true;
  clearActiveSessionId();
  appState.session = null;
  appState.messages = [];
  appState.contexts = [];
  appState.bots = [];
  showScreen("restricted");
  elements.bottomNav.hidden = true;
  render();
}

function render() {
  applyTranslations();
  renderStep();
  renderMessages();
  renderResult();
  renderUnfinishedSession();
  renderContexts();
  renderLanguageOptions();
  renderBots();
  renderInterviewState();
  renderControls();
}

function applyTranslations() {
  document.documentElement.lang = selectedLanguage;
  setText("appTitle", t("appTitle"));
  setText("contextsTitle", t("contextsTitle"));
  setText("contextsIntro", t("contextsIntro"));
  setText("startInterviewButton", t("createNewContext"));
  setText("continueInterviewButton", t("continueInterview"));
  setText("currentInterviewEyebrow", t("continueUnfinished"));
  setText("currentInterviewTitle", t("currentInterview"));
  setText("draftContextsEyebrow", t("draftContexts"));
  setText("draftContextsTitle", t("savedDrafts"));
  setText("previousPageButton", t("previous"));
  setText("nextPageButton", t("next"));
  setText("interviewEmptyTitle", t("noActiveInterview"));
  setText("interviewEmptyCopy", t("noActiveInterviewCopy"));
  setText("interviewCreateButton", t("createContext"));
  setText("completeInterviewButton", t("completeInterview"));
  setText("resultEyebrow", t("draftResult"));
  setText("resultTitle", t("generatedContext"));
  setText("backToContextsButton", t("backToContexts"));
  setText("startAnotherContextButton", t("startAnotherContext"));
  setText("languageEyebrow", t("language"));
  setText("languageTitle", t("chooseLanguage"));
  setText("botsEyebrow", t("bots"));
  setText("botsTitle", t("botsTitle"));
  setText("botsIntro", t("botsIntro"));
  setText("createBotButton", `${t("createBot")} · ${t("comingSoon")}`);
  setText("moreEyebrow", t("more"));
  setText("moreTitle", t("settings"));
  setText("modeLabel", t("mode"));
  setText("modeValue", apiMode);
  setText("accessLabel", t("access"));
  setText("accessValue", t("ownerOnly"));
  setText("languageGapLabel", t("backendLanguage"));
  setText("languageGapValue", t("backendLanguageGap"));
  setText("restrictedTitle", t("restrictedTitle"));
  setText("restrictedCopy", t("restrictedCopy"));
  elements.messageInput.placeholder = t("messagePlaceholder");
  elements.telegramStatus.textContent = getTelegramWebApp() ? t("telegram") : t("browserPreview");
  elements.bottomNav.querySelector('[data-tab="language"] span').textContent = t("language");
  elements.bottomNav.querySelector('[data-tab="contexts"] span').textContent = t("contexts");
  elements.bottomNav.querySelector('[data-tab="interview"] span').textContent = t("interview");
  elements.bottomNav.querySelector('[data-tab="bots"] span').textContent = t("bots");
  elements.bottomNav.querySelector('[data-tab="more"] span').textContent = t("more");
}

function renderBottomNav() {
  elements.bottomNav.querySelectorAll("button[data-tab]").forEach((button) => {
    const isActive = button.dataset.tab === appState.activeTab;
    button.classList.toggle("bottom-nav-active", isActive);
    button.setAttribute("aria-current", isActive ? "page" : "false");
  });
}

function renderInterviewState() {
  const active = isOpenSession(appState.session);
  elements.interviewEmptyState.hidden = active;
  elements.interviewActiveState.hidden = !active;
}

function renderStep() {
  const step = appState.session && appState.session.current_step;
  const stepIndex = getStepIndex(step);
  const stepNumber = stepIndex + 1;
  const totalSteps = INTERVIEW_STEPS.length;
  const progressPercent = Math.round((stepNumber / totalSteps) * 100);

  elements.currentStepLabel.textContent = step ? formatStep(step) : formatStep("company_information");
  elements.currentStepCount.textContent = `${t("step")} ${stepNumber} ${t("of")} ${totalSteps}`;
  elements.interviewStatus.textContent = appState.isBusy ? t("assistantResponding") : t("interview");
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
    ...rows.map(([label, value]) => createMetadataItem(label, value || t("notAvailable")))
  );
}

function renderContexts() {
  elements.contextList.replaceChildren();
  if (appState.contextsError) {
    elements.contextList.appendChild(createEmptyState(appState.contextsError));
  } else if (appState.contexts.length === 0) {
    elements.contextList.appendChild(createEmptyState(t("noDrafts")));
  } else {
    appState.contexts.forEach((context) => {
      const node = elements.contextTemplate.content.firstElementChild.cloneNode(true);
      node.querySelector("h3").textContent = getContextTitle(context);
      node.querySelector(".context-summary").textContent =
        context.generated_prompt || "Generated draft context.";
      renderContextMeta(node.querySelector(".context-meta"), context);
      node.querySelector("button").textContent = t("viewResult");
      node.querySelector("button").addEventListener("click", () => {
        appState.result = context;
        showScreen("result");
        render();
      });
      elements.contextList.appendChild(node);
    });
  }

  const page = Math.floor(appState.offset / appState.limit) + 1;
  elements.pageIndicator.textContent = `${t("page")} ${page}`;
  elements.previousPageButton.disabled = appState.offset === 0;
  elements.nextPageButton.disabled = appState.contexts.length < appState.limit;
}

function renderUnfinishedSession() {
  elements.unfinishedSessionList.replaceChildren();
  if (appState.unfinishedError) {
    elements.unfinishedSessionList.appendChild(createEmptyState(appState.unfinishedError));
    return;
  }

  if (!appState.unfinishedSession) {
    elements.unfinishedSessionList.appendChild(createEmptyState(t("noUnfinished")));
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
  button.textContent = t("continue");
  button.addEventListener("click", () => continueSession(appState.unfinishedSession.id));
  content.append(title, summary);
  item.append(content, button);
  elements.unfinishedSessionList.appendChild(item);
}

function renderLanguageOptions() {
  elements.languageList.replaceChildren(
    ...SUPPORTED_LANGUAGES.map((language) => {
      const button = document.createElement("button");
      button.className = "language-option";
      button.type = "button";
      button.dataset.language = language.code;
      button.classList.toggle("language-option-active", language.code === selectedLanguage);
      button.innerHTML = `<span>${language.label}</span><strong>${language.code}</strong>`;
      button.addEventListener("click", () => selectLanguage(language.code));
      return button;
    })
  );
}

function renderBots() {
  elements.botList.replaceChildren();
  if (appState.botsError) {
    elements.botList.appendChild(createEmptyState(appState.botsError));
    return;
  }
  if (appState.bots.length === 0) {
    elements.botList.appendChild(createEmptyState(t("noBots")));
    return;
  }
  appState.bots.forEach((bot) => {
    const node = elements.botTemplate.content.firstElementChild.cloneNode(true);
    node.querySelector("h3").textContent = bot.name || "Bot";
    node.querySelector(".meta-chip").textContent = bot.status || "draft";
    node.querySelector(".bot-source").textContent = bot.source || "Other";
    node.querySelector(".bot-context").textContent = bot.context_title
      ? `${t("linkedContext")}: ${bot.context_title} (${bot.context_id})`
      : t("noLinkedContext");
    node.querySelector(".bot-updated").textContent = bot.updated_at
      ? `${t("lastUpdated")}: ${formatDate(bot.updated_at)}`
      : "";
    node.querySelector('[data-bot-action="view"]').textContent = t("viewBot");
    node.querySelector('[data-bot-action="view"]').addEventListener("click", () => {
      appState.botsError = t("botPlaceholder");
      renderBots();
    });
    const disabledButtons = node.querySelectorAll("button:disabled");
    disabledButtons[0].textContent = `${t("createBot")} · ${t("comingSoon")}`;
    disabledButtons[1].textContent = `${t("linkContext")} · ${t("comingSoon")}`;
    elements.botList.appendChild(node);
  });
}

function selectLanguage(languageCode) {
  selectedLanguage = languageCode;
  window.localStorage.setItem(LANGUAGE_STORAGE_KEY, selectedLanguage);
  if (!isOpenSession(appState.session)) {
    client = createClient();
  }
  applyTranslations();
  render();
}

function renderControls() {
  const sessionCanContinue = isOpenSession(appState.session);
  const canSend =
    sessionCanContinue && !appState.isBusy && elements.messageInput.value.trim().length > 0;
  const canComplete = sessionCanContinue && !appState.isBusy && hasUserMessage();

  elements.continueInterviewButton.disabled = !getActiveSessionId() && !sessionCanContinue;
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

function createEmptyState(content) {
  const empty = document.createElement("p");
  empty.className = "empty-state";
  empty.textContent = content;
  return empty;
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
    if (element.closest(".bottom-nav")) return;
    if (element.dataset.staticDisabled === "true") return;
    element.disabled = isBusy;
  });
  renderStep();
}

function handleComposerKeydown(event) {
  if (event.key !== "Enter" || event.shiftKey || event.isComposing) return;
  event.preventDefault();
  elements.messageForm.requestSubmit();
}

function handleError(error, target = "") {
  if (isAccessRestrictedError(error)) {
    showRestricted();
    return true;
  }
  if (target === "messages") {
    pushSystemMessage(error.message);
    return false;
  }
  return false;
}

function isAccessRestrictedError(error) {
  return error && (error.status === 403 || error.code === "TELEGRAM_USER_NOT_ALLOWED");
}

function getConfigValue(name, fallback) {
  const params = new URLSearchParams(window.location.search);
  return params.get(name) || fallback;
}

function getStoredLanguage() {
  const value = window.localStorage.getItem(LANGUAGE_STORAGE_KEY);
  return SUPPORTED_LANGUAGES.some((language) => language.code === value) ? value : "en";
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

function t(key) {
  return (TEXT[selectedLanguage] && TEXT[selectedLanguage][key]) || TEXT.en[key] || key;
}

function setText(id, value) {
  const element = document.getElementById(id);
  if (element) element.textContent = value;
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
  return new Intl.DateTimeFormat(selectedLanguage, {
    year: "numeric",
    month: "short",
    day: "numeric"
  }).format(date);
}

function formatSessionSummary(session) {
  const updated = formatDate(session.updated_at || session.created_at);
  const status = session.status || "in progress";
  return updated ? `${formatStep(status)} · ${t("updated")} ${updated}` : formatStep(status);
}

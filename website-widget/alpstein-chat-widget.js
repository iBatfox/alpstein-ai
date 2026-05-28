(function () {
  var widgetScript = document.currentScript;
  if (!widgetScript) {
    var scripts = document.getElementsByTagName("script");
    widgetScript = scripts[scripts.length - 1];
  }

  function createId(prefix) {
    if (window.crypto && typeof window.crypto.randomUUID === "function") {
      return prefix + window.crypto.randomUUID();
    }
    return prefix + Date.now() + "-" + Math.random().toString(16).slice(2);
  }

  function createCorrelationId() {
    var cryptoObj = window.crypto || window.msCrypto;
    if (cryptoObj && typeof cryptoObj.randomUUID === "function") {
      return cryptoObj.randomUUID();
    }
    if (cryptoObj && typeof cryptoObj.getRandomValues === "function") {
      var bytes = new Uint8Array(16);
      cryptoObj.getRandomValues(bytes);
      bytes[6] = (bytes[6] & 15) | 64;
      bytes[8] = (bytes[8] & 63) | 128;
      var hex = [];
      for (var i = 0; i < bytes.length; i += 1) {
        hex.push(bytes[i].toString(16).padStart(2, "0"));
      }
      return (
        hex.slice(0, 4).join("") +
        "-" +
        hex.slice(4, 6).join("") +
        "-" +
        hex.slice(6, 8).join("") +
        "-" +
        hex.slice(8, 10).join("") +
        "-" +
        hex.slice(10, 16).join("")
      );
    }
    createCorrelationId._counter = (createCorrelationId._counter || 0) + 1;
    var seedInput =
      (navigator.userAgent || "") +
      "|" +
      (window.location && window.location.href ? window.location.href : "") +
      "|" +
      String(createCorrelationId._counter);
    var seed = 2166136261;
    for (var j = 0; j < seedInput.length; j += 1) {
      seed ^= seedInput.charCodeAt(j);
      seed = Math.imul(seed, 16777619);
    }
    var fallback = new Uint8Array(16);
    var state = seed >>> 0;
    for (var k = 0; k < fallback.length; k += 1) {
      state ^= state << 13;
      state ^= state >>> 17;
      state ^= state << 5;
      fallback[k] = state & 255;
    }
    fallback[6] = (fallback[6] & 15) | 64;
    fallback[8] = (fallback[8] & 63) | 128;
    var fallbackHex = [];
    for (var m = 0; m < fallback.length; m += 1) {
      fallbackHex.push(fallback[m].toString(16).padStart(2, "0"));
    }
    return (
      fallbackHex.slice(0, 4).join("") +
      "-" +
      fallbackHex.slice(4, 6).join("") +
      "-" +
      fallbackHex.slice(6, 8).join("") +
      "-" +
      fallbackHex.slice(8, 10).join("") +
      "-" +
      fallbackHex.slice(10, 16).join("")
    );
  }

  function getOrCreateStorageValue(key, prefix) {
    try {
      var existing = localStorage.getItem(key);
      if (existing && existing.trim() !== "") {
        return existing;
      }
      var next = createId(prefix);
      localStorage.setItem(key, next);
      return next;
    } catch (error) {
      return createId(prefix);
    }
  }

  function createWidget() {
    var script = widgetScript;
    if (!script) return;

    var webhookUrl = script.getAttribute("data-webhook-url");
    var businessId = script.getAttribute("data-business-id");
    var title = script.getAttribute("data-title") || "Chat with us";

    if (!webhookUrl || !businessId) {
      console.error("Alpstein widget requires data-webhook-url and data-business-id.");
      return;
    }

    var visitorId = getOrCreateStorageValue("alpstein_visitor_id", "v_");
    var sessionId = createId("s_");
    var inFlight = false;

    var root = document.createElement("div");
    root.style.cssText =
      "position:fixed;bottom:20px;right:20px;width:340px;font-family:Arial,sans-serif;" +
      "z-index:99999;border:1px solid #d9d9d9;border-radius:10px;background:#fff;box-shadow:0 4px 16px rgba(0,0,0,0.15);";

    var header = document.createElement("div");
    header.textContent = title;
    header.style.cssText =
      "padding:10px 12px;background:#111827;color:#fff;border-radius:10px 10px 0 0;font-size:14px;";

    var messages = document.createElement("div");
    messages.style.cssText =
      "height:280px;overflow:auto;padding:10px;background:#f9fafb;border-bottom:1px solid #e5e7eb;";

    var inputWrap = document.createElement("div");
    inputWrap.style.cssText = "display:flex;gap:8px;padding:10px;";

    var input = document.createElement("textarea");
    input.rows = 2;
    input.placeholder = "Type your message...";
    input.style.cssText =
      "flex:1;resize:none;border:1px solid #cbd5e1;border-radius:6px;padding:8px;font-size:14px;";

    var send = document.createElement("button");
    send.textContent = "Send";
    send.style.cssText =
      "width:72px;border:0;border-radius:6px;background:#2563eb;color:#fff;font-weight:600;cursor:pointer;";

    function pushMessage(role, text) {
      var line = document.createElement("div");
      line.style.cssText =
        "margin-bottom:8px;padding:8px 10px;border-radius:8px;max-width:85%;white-space:pre-wrap;word-break:break-word;";
      if (role === "user") {
        line.style.marginLeft = "auto";
        line.style.background = "#dbeafe";
      } else if (role === "system") {
        line.style.background = "#fee2e2";
      } else {
        line.style.background = "#e5e7eb";
      }
      line.textContent = text;
      messages.appendChild(line);
      messages.scrollTop = messages.scrollHeight;
    }

    async function sendMessage() {
      if (inFlight) return;
      var text = input.value.trim();
      if (!text) return;
      inFlight = true;
      send.disabled = true;
      send.style.opacity = "0.6";

      var messageId = createId("m_");
      pushMessage("user", text);
      input.value = "";
      pushMessage("assistant", "...");

      var payload = {
        business_id: businessId,
        visitor_id: visitorId,
        session_id: sessionId,
        message_id: messageId,
        text: text,
        timestamp: new Date().toISOString(),
        language: navigator.language || null,
        page_url: window.location.href,
        referrer: document.referrer || null,
        utm_source: new URLSearchParams(window.location.search).get("utm_source"),
        utm_medium: new URLSearchParams(window.location.search).get("utm_medium"),
        utm_campaign: new URLSearchParams(window.location.search).get("utm_campaign"),
        utm_content: new URLSearchParams(window.location.search).get("utm_content"),
        utm_term: new URLSearchParams(window.location.search).get("utm_term"),
        user_agent: navigator.userAgent || null
      };

      try {
        var response = await fetch(webhookUrl, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Correlation-Id": createCorrelationId()
          },
          body: JSON.stringify(payload)
        });

        var body = await response.json();
        messages.removeChild(messages.lastChild);

        if (!response.ok || body.success !== true) {
          throw new Error((body.error && body.error.message) || "Temporary failure");
        }

        pushMessage("assistant", body.message && body.message.text ? body.message.text : "Thank you.");
      } catch (error) {
        messages.removeChild(messages.lastChild);
        pushMessage("system", "Sorry, message failed. Please retry.");
        input.value = text;
      } finally {
        inFlight = false;
        send.disabled = false;
        send.style.opacity = "1";
        input.focus();
      }
    }

    send.addEventListener("click", sendMessage);
    input.addEventListener("keydown", function (event) {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
      }
    });

    inputWrap.appendChild(input);
    inputWrap.appendChild(send);
    root.appendChild(header);
    root.appendChild(messages);
    root.appendChild(inputWrap);
    document.body.appendChild(root);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", createWidget);
  } else {
    createWidget();
  }
})();

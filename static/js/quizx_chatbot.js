(function () {
  document.addEventListener("DOMContentLoaded", function () {
    // Avoid double init
    if (window.__quizxChatbotInitialized) return;
    window.__quizxChatbotInitialized = true;

    // Floating button
    const launcher = document.createElement("button");
    launcher.id = "quizx-chat-launcher";
    launcher.type = "button";
    launcher.innerHTML = '<i class="fas fa-robot"></i>';
    Object.assign(launcher.style, {
      position: "fixed",
      right: "20px",
      bottom: "20px",
      width: "56px",
      height: "56px",
      borderRadius: "50%",
      border: "none",
      background: "#0f172a",
      color: "#e5e7eb",
      boxShadow: "0 14px 30px rgba(15,23,42,0.4)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      cursor: "pointer",
      zIndex: 9999,
      fontSize: "22px",
    });

    // Chat panel
    const panel = document.createElement("div");
    panel.id = "quizx-chat-panel";
    Object.assign(panel.style, {
      position: "fixed",
      right: "20px",
      bottom: "90px",
      width: "320px",
      maxHeight: "420px",
      background: "#0b1220",
      color: "#e5e7eb",
      borderRadius: "18px",
      boxShadow: "0 24px 60px rgba(15,23,42,0.6)",
      overflow: "hidden",
      display: "none",
      flexDirection: "column",
      zIndex: 9999,
      fontFamily: "'Plus Jakarta Sans', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    });

    panel.innerHTML = `
      <div style="padding:10px 14px;border-bottom:1px solid rgba(148,163,184,0.2);display:flex;align-items:center;justify-content:space-between;background:linear-gradient(135deg,#0f172a,#020617);">
        <div style="display:flex;align-items:center;gap:8px;">
          <div style="width:26px;height:26px;border-radius:999px;background:rgba(15,118,110,0.15);display:flex;align-items:center;justify-content:center;">
            <i class="fas fa-robot" style="font-size:14px;color:#22c55e;"></i>
          </div>
          <div>
            <div style="font-size:0.85rem;font-weight:600;">QuizX AI</div>
            <div id="quizx-chat-status" style="font-size:0.7rem;color:#22c55e;">Online · Ready</div>
          </div>
        </div>
        <button type="button" id="quizx-chat-close" style="border:none;background:none;color:#9ca3af;font-size:14px;cursor:pointer;">
          <i class="fas fa-xmark"></i>
        </button>
      </div>
      <div id="quizx-chat-messages" style="flex:1;padding:10px 12px;overflow-y:auto;font-size:0.78rem;background:radial-gradient(circle at top left,#0f172a,#020617);">
        <div style="color:#9ca3af;">Hi! I’m QuizX AI. Ask me anything about quizzes, MCQs, or exam prep.</div>
      </div>
      <form id="quizx-chat-form" style="padding:8px 10px;border-top:1px solid rgba(148,163,184,0.2);background:#020617;">
        <div style="display:flex;align-items:center;gap:6px;">
          <input
            id="quizx-chat-input"
            type="text"
            autocomplete="off"
            placeholder="Ask a question..."
            style="flex:1;border-radius:999px;border:1px solid rgba(148,163,184,0.5);background:#020617;color:#e5e7eb;padding:6px 10px;font-size:0.78rem;outline:none;"
          />
          <button type="submit" style="border:none;border-radius:999px;background:#22c55e;color:#0f172a;padding:6px 12px;font-size:0.78rem;font-weight:600;cursor:pointer;">
            Send
          </button>
        </div>
      </form>
    `;

    document.body.appendChild(launcher);
    document.body.appendChild(panel);

    const form = panel.querySelector("#quizx-chat-form");
    const input = panel.querySelector("#quizx-chat-input");
    const messagesEl = panel.querySelector("#quizx-chat-messages");
    const statusEl = panel.querySelector("#quizx-chat-status");
    const closeBtn = panel.querySelector("#quizx-chat-close");

    function appendMessage(role, text) {
      const wrapper = document.createElement("div");
      wrapper.style.marginBottom = "6px";

      const bubble = document.createElement("div");
      bubble.textContent = text;
      bubble.style.padding = "6px 9px";
      bubble.style.borderRadius = "10px";
      bubble.style.maxWidth = "90%";
      bubble.style.fontSize = "0.8rem";
      bubble.style.lineHeight = "1.4";

      if (role === "user") {
        wrapper.style.display = "flex";
        wrapper.style.justifyContent = "flex-end";
        bubble.style.background = "#22c55e";
        bubble.style.color = "#022c22";
      } else {
        wrapper.style.display = "flex";
        wrapper.style.justifyContent = "flex-start";
        bubble.style.background = "rgba(15,23,42,0.85)";
        bubble.style.color = "#e5e7eb";
        bubble.style.border = "1px solid rgba(148,163,184,0.4)";
      }

      wrapper.appendChild(bubble);
      messagesEl.appendChild(wrapper);
      messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    launcher.addEventListener("click", function () {
      panel.style.display = panel.style.display === "none" ? "flex" : "none";
    });

    closeBtn.addEventListener("click", function () {
      panel.style.display = "none";
    });

    form.addEventListener("submit", async function (e) {
      e.preventDefault();
      const message = (input.value || "").trim();
      if (!message) return;

      appendMessage("user", message);
      input.value = "";

      if (statusEl) {
        statusEl.textContent = "Thinking...";
        statusEl.style.color = "#facc15";
      }

      try {
        const resp = await fetch("/api/chat", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ message }),
        });

        if (!resp.ok) {
          throw new Error("Server error: " + resp.status);
        }

        const data = await resp.json();
        const aiText =
          data && data.response && typeof data.response.reply === "string"
            ? data.response.reply
            : "I could not generate a response.";

        appendMessage("assistant", aiText);
        if (statusEl) {
          statusEl.textContent = "Online · Ready";
          statusEl.style.color = "#22c55e";
        }
      } catch (err) {
        console.error(err);
        appendMessage(
          "assistant",
          "Sorry, something went wrong while contacting QuizX AI. Please try again."
        );
        if (statusEl) {
          statusEl.textContent = "Error · Check connection";
          statusEl.style.color = "#f97316";
        }
      }
    });
  });
})();


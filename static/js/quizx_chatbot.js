(function () {
  document.addEventListener("DOMContentLoaded", function () {
    // Avoid double init
    if (window.__quizxChatbotInitialized) return;
    window.__quizxChatbotInitialized = true;

    // Inject CSS for animations and Gemini-style markdown
    const styleEl = document.createElement("style");
    styleEl.textContent = `
      #quizx-chat-panel {
        transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.3s ease;
        transform: translateY(20px) scale(0.95);
        opacity: 0;
        pointer-events: none;
      }
      #quizx-chat-panel.active {
        transform: translateY(0) scale(1);
        opacity: 1;
        pointer-events: auto;
      }
      .gemini-message {
        animation: gemini-msg-pop 0.4s cubic-bezier(0.16, 1, 0.3, 1) both;
      }
      @keyframes gemini-msg-pop {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
      }
      .thinking-pulse {
        animation: gemini-pulse 1.5s ease-in-out infinite;
      }
      @keyframes gemini-pulse {
        0%, 100% { opacity: 0.4; transform: scale(0.98); }
        50% { opacity: 1; transform: scale(1.02); }
      }
      .chat-md-content { line-height: 1.6; }
      .chat-md-content h3 { font-size: 1rem; margin: 12px 0 6px; color: #22c55e; }
      .chat-md-content ul { padding-left: 18px; margin: 8px 0; }
      .chat-md-content li { margin-bottom: 4px; }
      .chat-md-content hr { border: 0; border-top: 1px solid rgba(148,163,184,0.1); margin: 12px 0; }
      .chat-md-content table { width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 0.75rem; }
      .chat-md-content th, .chat-md-content td { border: 1px solid rgba(148,163,184,0.2); padding: 4px 8px; text-align: left; }
      .chat-md-content th { background: rgba(148,163,184,0.1); }
    `;
    document.head.appendChild(styleEl);

    // Floating button
    const launcher = document.createElement("button");
    launcher.id = "quizx-chat-launcher";
    launcher.type = "button";
    launcher.innerHTML = '<i class="fas fa-sparkles"></i>';
    Object.assign(launcher.style, {
      position: "fixed",
      right: "30px",
      bottom: "30px",
      width: "60px",
      height: "60px",
      borderRadius: "20px",
      border: "none",
      background: "linear-gradient(135deg, #22c55e, #16a34a)",
      color: "#022c22",
      boxShadow: "0 10px 30px rgba(34, 197, 94, 0.3)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      cursor: "pointer",
      zIndex: 9999,
      fontSize: "24px",
      transition: "transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275)",
    });
    launcher.onmouseenter = () => launcher.style.transform = "scale(1.1) rotate(5deg)";
    launcher.onmouseleave = () => launcher.style.transform = "scale(1) rotate(0deg)";

    // Chat panel
    const panel = document.createElement("div");
    panel.id = "quizx-chat-panel";
    Object.assign(panel.style, {
      position: "fixed",
      right: "30px",
      bottom: "105px",
      width: "380px",
      height: "600px",
      maxHeight: "calc(100vh - 140px)",
      background: "rgba(10, 15, 28, 0.95)",
      backdropFilter: "blur(20px)",
      WebkitBackdropFilter: "blur(20px)",
      color: "#e2e8f0",
      borderRadius: "24px",
      boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.5)",
      border: "1px solid rgba(148,163,184,0.1)",
      overflow: "hidden",
      display: "flex",
      flexDirection: "column",
      zIndex: 9999,
      fontFamily: "'Plus Jakarta Sans', system-ui, sans-serif",
    });

    panel.innerHTML = `
      <div style="padding:20px; border-bottom:1px solid rgba(148,163,184,0.1); display:flex; align-items:center; justify-content:space-between;">
        <div style="display:flex; align-items:center; gap:12px;">
          <div class="thinking-pulse" style="width:36px; height:36px; border-radius:12px; background:rgba(34,197,94,0.1); display:flex; align-items:center; justify-content:center;">
            <i class="fas fa-robot" style="font-size:18px; color:#22c55e;"></i>
          </div>
          <div>
            <div style="font-size:0.95rem; font-weight:700; color:#f8fafc;">QuizX AI</div>
            <div id="quizx-chat-status" style="font-size:0.75rem; color:#22c55e; display:flex; align-items:center; gap:4px;">
              <span style="width:6px; height:6px; background:#22c55e; border-radius:50%;"></span>
              Online
            </div>
          </div>
        </div>
        <button type="button" id="quizx-chat-close" style="border:none; background:none; color:#64748b; font-size:18px; cursor:pointer; padding:5px;">
          <i class="fas fa-times"></i>
        </button>
      </div>
      <div id="quizx-chat-messages" style="flex:1; padding:20px; overflow-y:auto; scroll-behavior:smooth;">
        <div style="color:#64748b; font-size:0.9rem; text-align:center; margin-top:100px;">
          <i class="fas fa-sparkles" style="display:block; font-size:2rem; margin-bottom:15px; opacity:0.3;"></i>
          How can I help you today?
        </div>
      </div>
      <form id="quizx-chat-form" style="padding:20px; background:transparent;">
        <div style="position:relative; background:rgba(30,41,59,0.5); border-radius:16px; border:1px solid rgba(148,163,184,0.2); transition:border-color 0.3s;">
          <input
            id="quizx-chat-input"
            type="text"
            autocomplete="off"
            placeholder="Ask anything..."
            style="width:100%; border:none; background:transparent; color:#f8fafc; padding:15px 50px 15px 20px; font-size:0.95rem; outline:none;"
          />
          <button type="submit" style="position:absolute; right:10px; top:50%; transform:translateY(-50%); border:none; background:#22c55e; color:#022c22; width:34px; height:34px; border-radius:10px; display:flex; align-items:center; justify-content:center; cursor:pointer; transition:transform 0.2s;">
            <i class="fas fa-paper-plane" style="font-size:14px;"></i>
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

    function renderMarkdown(text) {
      if (!text) return "";
      let html = text
        .replace(/^### (.*$)/gim, '<h3>$1</h3>')
        .replace(/^\d\. (.*$)/gim, '<li>$1</li>')
        .replace(/^\- (.*$)/gim, '<li>$1</li>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\n\n/g, '<br><br>')
        .replace(/\n/g, '<br>')
        .replace(/---/g, '<hr>');

      if (html.includes('<li>')) {
        html = html.replace(/(<li>.*<\/li>)/gms, '<ul>$1</ul>');
      }
      return html;
    }

    function appendMessage(role, text) {
      const wrapper = document.createElement("div");
      wrapper.className = "gemini-message";
      wrapper.style.marginBottom = "20px";
      wrapper.style.display = "flex";
      wrapper.style.flexDirection = "column";
      wrapper.style.alignItems = role === "user" ? "flex-end" : "flex-start";

      if (role === "assistant") {
        const avatarWrapper = document.createElement("div");
        avatarWrapper.style.display = "flex";
        avatarWrapper.style.alignItems = "center";
        avatarWrapper.style.gap = "8px";
        avatarWrapper.style.marginBottom = "6px";
        avatarWrapper.innerHTML = `
          <div style="width:24px; height:24px; border-radius:8px; background:rgba(34,197,94,0.1); display:flex; align-items:center; justify-content:center;">
             <i class="fas fa-robot" style="font-size:12px; color:#22c55e;"></i>
          </div>
          <span style="font-size:0.75rem; font-weight:700; color:#94a3b8; text-transform:uppercase; letter-spacing:0.5px;">QuizX AI</span>
        `;
        wrapper.appendChild(avatarWrapper);
      }

      const bubble = document.createElement("div");
      if (role === "assistant") {
        bubble.className = "chat-md-content";
        bubble.innerHTML = renderMarkdown(text);
      } else {
        bubble.textContent = text;
      }

      bubble.style.padding = role === "user" ? "12px 16px" : "0px";
      bubble.style.borderRadius = "16px";
      bubble.style.maxWidth = "85%";
      bubble.style.fontSize = "0.95rem";
      bubble.style.lineHeight = "1.6";

      if (role === "user") {
        bubble.style.background = "#22c55e";
        bubble.style.color = "#022c22";
        bubble.style.fontWeight = "500";
        bubble.style.boxShadow = "0 4px 15px rgba(34, 197, 94, 0.2)";
      } else {
        bubble.style.background = "transparent";
        bubble.style.color = "#e2e8f0";
      }

      wrapper.appendChild(bubble);
      messagesEl.appendChild(wrapper);
      messagesEl.scrollTop = messagesEl.scrollHeight;

      // Clean up "How can I help" message if messages added
      const welcome = messagesEl.querySelector("div[style*='margin-top:100px']");
      if (welcome) welcome.remove();
    }

    launcher.addEventListener("click", function () {
      panel.classList.toggle("active");
    });

    closeBtn.addEventListener("click", function () {
      panel.classList.remove("active");
    });

    form.addEventListener("submit", async function (e) {
      e.preventDefault();
      const message = (input.value || "").trim();
      if (!message) return;

      appendMessage("user", message);
      input.value = "";

      if (statusEl) {
        statusEl.innerHTML = '<span class="thinking-pulse" style="width:6px; height:6px; background:#facc15; border-radius:50%; display:inline-block; margin-right:4px;"></span>Thinking...';
        statusEl.style.color = "#facc15";
      }

      // Add thinking bubble
      const thinkingBubble = document.createElement("div");
      thinkingBubble.className = "gemini-message thinking-pulse";
      thinkingBubble.style.marginBottom = "20px";
      thinkingBubble.innerHTML = `
        <div style="display:flex; align-items:center; gap:8px; margin-bottom:6px;">
          <div style="width:24px; height:24px; border-radius:8px; background:rgba(34,197,94,0.1); display:flex; align-items:center; justify-content:center;">
             <i class="fas fa-robot" style="font-size:12px; color:#22c55e;"></i>
          </div>
          <span style="font-size:0.75rem; font-weight:700; color:#94a3b8;">QuizX AI</span>
        </div>
        <div style="width:100px; height:20px; background:rgba(148,163,184,0.1); border-radius:10px;"></div>
      `;
      messagesEl.appendChild(thinkingBubble);
      messagesEl.scrollTop = messagesEl.scrollHeight;

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
        const responseData = data.response || {};

        // Remove thinking bubble
        thinkingBubble.remove();

        if (responseData.type === "admin_quiz" && responseData.quiz_data) {
          const aiText = responseData.reply || "I've generated a quiz for you! Opening the preview now...";
          appendMessage("assistant", aiText);

          // Small delay before opening modal for better UX
          setTimeout(() => {
            openQuizPreview(responseData.quiz_data);
          }, 800);
        } else {
          const aiText = responseData.reply || "I could not generate a response.";
          appendMessage("assistant", aiText);
        }

        if (statusEl) {
          statusEl.innerHTML = '<span style="width:6px; height:6px; background:#22c55e; border-radius:50%; display:inline-block; margin-right:4px;"></span>Online';
          statusEl.style.color = "#22c55e";
        }
      } catch (err) {
        console.error(err);
        thinkingBubble.remove();
        appendMessage(
          "assistant",
          "Sorry, something went wrong while contacting QuizX AI. Please try again."
        );
        if (statusEl) {
          statusEl.innerHTML = '<span style="width:6px; height:6px; background:#ef4444; border-radius:50%; display:inline-block; margin-right:4px;"></span>Error';
          statusEl.style.color = "#ef4444";
        }
      }
    });

    // ============================================
    // QUIZ PREVIEW MODAL SYSTEM
    // ============================================
    function openQuizPreview(quiz) {
      const modal = document.createElement("div");
      modal.id = "quizx-admin-modal";
      Object.assign(modal.style, {
        position: "fixed",
        top: "0", left: "0", width: "100%", height: "100%",
        background: "rgba(2, 6, 23, 0.95)",
        zIndex: "10000",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "20px",
        backdropFilter: "blur(12px)",
        color: "#e5e7eb",
        fontFamily: "'Plus Jakarta Sans', sans-serif"
      });

      const container = document.createElement("div");
      Object.assign(container.style, {
        width: "100%",
        maxWidth: "800px",
        maxHeight: "90vh",
        background: "#0f172a",
        borderRadius: "24px",
        border: "1px solid rgba(148,163,184,0.2)",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
        boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.5)"
      });

      container.innerHTML = `
        <div style="padding:24px; border-bottom:1px solid rgba(148,163,184,0.1); display:flex; justify-content:space-between; align-items:center;">
          <div>
            <span style="background:rgba(34,197,94,0.1); color:#22c55e; padding:4px 12px; border-radius:999px; font-size:0.75rem; font-weight:700; margin-bottom:8px; display:inline-block;">AI GENERATED</span>
            <h2 style="margin:0; font-size:1.5rem; letter-spacing:-0.5px;">${quiz.title}</h2>
          </div>
          <button id="close-preview" style="background:none; border:none; color:#94a3b8; font-size:1.5rem; cursor:pointer;"><i class="fas fa-times"></i></button>
        </div>
        <div id="questions-list" style="flex:1; overflow-y:auto; padding:24px;">
          ${quiz.questions.map((q, i) => `
            <div class="draggable-q" draggable="true" data-index="${i}" style="margin-bottom:20px; background:rgba(255,255,255,0.03); border:1px solid rgba(148,163,184,0.1); border-radius:16px; padding:20px; cursor:grab;">
              <div style="display:flex; justify-content:space-between; margin-bottom:12px;">
                <span style="font-weight:700; color:#22c55e;">#${i + 1}</span>
                <i class="fas fa-grip-lines" style="color:#475569;"></i>
              </div>
              <div contenteditable="true" class="edit-q-text" style="font-size:1.1rem; margin-bottom:16px; outline:none;">${q.question}</div>
              <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:16px;">
                ${q.options.map((opt, oi) => `
                  <div style="display:flex; align-items:center; gap:8px; background:rgba(2,6,23,0.4); padding:10px; border-radius:10px; border:${String.fromCharCode(65 + oi) === q.correct_answer ? '1px solid #22c55e' : '1px solid rgba(148,163,184,0.1)'}">
                    <span style="font-weight:800; opacity:0.5;">${String.fromCharCode(65 + oi)}</span>
                    <div contenteditable="true" class="edit-opt-text" style="flex:1; outline:none;">${opt}</div>
                  </div>
                `).join('')}
              </div>
              <div style="background:rgba(34,197,94,0.05); border-left:3px solid #22c55e; padding:12px; border-radius:0 8px 8px 0; font-size:0.85rem; color:#94a3b8;">
                <strong style="color:#22c55e; display:block; margin-bottom:4px; font-size:0.75rem; text-transform:uppercase; letter-spacing:0.5px;">Explanation</strong>
                <div contenteditable="true" class="edit-explanation" style="outline:none; font-style:italic;">${q.explanation || 'No explanation provided.'}</div>
              </div>
            </div>
          `).join('')}
        </div>
        <div style="padding:24px; border-top:1px solid rgba(148,163,184,0.1); display:flex; justify-content:flex-end; gap:12px; background:rgba(2,6,23,0.2);">
          <button id="save-draft" style="background:rgba(255,255,255,0.05); color:white; border:1px solid rgba(148,163,184,0.2); padding:12px 24px; border-radius:12px; font-weight:600; cursor:pointer;">Save as Draft</button>
          <button id="publish-quiz" style="background:#22c55e; color:#022c22; border:none; padding:12px 32px; border-radius:12px; font-weight:700; cursor:pointer;">Publish Now</button>
        </div>
      `;

      modal.appendChild(container);
      document.body.appendChild(modal);

      // Close Logic
      modal.querySelector("#close-preview").onclick = () => document.body.removeChild(modal);

      // Drag and Drop
      let draggedItem = null;
      const list = modal.querySelector("#questions-list");
      list.addEventListener('dragstart', e => {
        draggedItem = e.target.closest('.draggable-q');
        e.dataTransfer.effectAllowed = 'move';
        draggedItem.style.opacity = '0.5';
      });

      list.addEventListener('dragend', e => {
        draggedItem.style.opacity = '1';
        draggedItem = null;
      });

      list.addEventListener('dragover', e => {
        e.preventDefault();
        const target = e.target.closest('.draggable-q');
        if (target && target !== draggedItem) {
          const rect = target.getBoundingClientRect();
          const next = (e.clientY - rect.top) / (rect.bottom - rect.top) > 0.5;
          list.insertBefore(draggedItem, next ? target.nextSibling : target);
        }
      });

      // Action Handlers
      modal.querySelector("#save-draft").onclick = async () => {
        const updatedQuiz = getUpdatedQuizData(quiz, modal);
        const resp = await fetch("/admin/api/save-quiz", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(updatedQuiz)
        });
        const d = await resp.json();
        if (d.success) {
          alert("Quiz saved as draft!");
          document.body.removeChild(modal);
        }
      };

      modal.querySelector("#publish-quiz").onclick = async () => {
        const updatedQuiz = getUpdatedQuizData(quiz, modal);
        // First save, then publish
        const save = await fetch("/admin/api/save-quiz", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(updatedQuiz)
        });
        const saveRes = await save.json();
        if (saveRes.success) {
          const pub = await fetch("/admin/api/publish-quiz", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ quiz_id: saveRes.quiz_id })
          });
          const pubRes = await pub.json();
          if (pubRes.success) {
            alert("Quiz published successfully!");
            window.location.href = "/admin/quizzes";
          }
        }
      };
    }

    function getUpdatedQuizData(original, modal) {
      const questions = [];
      modal.querySelectorAll(".draggable-q").forEach((el, i) => {
        const opts = [];
        el.querySelectorAll(".edit-opt-text").forEach(opt => opts.push(opt.textContent.trim()));
        questions.push({
          order: i + 1,
          question: el.querySelector(".edit-q-text").textContent.trim(),
          options: opts,
          correct_answer: original.questions[el.dataset.index].correct_answer,
          explanation: el.querySelector(".edit-explanation").textContent.trim()
        });
      });
      return { ...original, questions };
    }
  });
})();


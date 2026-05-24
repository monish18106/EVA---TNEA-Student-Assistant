const input = document.getElementById("input");
const chat = document.getElementById("chat");
const sendBtn = document.getElementById("send-btn");
const clearBtn = document.getElementById("clear-btn");
const suggestionsContainer = document.getElementById("suggestions");

let busy = false;

// ────────────────────────────────────────────────────────────
// Toast Notifications
// ────────────────────────────────────────────────────────────
function showToast(message, duration = 2000) {
  const toast = document.getElementById("toast-notification");
  toast.textContent = message;
  toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), duration);
}

// ────────────────────────────────────────────────────────────
// Character Counter
// ────────────────────────────────────────────────────────────
input.addEventListener("input", () => {
  const count = input.value.length;
  const charCount = document.getElementById("char-count");
  charCount.textContent = `${count}/500`;
  
  // Change color if near limit
  if (count > 450) {
    charCount.style.color = "#ff6b6b";
  } else if (count > 400) {
    charCount.style.color = "#ffd700";
  } else {
    charCount.style.color = "#8a7f6f";
  }
});

// ────────────────────────────────────────────────────────────
// Clear Chat History
// ────────────────────────────────────────────────────────────
clearBtn.addEventListener("click", async () => {
  if (chat.children.length === 0) {
    // Still clear backend memory to keep client/server state aligned.
    try {
      await fetch("/clear", { method: "POST" });
    } catch (_) {
      // Ignore network errors for clear action feedback.
    }
    showToast("Chat is already empty!");
    return;
  }
  
  if (confirm("Are you sure you want to clear the chat history?")) {
    chat.innerHTML = "";
    try {
      await fetch("/clear", { method: "POST" });
    } catch (_) {
      showToast("Chat cleared locally. Server clear failed.");
      return;
    }
    showToast("Chat cleared!");
    suggestionsContainer.style.display = "block";
  }
});

// ────────────────────────────────────────────────────────────
// Send Suggestion
// ────────────────────────────────────────────────────────────
function sendSuggestion(text) {
  input.value = text;
  sendMessage();
}

// ────────────────────────────────────────────────────────────
// Get Current Time
// ────────────────────────────────────────────────────────────
function getCurrentTime() {
  const now = new Date();
  return now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

// ────────────────────────────────────────────────────────────
// Copy Message to Clipboard
// ────────────────────────────────────────────────────────────
function copyToClipboard(text) {
  navigator.clipboard.writeText(text).then(() => {
    showToast("Copied to clipboard!");
  }).catch(() => {
    showToast("Failed to copy!");
  });
}

// ────────────────────────────────────────────────────────────
// Add Message Line with Enhanced UI
// ────────────────────────────────────────────────────────────
function addLine(text, cls, isTyping = false) {
  const msg = document.createElement("div");
  msg.className = "msg " + cls;
  
  if (isTyping) {
    msg.innerHTML = `
      <span class="typing">
        <span class="typing-dot"></span>
        <span class="typing-dot"></span>
        <span class="typing-dot"></span>
      </span>
    `;
    msg.id = "thinking";
  } else {
    msg.textContent = text;
    
    // Add copy button for EVA messages
    if (cls === "eva" && text.trim()) {
      const wrapper = document.createElement("div");
      wrapper.style.display = "flex";
      wrapper.style.alignItems = "flex-end";
      wrapper.style.gap = "8px";
      
      const copyBtn = document.createElement("button");
      copyBtn.className = "msg-copy-btn";
      copyBtn.innerHTML = '<i class="fas fa-copy"></i>';
      copyBtn.addEventListener("click", () => copyToClipboard(text));
      
      const timeSpan = document.createElement("span");
      timeSpan.className = "msg-time";
      timeSpan.textContent = getCurrentTime();
      
      wrapper.appendChild(msg);
      wrapper.appendChild(copyBtn);
      wrapper.appendChild(timeSpan);
      
      chat.appendChild(wrapper);
      chat.scrollTop = chat.scrollHeight;
      return;
    }
  }
  
  chat.appendChild(msg);
  chat.scrollTop = chat.scrollHeight;
}

// ────────────────────────────────────────────────────────────
// Remove Thinking Animation
// ────────────────────────────────────────────────────────────
function removeThinking() {
  const t = document.getElementById("thinking");
  if (t) t.remove();
}

// ────────────────────────────────────────────────────────────
// Hide Suggestions When Chat Starts
// ────────────────────────────────────────────────────────────
function hideSuggestions() {
  suggestionsContainer.style.display = "none";
}

// ────────────────────────────────────────────────────────────
// Send Message
// ────────────────────────────────────────────────────────────
async function sendMessage() {
  const q = input.value.trim();
  
  if (!q) return;
  if (busy) return;
  
  busy = true;
  sendBtn.disabled = true;
  input.disabled = true;
  
  // Hide suggestions on first message
  hideSuggestions();
  
  // Add user message
  addLine("You: " + q, "user");
  input.value = "";
  document.getElementById("char-count").textContent = "0/500";
  
  // Show typing indicator
  addLine("", "eva", true);

  try {
    const res = await fetch("/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: q })
    });

    if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);

    const data = await res.json();
    removeThinking();

    if (!data.lines || data.lines.length === 0) {
      addLine("I couldn't find an answer for that. Please try rephrasing your question.", "eva");
    } else {
      data.lines.forEach(line => {
        if (line.trim()) {
          // Check if line contains HTML (starts with <)
          if (line.trim().startsWith('<')) {
            const msg = document.createElement("div");
            msg.className = "msg eva";
            msg.innerHTML = line;
            
            // Add copy button for HTML messages
            const wrapper = document.createElement("div");
            wrapper.style.display = "flex";
            wrapper.style.alignItems = "flex-end";
            wrapper.style.gap = "8px";
            
            const copyBtn = document.createElement("button");
            copyBtn.className = "msg-copy-btn";
            copyBtn.innerHTML = '<i class="fas fa-copy"></i>';
            copyBtn.addEventListener("click", () => copyToClipboard(msg.innerText));
            
            const timeSpan = document.createElement("span");
            timeSpan.className = "msg-time";
            timeSpan.textContent = getCurrentTime();
            
            wrapper.appendChild(msg);
            wrapper.appendChild(copyBtn);
            wrapper.appendChild(timeSpan);
            
            chat.appendChild(wrapper);
            chat.scrollTop = chat.scrollHeight;
          } else {
            // Plain text message
            addLine(line, "eva");
          }
        }
      });
    }
  } catch (err) {
    removeThinking();
    console.error("Error:", err);
    addLine("Something went wrong. Please try again.", "eva");
  } finally {
    busy = false;
    sendBtn.disabled = false;
    input.disabled = false;
    input.focus();
  }
}

// ────────────────────────────────────────────────────────────
// Keyboard Events
// ────────────────────────────────────────────────────────────
input.addEventListener("keydown", async (e) => {
  // Enter to send
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
  
  // Ctrl/Cmd + Enter to send (alternative)
  if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
    e.preventDefault();
    sendMessage();
  }
});

sendBtn.addEventListener("click", sendMessage);

// ────────────────────────────────────────────────────────────
// Gold Particle Effect
// ────────────────────────────────────────────────────────────
(function initParticles() {
  const canvas = document.getElementById("particle-canvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  let particles = [];
  const PARTICLE_COUNT = 100;

  function resize() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
  }
  resize();
  window.addEventListener("resize", resize);

  class Particle {
    constructor() { this.reset(); }
    reset() {
      this.x = Math.random() * canvas.width;
      this.size = Math.random() * 4 + 1.5;
      this.y = -this.size;
      this.speedY = Math.random() * 1.5 + 0.5;
      this.speedX = (Math.random() - 0.5) * 0.8;
      this.opacity = Math.random() * 0.6 + 0.4;
      this.blinkSpeed = Math.random() * 0.08 + 0.03;
      this.blinkPhase = Math.random() * Math.PI * 2;
      this.rotation = Math.random() * Math.PI * 2;
      this.rotSpeed = (Math.random() - 0.5) * 0.04;
      const golds = [
        "255,215,0",    // gold
        "201,168,76",   // muted gold
        "255,224,102",  // light gold
        "184,134,11",   // dark gold
        "218,165,32",   // goldenrod
        "255,255,255",  // white sparkle
      ];
      this.color = golds[Math.floor(Math.random() * golds.length)];
    }
    update() {
      this.y += this.speedY;
      this.x += this.speedX;
      this.blinkPhase += this.blinkSpeed;
      this.rotation += this.rotSpeed;
      if (this.y > canvas.height + this.size) this.reset();
    }
    draw() {
      const blink = 0.4 + 0.6 * Math.abs(Math.sin(this.blinkPhase));
      const alpha = this.opacity * blink;
      ctx.save();
      ctx.translate(this.x, this.y);
      ctx.rotate(this.rotation);
      // Diamond shape
      const s = this.size;
      ctx.beginPath();
      ctx.moveTo(0, -s);
      ctx.lineTo(s * 0.6, 0);
      ctx.moveTo(0, -s);
      ctx.lineTo(-s * 0.6, 0);
      ctx.lineTo(0, s);
      ctx.lineTo(s * 0.6, 0);
      ctx.closePath();
      ctx.fillStyle = `rgba(${this.color},${alpha})`;
      ctx.shadowColor = `rgba(255,215,0,${alpha * 0.7})`;
      ctx.shadowBlur = 10 + blink * 8;
      ctx.fill();
      // Center sparkle flash
      if (blink > 0.85) {
        ctx.beginPath();
        ctx.arc(0, 0, s * 0.3, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255,255,255,${alpha * 0.9})`;
        ctx.shadowColor = `rgba(255,255,255,${alpha})`;
        ctx.shadowBlur = 12;
        ctx.fill();
      }
      ctx.restore();
      ctx.shadowBlur = 0;
    }
  }

  for (let i = 0; i < PARTICLE_COUNT; i++) {
    const p = new Particle();
    p.y = Math.random() * canvas.height;
    particles.push(p);
  }

  function animate() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    particles.forEach(p => { p.update(); p.draw(); });
    requestAnimationFrame(animate);
  }
  animate();
})();

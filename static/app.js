const input = document.getElementById("input");
const chat = document.getElementById("chat");

let busy = false;

input.addEventListener("keydown", async (e) => {
  if (e.key !== "Enter") return;
  if (!input.value.trim()) return;
  if (busy) return;

  busy = true;
  const q = input.value;
  input.value = "";

  addLine("You: " + q, "user");
  addLine("EVA is thinking...", "eva", true);

  try {
    const res = await fetch("/ask", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ query: q })
    });

    const data = await res.json();
    removeThinking();

    if (!data.lines || data.lines.length === 0) {
      addLine("EVA: ", "eva");
    } else {
      data.lines.forEach(line => {
        addLine("EVA: " + line, "eva");
      });
    }
  } catch (err) {
    removeThinking();
    addLine("EVA: Something went wrong.", "eva");
  } finally {
    busy = false;   // 🔑 ALWAYS reset
  }
});

function addLine(text, cls, thinking=false) {
  const div = document.createElement("div");
  div.className = "msg " + cls;
  div.textContent = text;
  if (thinking) div.id = "thinking";
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
}

function removeThinking() {
  const t = document.getElementById("thinking");
  if (t) t.remove();
}

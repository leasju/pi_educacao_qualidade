const GEMINI_KEY = "SUA_CHAVE_AQUI";

const GEMINI_URL = `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${GEMINI_KEY}`;

const SYSTEM_CTX = `Você é um assistente especializado no painel EduStats,
  que analisa desigualdades educacionais nos municípios da Região Metropolitana
  de Campinas (RMC). Os dados incluem proficiência SARESP, absenteísmo docente,
  taxa de aprovação/reprovação, fluxo escolar e infraestrutura escolar.
  Responda de forma clara e objetiva em português brasileiro.`;

const chatHistory = [];

// ─── TOGGLE DA JANELA ────────────────────────────────────────
function toggleChat() {
  const box = document.getElementById("chat-box");
  box.classList.toggle("open");
  if (box.classList.contains("open")) {
    document.getElementById("chat-input").focus();
  }
}

// ─── ADICIONA MENSAGEM NA TELA ───────────────────────────────
function addMsg(text, role) {
  const el = document.createElement("div");
  el.className = "msg " + role;
  el.textContent = text;
  const msgs = document.getElementById("chat-messages");
  msgs.appendChild(el);
  msgs.scrollTop = msgs.scrollHeight;
  return el;
}

// ─── ENVIO DE MENSAGEM ───────────────────────────────────────
async function sendMessage() {
  const input = document.getElementById("chat-input");
  const text = input.value.trim();
  if (!text) return;

  input.value = "";
  input.disabled = true;

  addMsg(text, "user");
  chatHistory.push({ role: "user", parts: [{ text }] });

  const loading = addMsg("Digitando...", "bot loading");

  try {
    const response = await fetch(GEMINI_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        system_instruction: { parts: [{ text: SYSTEM_CTX }] },
        contents: chatHistory
      })
    });

    const data = await response.json();
    const reply = data.candidates?.[0]?.content?.parts?.[0]?.text
      || "Não consegui gerar uma resposta. Tente novamente.";

    chatHistory.push({ role: "model", parts: [{ text: reply }] });
    loading.className = "msg bot";
    loading.textContent = reply;

  } catch (err) {
    loading.className = "msg bot";
    loading.textContent = "Erro ao conectar com o Gemini. Verifique sua chave de API e tente novamente.";
    console.error("Gemini API error:", err);
  }

  input.disabled = false;
  input.focus();
  document.getElementById("chat-messages").scrollTop = 9999;
}
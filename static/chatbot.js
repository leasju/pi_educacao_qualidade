const SYSTEM_CTX = `Você é um assistente especializado no painel EduStats, que analisa 
desigualdades educacionais nos municípios da Região Metropolitana de Campinas (RMC). 
Os dados incluem proficiência SARESP, absenteísmo docente, taxa de aprovação/reprovação, 
fluxo escolar e infraestrutura escolar. Responda de forma clara e objetiva em português brasileiro.`;

const chatHistory = [];

function toggleChat() {
    const box = document.getElementById("chat-box");
    box.classList.toggle("open");
    if (box.classList.contains("open")) {
        document.getElementById("chat-input").focus();
    }
}

function addMsg(text, role) {
    const el = document.createElement("div");
    el.className = "msg " + role;
    el.textContent = text;
    const msgs = document.getElementById("chat-messages");
    msgs.appendChild(el);
    msgs.scrollTop = msgs.scrollHeight;
    return el;
}

async function sendMessage() {
    const input = document.getElementById("chat-input");
    const text = input.value.trim();
    if (!text) return;

    input.value = "";
    input.disabled = true;
    addMsg(text, "user");
    chatHistory.push({ role: "user", content: text });

    const loading = addMsg("Digitando...", "bot loading");

    try {
        const response = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                messages: [
                    { role: "system", content: SYSTEM_CTX },
                    ...chatHistory
                ]
            })
        });

        const data = await response.json();
        console.log("[DEBUG] Resposta completa:", JSON.stringify(data, null, 2));
        const reply = data.choices?.[0]?.message?.content || "Não consegui gerar uma resposta. Tente novamente.";

        chatHistory.push({ role: "assistant", content: reply });
        loading.className = "msg bot";
        loading.textContent = reply;

    } catch (err) {
        loading.className = "msg bot";
        loading.textContent = "Erro ao conectar. Verifique sua chave e tente novamente.";
        console.error("OpenRouter error:", err);
    }

    input.disabled = false;
    input.focus();
    document.getElementById("chat-messages").scrollTop = 9999;
}
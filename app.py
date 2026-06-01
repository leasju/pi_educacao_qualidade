import os
import requests
import plotly.express as px
from flask import Flask, render_template, request, jsonify
from pymongo import MongoClient

from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__, template_folder="Template")

# ─── CONTEXTO DO BANCO ──────────────────────────────────────
def get_db_context():
    try:
        client = MongoClient(os.environ.get("MONGO_URI"))
        db = client["datasets"]

        context = "=== DADOS EDUCACIONAIS RMC ===\n\n"

        # SARESP
        saresp = db["saresp"]
        municipios = saresp.distinct("MUNICÍPIOS")
        anos = sorted(saresp.distinct("ANO"))
        sample = list(saresp.find({}, {"_id": 0}).limit(3))
        context += f"SARESP (proficiência por município):\n- Municípios: {', '.join(str(m) for m in municipios[:15])}\n- Anos disponíveis: {anos}\n- Exemplo de registros: {sample}\n\n"

        # Fluxo
        fluxo = db["fluxo"]
        sample = list(fluxo.find({}, {"_id": 0}).limit(3))
        context += f"FLUXO ESCOLAR (aprovação/reprovação/abandono):\n- Exemplo de registros: {sample}\n\n"

        # Ausência
        ausencia = db["ausencia"]
        sample = list(ausencia.find({}, {"_id": 0}).limit(3))
        context += f"AUSÊNCIAS DOCENTES (absenteísmo):\n- Exemplo de registros: {sample}\n\n"

        # Censo
        censo = db["censo"]
        sample = list(censo.find({}, {"_id": 0}).limit(3))
        context += f"CENSO ESCOLAR (infraestrutura):\n- Exemplo de registros: {sample}\n\n"

        client.close()
        return context

    except Exception as e:
        print(f"[DB ERROR] {e}")
        return "Dados do banco indisponíveis no momento."


# ─── ROTA PRINCIPAL ─────────────────────────────────────────
@app.route("/")
def home():
    data_canada = px.data.gapminder().query("country == 'Canada'")
    fig = px.bar(data_canada, x='year', y='pop', title='População do Canadá')
    graph_html = fig.to_html(full_html=False)
    return render_template("index.html", graph_html=graph_html)


# ─── ROTA DO CHATBOT ─────────────────────────────────────────
MODELS = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemma-4-31b-it:free",
    "deepseek/deepseek-v4-flash:free",
    "openai/gpt-oss-120b:free",
    "z-ai/glm-4.5-air:free",
]

@app.route("/api/chat", methods=["POST"])
def chat():
    openrouter_key = os.environ.get("OPENROUTER_KEY")
    if not openrouter_key:
        return jsonify({"error": "Chave não configurada"}), 500

    body = request.json
    db_context = get_db_context()

    system_prompt = f"""Você é um assistente especializado no painel EduStats, que analisa \
desigualdades educacionais nos municípios da Região Metropolitana de Campinas (RMC).
Responda de forma clara e objetiva em português brasileiro.
Quando o usuário perguntar sobre dados específicos, use as informações abaixo para embasar sua resposta.

{db_context}

Use esses dados para responder perguntas sobre municípios, anos e indicadores educacionais."""

    # Remove o system prompt do frontend e usa o do servidor (que tem os dados)
    messages = [m for m in body.get("messages", []) if m.get("role") != "system"]
    messages.insert(0, {"role": "system", "content": system_prompt})

    for model in MODELS:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {openrouter_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:8080",
                "X-Title": "EduStats RMC"
            },
            json={
                "model": model,
                "messages": messages,
                "max_tokens": 1000
            }
        )

        print(f"[DEBUG] Modelo: {model} | Status: {response.status_code}")

        if response.status_code not in (429, 404):
            return jsonify(response.json()), response.status_code

        print(f"[FALLBACK] {model} | Status: {response.status_code} | Erro: {response.text}")

    return jsonify({"choices": [{"message": {"content": "Todos os modelos estão sobrecarregados. Tente novamente em instantes!"}}]}), 200


if __name__ == "__main__":
    app.run(debug=True, port=8080)
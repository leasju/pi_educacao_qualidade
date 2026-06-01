import os
import requests
import plotly.express as px
from flask import Flask, render_template, request, jsonify

from dotenv import load_dotenv
load_dotenv()  

app = Flask(__name__, template_folder="Template")

# ─── ROTA PRINCIPAL ─────────────────────────────────────────
@app.route("/")
def home():
    data_canada = px.data.gapminder().query("country == 'Canada'")

    fig = px.bar(
        data_canada,
        x='year',
        y='pop',
        title='População do Canadá'
    )
    graph_html = fig.to_html(full_html=False)

    return render_template("index.html", graph_html=graph_html)


# ─── ROTA DO CHATBOT ─────────────────────────────────────────
# O JS do frontend chama /api/chat em vez da API do Gemini diretamente
# A chave fica aqui no servidor, invisível pro navegador
@app.route("/api/chat", methods=["POST"])
def chat():
    openrouter_key = os.environ.get("OPENROUTER_KEY")
    if not openrouter_key:
        return jsonify({"error": "Chave não configurada"}), 500

    body = request.json

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {openrouter_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8080",  # opcional mas recomendado
            "X-Title": "EduStats RMC"                 # aparece no dashboard do OpenRouter
        },
        json={
            "model": "meta-llama/llama-3.3-70b-instruct:free",  # modelo gratuito
            "messages": body.get("messages", []),
            "max_tokens": 1000
        }
    )

    if response.status_code == 429:
        return jsonify({"choices": [{"message": {"content": "Muitas requisições. Aguarde um momento!"}}]}), 200

    return jsonify(response.json()), response.status_code

if __name__ == "__main__":
    app.run(debug=True, port=8080)
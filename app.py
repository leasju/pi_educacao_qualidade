# python app.py

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
                "messages": body.get("messages", []),
                "max_tokens": 1000
            }
        )

        print(f"[DEBUG] Modelo: {model} | Status: {response.status_code}")

        if response.status_code not in (429, 404):
           return jsonify(response.json()), response.status_code

        print(f"[FALLBACK] {model} | Status: {response.status_code} | Erro: {response.text}")
        continue

        return jsonify(response.json()), response.status_code

    return jsonify({"choices": [{"message": {"content": "Todos os modelos estão sobrecarregados. Tente novamente em instantes!"}}]}), 200

if __name__ == "__main__":
    app.run(debug=True, port=8080)
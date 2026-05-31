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
    gemini_key = os.environ.get("GEMINI_KEY")
    print("[DEBUG] KEY carregada?", bool(os.environ.get("GEMINI_KEY"))) # Debug

    if not gemini_key:
        return jsonify({"error": "Chave da API não configurada."}), 500

    gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}"

    # Repassa o body enviado pelo JS diretamente para a API do Gemini
    response = requests.post(
        gemini_url,
        json=request.json,
        headers={"Content-Type": "application/json"}
    )

    if response.status_code == 429:
        return jsonify({"candidates": [{"content": {"parts": [{"text": "Muitas requisições em pouco tempo. Aguarde um momento e tente novamente!"}]}}]}), 200
    
    return jsonify(response.json()), response.status_code

if __name__ == "__main__":
    app.run(debug=True, port=8080)
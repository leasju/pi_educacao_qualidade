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


# ─── ROTA DE DADOS PARA GRÁFICOS ────────────────────────────
@app.route("/api/chart-data", methods=["GET"])
def chart_data():
    """Retorna dados estruturados para os gráficos Plotly"""
    
    # Dados mock para testes (substitua com Mongo quando disponível)
    data = {
        "MÉDIA_PROFICIÊNCIA": {
            "labels": ["Campinas", "Hortolândia", "Sumaré", "Indaiatuba", "Paulínia", "Americana"],
            "datasets": [{
                "label": "Proficiência Média SARESP",
                "data": [72.5, 68.3, 65.8, 70.2, 67.4, 69.1]
            }]
        },
        "PROFICIÊNCIA_VS_AUSÊNCIA": {
            "data": [
                {"x": 5.2, "y": 72.5, "label": "Campinas"},
                {"x": 8.1, "y": 68.3, "label": "Hortolândia"},
                {"x": 6.7, "y": 65.8, "label": "Sumaré"},
                {"x": 4.5, "y": 70.2, "label": "Indaiatuba"},
                {"x": 7.3, "y": 67.4, "label": "Paulínia"},
                {"x": 6.2, "y": 69.1, "label": "Americana"}
            ]
        },
        "APROVAÇÃO_E_REPROVAÇÃO": {
            "labels": ["Campinas", "Hortolândia", "Sumaré", "Indaiatuba"],
            "datasets": [
                {"label": "Aprovação", "data": [78.5, 75.2, 72.1, 76.8]},
                {"label": "Reprovação", "data": [15.3, 18.2, 21.4, 16.5]},
                {"label": "Abandono", "data": [6.2, 6.6, 6.5, 6.7]}
            ]
        },
        "FLUXO_VS_INFRAESTRUTURA": {
            "data": [
                {"x": 78, "y": 8.2, "label": "Campinas"},
                {"x": 75, "y": 6.9, "label": "Hortolândia"},
                {"x": 72, "y": 5.3, "label": "Sumaré"},
                {"x": 77, "y": 7.8, "label": "Indaiatuba"},
                {"x": 74, "y": 6.5, "label": "Paulínia"},
                {"x": 76, "y": 7.2, "label": "Americana"}
            ]
        },
        "TOTAL_DIAS_AUSENTES": {
            "labels": ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"],
            "datasets": [
                {"label": "Campinas", "data": [245, 238, 251, 268, 290, 312, 328, 315, 298, 276, 255, 242]},
                {"label": "Hortolândia", "data": [156, 148, 162, 178, 195, 210, 224, 215, 202, 185, 168, 152]},
                {"label": "Sumaré", "data": [128, 122, 135, 148, 162, 175, 188, 178, 165, 152, 138, 125]}
            ]
        },
        "INFRA_TREND": {
            "labels": ["2022", "2023", "2024"],
            "datasets": [
                {"label": "Infraestrutura (Score)", "data": [6.2, 6.8, 7.3]},
                {"label": "Proficiência SARESP", "data": [68.1, 69.5, 71.2]}
            ]
        },
        "main_chart": {
            "labels": ["Campinas", "Hortolândia", "Sumaré", "Indaiatuba", "Paulínia", "Americana"],
            "datasets": [
                {"label": "2022", "data": [65.2, 62.1, 59.8, 64.5, 61.3, 63.2]},
                {"label": "2023", "data": [68.7, 65.4, 63.2, 67.1, 64.8, 66.5]},
                {"label": "2024", "data": [72.1, 68.9, 66.5, 70.8, 68.2, 70.3]}
            ]
        }
    }
    
    return jsonify(data), 200


if __name__ == "__main__":
    app.run(debug=True, port=8080)
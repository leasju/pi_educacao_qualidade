import os
import requests
from flask import Flask, jsonify, render_template, request
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, template_folder="Template")


def get_mongo_client():
    mongo_uri = os.environ.get("MONGODB_URI") or os.environ.get("MONGO_URI")
    if not mongo_uri:
        raise RuntimeError("Variavel MONGODB_URI nao configurada")
    return MongoClient(mongo_uri)


# CONTEXTO DO BANCO
def get_db_context():
    try:
        client = get_mongo_client()
        db = client["datasets"]

        context = "=== DADOS EDUCACIONAIS RMC ===\n\n"

        saresp = db["saresp"]
        municipios = saresp.distinct("MUNICÍPIOS")
        anos = sorted(saresp.distinct("ANO"))
        sample = list(saresp.find({}, {"_id": 0}).limit(3))
        context += (
            "SARESP (proficiência por município):\n"
            f"- Municípios: {', '.join(str(m) for m in municipios[:15])}\n"
            f"- Anos disponíveis: {anos}\n"
            f"- Exemplo de registros: {sample}\n\n"
        )

        fluxo = db["fluxo"]
        sample = list(fluxo.find({}, {"_id": 0}).limit(3))
        context += f"FLUXO ESCOLAR (aprovação/reprovação/abandono):\n- Exemplo de registros: {sample}\n\n"

        ausencia = db["ausencia"]
        sample = list(ausencia.find({}, {"_id": 0}).limit(3))
        context += f"AUSÊNCIAS DOCENTES (absenteísmo):\n- Exemplo de registros: {sample}\n\n"

        censo = db["censo"]
        sample = list(censo.find({}, {"_id": 0}).limit(3))
        context += f"CENSO ESCOLAR (infraestrutura):\n- Exemplo de registros: {sample}\n\n"

        client.close()
        return context
    except Exception as exc:
        print(f"[DB ERROR] {exc}")
        return "Dados do banco indisponíveis no momento."


# ROTA PRINCIPAL
@app.route("/")
def home():
    return render_template("index.html")


# ROTA DO CHATBOT
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

    body = request.json or {}
    db_context = get_db_context()

    system_prompt = f"""Você é um assistente especializado no painel EduStats, que analisa desigualdades educacionais nos municípios da Região Metropolitana de Campinas (RMC).
Responda de forma clara e objetiva em português brasileiro.
Quando o usuário perguntar sobre dados específicos, use as informações abaixo para embasar sua resposta.

{db_context}

Use esses dados para responder perguntas sobre municípios, anos e indicadores educacionais."""

    messages = [message for message in body.get("messages", []) if message.get("role") != "system"]
    messages.insert(0, {"role": "system", "content": system_prompt})

    for model in MODELS:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {openrouter_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:8080",
                "X-Title": "EduStats RMC",
            },
            json={"model": model, "messages": messages, "max_tokens": 1000},
            timeout=30,
        )

        print(f"[DEBUG] Modelo: {model} | Status: {response.status_code}")

        if response.status_code not in (429, 404):
            return jsonify(response.json()), response.status_code

        print(f"[FALLBACK] {model} | Status: {response.status_code} | Erro: {response.text}")

    return jsonify({
        "choices": [{"message": {"content": "Todos os modelos estão sobrecarregados. Tente novamente em instantes!"}}]
    }), 200


# ROTA DE DADOS PARA GRAFICOS
@app.route("/api/chart-data", methods=["GET"])
def chart_data():
    """Executa as agregacoes MongoDB e retorna os dados para Chart.js."""
    try:
        client = get_mongo_client()
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 500

    db = client["datasets"]

    try:
        def clean_number(value):
            if value is None:
                return None
            try:
                return float(value)
            except (TypeError, ValueError):
                return None

        def min_max(values):
            valid = [clean_number(value) for value in values]
            valid = [value for value in valid if value is not None]
            if not valid:
                return [0 for _ in values]
            min_value = min(valid)
            max_value = max(valid)
            if min_value == max_value:
                return [0 for _ in values]
            return [
                0 if clean_number(value) is None else (clean_number(value) - min_value) / (max_value - min_value)
                for value in values
            ]

        pipeline_censo_infra = [{
            "$group": {
                "_id": "$MUNICÍPIOS",
                "biblioteca": {"$avg": {"$convert": {"input": "$BIBLIOTECA", "to": "double", "onError": None, "onNull": None}}},
                "sala_leitura": {"$avg": {"$convert": {"input": "$BIBLIOTECA OU SALA DE LEITURA", "to": "double", "onError": None, "onNull": None}}},
                "lab_info": {"$avg": {"$convert": {"input": "$LAB. INFORMÁTICA", "to": "double", "onError": None, "onNull": None}}},
                "lab_ciencias": {"$avg": {"$convert": {"input": "$LAB. CIÊNCIAS", "to": "double", "onError": None, "onNull": None}}},
                "internet": {"$avg": {"$convert": {"input": "$INTERNET", "to": "double", "onError": None, "onNull": None}}},
                "internet_alunos": {"$avg": {"$convert": {"input": "$INTERNET - ALUNOS", "to": "double", "onError": None, "onNull": None}}},
                "banda_larga": {"$avg": {"$convert": {"input": "$INTERNET - BANDA LARGA", "to": "double", "onError": None, "onNull": None}}},
            }
        }]

        dados_censo_infra = list(db["censo"].aggregate(pipeline_censo_infra))
        infraestrutura = []
        for item in dados_censo_infra:
            indicadores = [
                item.get("biblioteca"), item.get("sala_leitura"), item.get("lab_info"), item.get("lab_ciencias"),
                item.get("internet"), item.get("internet_alunos"), item.get("banda_larga"),
            ]
            validos = [clean_number(value) for value in indicadores if clean_number(value) is not None]
            if validos:
                infraestrutura.append({"Município": item["_id"], "Infraestrutura": round(sum(validos) / len(validos), 3)})

        pipeline_saresp_media = [{
            "$group": {
                "_id": "$MUNICÍPIOS",
                "saresp": {"$avg": {"$convert": {"input": "$MÉDIA_PROFICIÊNCIA", "to": "double", "onError": None, "onNull": None}}},
            }
        }]
        dados_saresp_media = list(db["saresp"].aggregate(pipeline_saresp_media))
        saresp_dict = {item["_id"]: clean_number(item.get("saresp")) for item in dados_saresp_media}

        analise_um = [
            {"x": item["Infraestrutura"], "y": saresp_dict[item["Município"]], "label": item["Município"]}
            for item in infraestrutura
            if item["Município"] in saresp_dict and saresp_dict[item["Município"]] is not None
        ]

        pipeline_ausencia_media = [{
            "$group": {"_id": "$MUNICÍPIOS", "dias_ausentes": {"$avg": {"$toDouble": "$TOTAL DIAS AUSENTES"}}}
        }]
        dados_ausencia_media = list(db["ausencia"].aggregate(pipeline_ausencia_media))

        pipeline_fluxo_media = [{
            "$group": {
                "_id": "$MUNICÍPIOS",
                "aprovacao": {"$avg": {"$divide": [{"$add": [{"$toDouble": "$APROVAÇÃO ANOS INICIAIS 9 ANOS"}, {"$toDouble": "$APROVAÇÃO ANOS FINAIS 9 ANOS"}]}, 2]}},
                "reprovacao": {"$avg": {"$divide": [{"$add": [{"$toDouble": "$REPROVAÇÃO ANOS INICIAIS 9 ANOS"}, {"$toDouble": "$REPROVAÇÃO ANOS FINAIS 9 ANOS"}]}, 2]}},
            }
        }]
        dados_fluxo_media = list(db["fluxo"].aggregate(pipeline_fluxo_media))
        fluxo_media_dict = {
            item["_id"]: {"aprovacao": clean_number(item.get("aprovacao")), "reprovacao": clean_number(item.get("reprovacao"))}
            for item in dados_fluxo_media
        }

        analise_dois = []
        for item in dados_ausencia_media:
            municipio = item["_id"]
            if municipio in fluxo_media_dict:
                dias_ausentes = clean_number(item.get("dias_ausentes"))
                reprovacao = fluxo_media_dict[municipio]["reprovacao"]
                if dias_ausentes is not None and reprovacao is not None:
                    analise_dois.append({"x": dias_ausentes, "y": reprovacao, "label": municipio})

        pipeline_tecnologia_infra = [
            {"$project": {
                "MUNICÍPIOS": 1,
                "computadores": {"$convert": {"input": "$Quantidade de computadores em uso pelos alunos", "to": "double", "onError": None, "onNull": None}},
                "lousa": {"$convert": {"input": "$QTDE LOUSAS DIGITAIS", "to": "double", "onError": None, "onNull": None}},
                "datashow": {"$convert": {"input": "$QTDE DATASHOW", "to": "double", "onError": None, "onNull": None}},
                "internet_alunos": {"$convert": {"input": "$INTERNET - ALUNOS", "to": "double", "onError": None, "onNull": None}},
            }},
            {"$group": {
                "_id": "$MUNICÍPIOS",
                "computadores": {"$avg": "$computadores"},
                "lousa": {"$avg": "$lousa"},
                "datashow": {"$avg": "$datashow"},
                "internet_alunos": {"$avg": "$internet_alunos"},
            }},
        ]
        dados_tec_infra = list(db["censo"].aggregate(pipeline_tecnologia_infra))
        tec_cols = ["computadores", "lousa", "datashow", "internet_alunos"]
        normalized_tec = {col: min_max([item.get(col) for item in dados_tec_infra]) for col in tec_cols}
        tecnologia = []
        for index, item in enumerate(dados_tec_infra):
            indice = sum(normalized_tec[col][index] for col in tec_cols) / len(tec_cols)
            tecnologia.append({"Município": item["_id"], "Indice_Tecnologia": indice})

        analise_tres = [
            {"x": item["Indice_Tecnologia"], "y": saresp_dict[item["Município"]], "label": item["Município"]}
            for item in tecnologia
            if item["Município"] in saresp_dict and saresp_dict[item["Município"]] is not None
        ]

        pipeline_censo_docentes = [{
            "$group": {
                "_id": "$MUNICÍPIOS",
                "docentes": {"$avg": {"$toDouble": "$QTDE DOCENTES FUNDAMENTAL - TOTAL"}},
                "matriculas": {"$avg": {"$toDouble": "$QTDE MATRICULAS FUNDAMENTAL - TOTAL"}},
            }
        }]
        dados_censo_docentes = list(db["censo"].aggregate(pipeline_censo_docentes))
        professor = []
        for item in dados_censo_docentes:
            docentes = clean_number(item.get("docentes"))
            matriculas = clean_number(item.get("matriculas"))
            if docentes and docentes > 0 and matriculas is not None:
                professor.append({"Município": item["_id"], "Aluno_Professor": matriculas / docentes})

        prof_labels = []
        aluno_professor = []
        aprovacao_professor = []
        for item in professor:
            municipio = item["Município"]
            if municipio in fluxo_media_dict and fluxo_media_dict[municipio]["aprovacao"] is not None:
                prof_labels.append(municipio)
                aluno_professor.append(item["Aluno_Professor"])
                aprovacao_professor.append(fluxo_media_dict[municipio]["aprovacao"])

        pipeline_saresp_ano = [{"$group": {"_id": "$ANO", "saresp": {"$avg": {"$toDouble": "$MÉDIA_PROFICIÊNCIA"}}}}, {"$sort": {"_id": 1}}]
        pipeline_fluxo_ano = [{"$group": {"_id": "$ANO", "aprovacao": {"$avg": {"$divide": [{"$add": [{"$toDouble": "$APROVAÇÃO ANOS INICIAIS 9 ANOS"}, {"$toDouble": "$APROVAÇÃO ANOS FINAIS 9 ANOS"}]}, 2]}}}}, {"$sort": {"_id": 1}}]
        pipeline_ausencia_ano = [{"$group": {"_id": "$ANO", "ausencia": {"$avg": {"$toDouble": "$TOTAL DIAS AUSENTES"}}}}, {"$sort": {"_id": 1}}]
        pipeline_infra_ano = [
            {"$project": {
                "ANO": 1,
                "biblioteca": {"$convert": {"input": "$BIBLIOTECA", "to": "double", "onError": None, "onNull": None}},
                "sala_leitura": {"$convert": {"input": "$BIBLIOTECA OU SALA DE LEITURA", "to": "double", "onError": None, "onNull": None}},
                "lab_info": {"$convert": {"input": "$LAB. INFORMÁTICA", "to": "double", "onError": None, "onNull": None}},
                "lab_ciencias": {"$convert": {"input": "$LAB. CIÊNCIAS", "to": "double", "onError": None, "onNull": None}},
                "internet": {"$convert": {"input": "$INTERNET", "to": "double", "onError": None, "onNull": None}},
                "internet_alunos": {"$convert": {"input": "$INTERNET - ALUNOS", "to": "double", "onError": None, "onNull": None}},
                "banda_larga": {"$convert": {"input": "$INTERNET - BANDA LARGA", "to": "double", "onError": None, "onNull": None}},
            }},
            {"$group": {
                "_id": "$ANO",
                "biblioteca": {"$avg": "$biblioteca"},
                "sala_leitura": {"$avg": "$sala_leitura"},
                "lab_info": {"$avg": "$lab_info"},
                "lab_ciencias": {"$avg": "$lab_ciencias"},
                "internet": {"$avg": "$internet"},
                "internet_alunos": {"$avg": "$internet_alunos"},
                "banda_larga": {"$avg": "$banda_larga"},
            }},
            {"$sort": {"_id": 1}},
        ]

        saresp_ano = {item["_id"]: clean_number(item.get("saresp")) for item in db["saresp"].aggregate(pipeline_saresp_ano)}
        fluxo_ano = {item["_id"]: clean_number(item.get("aprovacao")) for item in db["fluxo"].aggregate(pipeline_fluxo_ano)}
        ausencia_ano = {item["_id"]: clean_number(item.get("ausencia")) for item in db["ausencia"].aggregate(pipeline_ausencia_ano)}
        infra_ano = {}
        for item in db["censo"].aggregate(pipeline_infra_ano):
            indicadores = [item.get("biblioteca"), item.get("sala_leitura"), item.get("lab_info"), item.get("lab_ciencias"), item.get("internet"), item.get("internet_alunos"), item.get("banda_larga")]
            validos = [clean_number(value) for value in indicadores if clean_number(value) is not None]
            if validos:
                infra_ano[item["_id"]] = sum(validos) / len(validos)

        anos = sorted(set(saresp_ano) & set(fluxo_ano) & set(ausencia_ano) & set(infra_ano))
        saresp_values = [saresp_ano[ano] for ano in anos]
        aprovacao_values = [fluxo_ano[ano] for ano in anos]
        ausencia_values = [ausencia_ano[ano] for ano in anos]
        infraestrutura_values = [infra_ano[ano] for ano in anos]

        ranking_rows = []
        for municipio, saresp in saresp_dict.items():
            infra_item = next((item for item in infraestrutura if item["Município"] == municipio), None)
            ausencia_item = next((item for item in dados_ausencia_media if item["_id"] == municipio), None)
            fluxo_item = fluxo_media_dict.get(municipio)
            ausencia = clean_number(ausencia_item.get("dias_ausentes")) if ausencia_item else None
            if infra_item and fluxo_item and None not in (saresp, fluxo_item["aprovacao"], ausencia):
                ranking_rows.append({
                    "MUNICIPIO": municipio,
                    "SARESP": saresp,
                    "APROVACAO": fluxo_item["aprovacao"],
                    "INFRAESTRUTURA": infra_item["Infraestrutura"],
                    "AUSENCIA": ausencia,
                })

        ranking_norm = {col: min_max([item[col] for item in ranking_rows]) for col in ["SARESP", "APROVACAO", "INFRAESTRUTURA", "AUSENCIA"]}
        ranking = []
        for index, item in enumerate(ranking_rows):
            indice = (
                0.40 * ranking_norm["SARESP"][index]
                + 0.30 * ranking_norm["APROVACAO"][index]
                + 0.20 * ranking_norm["INFRAESTRUTURA"][index]
                + 0.10 * (1 - ranking_norm["AUSENCIA"][index])
            )
            ranking.append({"MUNICIPIO": item["MUNICIPIO"], "Índice Educação": indice})
        ranking.sort(key=lambda item: item["Índice Educação"], reverse=True)

        return jsonify({
            "infraestrutura_saresp": {
                "type": "scatter",
                "title": "Infraestrutura Escolar x Média SARESP",
                "xLabel": "Índice de Infraestrutura",
                "yLabel": "Média SARESP",
                "data": analise_um,
            },
            "ausencia_reprovacao": {
                "type": "scatter",
                "title": "Ausência de Docentes x Taxa de Reprovação",
                "xLabel": "Total de Dias Ausentes",
                "yLabel": "Taxa de Reprovação",
                "data": analise_dois,
            },
            "tecnologia_saresp": {
                "type": "scatter",
                "title": "Tecnologia Escolar x Desempenho no SARESP",
                "xLabel": "Índice Tecnológico",
                "yLabel": "Média SARESP",
                "data": analise_tres,
            },
            "aluno_professor_aprovacao": {
                "type": "bar",
                "title": "Aluno por Professor x Aprovação",
                "labels": prof_labels,
                "datasets": [
                    {"label": "Aluno/Professor", "data": min_max(aluno_professor)},
                    {"label": "Aprovação", "data": min_max(aprovacao_professor)},
                ],
            },
            "evolucao_temporal": {
                "type": "line",
                "title": "Evolução Temporal dos Indicadores Educacionais",
                "labels": anos,
                "datasets": [
                    {"label": "SARESP", "data": min_max(saresp_values)},
                    {"label": "Aprovação", "data": min_max(aprovacao_values)},
                    {"label": "Infraestrutura", "data": min_max(infraestrutura_values)},
                    {"label": "Ausência Docente", "data": min_max(ausencia_values)},
                ],
            },
            "municipio_filtro": {
                "type": "filtered",
                "title": "Comparativo por Município Selecionado",
                "labels": [item["MUNICIPIO"] for item in ranking_rows],
                "datasets": [
                    {"label": "SARESP", "data": min_max([item["SARESP"] for item in ranking_rows])},
                    {"label": "Aprovação", "data": min_max([item["APROVACAO"] for item in ranking_rows])},
                    {"label": "Infraestrutura", "data": min_max([item["INFRAESTRUTURA"] for item in ranking_rows])},
                    {"label": "Ausência Docente", "data": min_max([item["AUSENCIA"] for item in ranking_rows])},
                ],
            },            "ranking_municipios": {
                "type": "bar",
                "title": "Ranking Geral dos Municípios",
                "labels": [item["MUNICIPIO"] for item in ranking],
                "datasets": [{"label": "Índice Educação", "data": [item["Índice Educação"] for item in ranking]}],
            },
        }), 200
    except Exception as exc:
        print(f"[CHART DATA ERROR] {exc}")
        return jsonify({"error": "Erro ao carregar dados dos graficos"}), 500
    finally:
        client.close()


if __name__ == "__main__":
    app.run(debug=True, port=8080)

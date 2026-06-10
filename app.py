import io
import json
import os
import textwrap
import threading
import requests
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import networkx as nx
from flask import Flask, jsonify, render_template, request, Response
from pymongo import MongoClient
from dotenv import load_dotenv
from sklearn.model_selection import train_test_split

load_dotenv()

app = Flask(__name__, template_folder="Template")
graph_render_lock = threading.Lock()


def get_mongo_client():
    mongo_uri = os.environ.get("MONGODB_URI") or os.environ.get("MONGO_URI")
    if not mongo_uri:
        raise RuntimeError("Variavel MONGODB_URI nao configurada")
    return MongoClient(mongo_uri)


# CONTEXTO DO BANCO
CHAT_SAMPLE_SIZE = 24
CHAT_PROJECTIONS = {
    "saresp": {
        "_id": 0, "MUNICÍPIOS": 1, "ANO": 1, "MÉDIA_PROFICIÊNCIA": 1,
    },
    "fluxo": {
        "_id": 0, "MUNICÍPIOS": 1, "ANO": 1,
        "APROVAÇÃO ANOS INICIAIS 9 ANOS": 1,
        "APROVAÇÃO ANOS FINAIS 9 ANOS": 1,
        "REPROVAÇÃO ANOS INICIAIS 9 ANOS": 1,
        "REPROVAÇÃO ANOS FINAIS 9 ANOS": 1,
    },
    "ausencia": {
        "_id": 0, "MUNICÍPIOS": 1, "ANO": 1, "TOTAL DIAS AUSENTES": 1,
    },
    "censo": {
        "_id": 0, "MUNICÍPIOS": 1, "ANO": 1, "BIBLIOTECA": 1,
        "LAB. INFORMÁTICA": 1, "LAB. CIÊNCIAS": 1, "INTERNET": 1,
        "INTERNET - ALUNOS": 1, "INTERNET - BANDA LARGA": 1,
    },
}


def get_stratified_db_sample(db, sample_size=CHAT_SAMPLE_SIZE):
    """Seleciona uma amostra proporcional por dataset para reduzir o prompt."""
    records = []
    for dataset_name, projection in CHAT_PROJECTIONS.items():
        for record in db[dataset_name].find({}, projection):
            record["_dataset"] = dataset_name
            records.append(record)

    if len(records) <= sample_size:
        return records

    strata = [record["_dataset"] for record in records]
    classes = len(set(strata))
    test_size = len(records) - sample_size

    if sample_size >= classes and test_size >= classes:
        sample, _ = train_test_split(
            records,
            train_size=sample_size,
            random_state=42,
            stratify=strata,
        )
        return sample

    return records[:sample_size]


def get_db_context():
    try:
        client = get_mongo_client()
        db = client["datasets"]

        saresp = db["saresp"]
        municipios = saresp.distinct("MUNICÍPIOS")
        anos = sorted(saresp.distinct("ANO"))
        sample = get_stratified_db_sample(db)
        context = (
            "=== DADOS EDUCACIONAIS RMC ===\n"
            f"Municípios disponíveis: {', '.join(str(m) for m in municipios)}\n"
            f"Anos disponíveis: {anos}\n"
            f"Amostra estratificada proporcional por dataset ({len(sample)} registros):\n"
            f"{json.dumps(sample, ensure_ascii=False, default=str, separators=(',', ':'))}"
        )

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

        def correlation(x_values, y_values):
            pairs = [
                (clean_number(x), clean_number(y))
                for x, y in zip(x_values, y_values)
                if clean_number(x) is not None and clean_number(y) is not None
            ]
            if len(pairs) < 2:
                return 0
            xs, ys = zip(*pairs)
            mean_x = sum(xs) / len(xs)
            mean_y = sum(ys) / len(ys)
            numerator = sum((x - mean_x) * (y - mean_y) for x, y in pairs)
            denominator_x = sum((x - mean_x) ** 2 for x in xs) ** 0.5
            denominator_y = sum((y - mean_y) ** 2 for y in ys) ** 0.5
            denominator = denominator_x * denominator_y
            return numerator / denominator if denominator else 0

        def correlation_analysis(points, x_name, y_name):
            if not points:
                return "Não há observações suficientes para produzir uma análise descritiva."
            coefficient = correlation(
                [item["x"] for item in points],
                [item["y"] for item in points],
            )
            strength = "forte" if abs(coefficient) >= 0.7 else "moderada" if abs(coefficient) >= 0.4 else "fraca"
            direction = "positiva" if coefficient > 0.05 else "negativa" if coefficient < -0.05 else "praticamente nula"
            top = max(points, key=lambda item: item["y"])
            return (
                f"Entre {len(points)} municípios, a associação entre {x_name} e {y_name} é "
                f"{strength} e {direction} (r={coefficient:.2f}). "
                f"{top['label']} apresenta o maior valor de {y_name} ({top['y']:.2f})."
            )

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
        professor_corr = correlation(aluno_professor, aprovacao_professor)
        professor_direction = "positiva" if professor_corr > 0.05 else "negativa" if professor_corr < -0.05 else "praticamente nula"
        temporal_changes = []
        temporal_series = [
            ("SARESP", saresp_values),
            ("aprovação", aprovacao_values),
            ("infraestrutura", infraestrutura_values),
            ("ausência docente", ausencia_values),
        ]
        for label, values in temporal_series:
            if len(values) >= 2 and values[0] is not None and values[-1] is not None:
                trend = "aumentou" if values[-1] > values[0] else "diminuiu" if values[-1] < values[0] else "permaneceu estável"
                temporal_changes.append(f"{label} {trend}")
        temporal_summary = ", ".join(temporal_changes) or "não houve séries suficientes para comparar o início e o fim"
        ranking_top = ", ".join(item["MUNICIPIO"] for item in ranking[:3])

        return jsonify({
            "infraestrutura_saresp": {
                "type": "scatter",
                "title": "Infraestrutura Escolar x Média SARESP",
                "xLabel": "Índice de Infraestrutura",
                "yLabel": "Média SARESP",
                "data": analise_um,
                "analysis": correlation_analysis(analise_um, "infraestrutura", "proficiência no SARESP"),
            },
            "ausencia_reprovacao": {
                "type": "scatter",
                "title": "Ausência de Docentes x Taxa de Reprovação",
                "xLabel": "Total de Dias Ausentes",
                "yLabel": "Taxa de Reprovação",
                "data": analise_dois,
                "analysis": correlation_analysis(analise_dois, "ausência docente", "reprovação"),
            },
            "tecnologia_saresp": {
                "type": "scatter",
                "title": "Tecnologia Escolar x Desempenho no SARESP",
                "xLabel": "Índice Tecnológico",
                "yLabel": "Média SARESP",
                "data": analise_tres,
                "analysis": correlation_analysis(analise_tres, "tecnologia escolar", "proficiência no SARESP"),
            },
            "aluno_professor_aprovacao": {
                "type": "bar",
                "title": "Aluno por Professor x Aprovação",
                "labels": prof_labels,
                "datasets": [
                    {"label": "Aluno/Professor", "data": min_max(aluno_professor)},
                    {"label": "Aprovação", "data": min_max(aprovacao_professor)},
                ],
                "analysis": (
                    f"A relação entre alunos por professor e aprovação é {professor_direction} "
                    f"(r={professor_corr:.2f}) nos {len(prof_labels)} municípios comparados. "
                    "Os valores foram normalizados para permitir a leitura conjunta das duas escalas."
                ),
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
                "analysis": (
                    f"No período de {anos[0]} a {anos[-1]}, {temporal_summary}. "
                    "As séries estão normalizadas entre 0 e 1 para destacar suas variações relativas."
                    if anos else "Não há anos em comum suficientes para produzir uma análise temporal."
                ),
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
                "analysis": (
                    f"O índice combina SARESP (40%), aprovação (30%), infraestrutura (20%) e menor ausência docente (10%). "
                    f"Os três municípios mais bem posicionados são {ranking_top}."
                    if ranking else "Não há dados completos suficientes para calcular o ranking municipal."
                ),
            },
        }), 200
    except Exception as exc:
        print(f"[CHART DATA ERROR] {exc}")
        return jsonify({"error": "Erro ao carregar dados dos graficos"}), 500
    finally:
        client.close()


# ROTA DOS GRAFOS BIPARTIDOS
@app.route("/api/grafo/<tipo>")
def grafo(tipo):
    """Gera separadamente o grafo de SARESP ou de ausência docente."""
    if tipo not in {"saresp", "ausencia"}:
        return jsonify({"error": "Tipo de grafo inválido"}), 404
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

        # ── Docentes totais por município ────────────────────────────────
        pipeline_docentes = [{
            "$group": {
                "_id": "$MUNICÍPIOS",
                "total_docentes": {
                    "$sum": {
                        "$convert": {
                            "input": "$QTDE DOCENTES FUNDAMENTAL - TOTAL",
                            "to": "double",
                            "onError": 0,
                            "onNull": 0,
                        }
                    }
                },
            }
        }]
        dados_docentes = {
            item["_id"]: item["total_docentes"]
            for item in db["censo"].aggregate(pipeline_docentes)
            if item["_id"]
        }

        # ── Total de dias ausentes por município ─────────────────────────
        pipeline_ausencia = [{
            "$group": {
                "_id": "$MUNICÍPIOS",
                "total_ausencia": {
                    "$sum": {
                        "$convert": {
                            "input": "$TOTAL DIAS AUSENTES",
                            "to": "double",
                            "onError": 0,
                            "onNull": 0,
                        }
                    }
                },
            }
        }]
        dados_ausencia = {
            item["_id"]: item["total_ausencia"]
            for item in db["ausencia"].aggregate(pipeline_ausencia)
            if item["_id"]
        }

        # ── Média SARESP por município ───────────────────────────────────
        pipeline_saresp = [{
            "$group": {
                "_id": "$MUNICÍPIOS",
                "media_saresp": {
                    "$avg": {
                        "$convert": {
                            "input": "$MÉDIA_PROFICIÊNCIA",
                            "to": "double",
                            "onError": None,
                            "onNull": None,
                        }
                    }
                },
            }
        }]
        dados_saresp = {
            item["_id"]: clean_number(item.get("media_saresp"))
            for item in db["saresp"].aggregate(pipeline_saresp)
            if item["_id"]
        }

        # ── Municípios com todos os dados disponíveis ────────────────────
        municipios = sorted(
            set(dados_docentes) & set(dados_ausencia) & set(dados_saresp)
        )

        if not municipios:
            return jsonify({"error": "Dados insuficientes para gerar o grafo"}), 500

        # ── Calcula taxa de ausência e classifica em faixas ──────────────
        def faixa_saresp(media):
            if media is None:
                return "Sem dados"
            if media < 200:
                return "<200"
            if media < 205:
                return "200-205"
            if media < 215:
                return "205-215"
            if media < 220:
                return "215-220"
            return "≥220"

        def faixa_ausencia(taxa):
            if taxa is None:
                return "Sem dados"
            if taxa < 0.5:
                return "<0,5"
            if taxa < 0.7:
                return "0,5-0,7"
            if taxa < 0.9:
                return "0,7-0,9"
            if taxa < 1.1:
                return "0,9-1,1"
            return "≥1,1"

        edges_saresp = []
        edges_ausencia = []
        for municipio in municipios:
            docentes = dados_docentes.get(municipio, 0)
            ausencia = dados_ausencia.get(municipio, 0)
            taxa = (ausencia / docentes) if docentes and docentes > 0 else None
            saresp = dados_saresp.get(municipio)
            edges_saresp.append((municipio, faixa_saresp(saresp)))
            edges_ausencia.append((municipio, faixa_ausencia(taxa)))

        faixas_saresp = ["<200", "200-205", "205-215", "215-220", "≥220"]
        faixas_ausencia = ["<0,5", "0,5-0,7", "0,7-0,9", "0,9-1,1", "≥1,1"]

        if tipo == "saresp":
            faixas = faixas_saresp
            edges = edges_saresp
            title = "Municípios × Faixa de SARESP"
            range_color = "#f5a623"
        else:
            faixas = faixas_ausencia
            edges = edges_ausencia
            title = "Municípios × Taxa de Ausência Docente"
            range_color = "#FF6B6B"

        graph = nx.Graph()
        graph.add_nodes_from(municipios, bipartite=0)
        graph.add_nodes_from(faixas, bipartite=1)
        graph.add_edges_from(edges)
        labels = {
            node: "\n".join(textwrap.wrap(node, width=12))
            for node in graph.nodes()
        }
        positions = nx.bipartite_layout(graph, municipios)

        # Matplotlib usa estado global; o lock evita conflito entre as duas imagens.
        with graph_render_lock:
            fig, axis = plt.subplots(figsize=(9, 8))
            fig.patch.set_facecolor("#161616")
            axis.set_facecolor("#161616")

            nx.draw_networkx_nodes(
                graph, positions, nodelist=municipios,
                node_color="#74BCFF", node_size=3000, ax=axis,
            )
            nx.draw_networkx_nodes(
                graph, positions, nodelist=faixas,
                node_color=range_color, node_size=2400, ax=axis,
            )
            nx.draw_networkx_labels(
                graph, positions, labels=labels, font_size=10,
                font_color="#0f0f0f", font_weight="bold", ax=axis,
            )
            nx.draw_networkx_edges(
                graph, positions, edge_color="#e8e8e8",
                alpha=0.6, ax=axis,
            )
            axis.set_title(title, color="#e8e8e8", fontsize=15, pad=18)
            axis.axis("off")
            plt.tight_layout()

            buf = io.BytesIO()
            fig.savefig(
                buf, format="png", dpi=130, bbox_inches="tight",
                facecolor=fig.get_facecolor(),
            )
            plt.close(fig)
            buf.seek(0)

        return Response(buf.getvalue(), mimetype="image/png")

    except Exception as exc:
        print(f"[GRAFO ERROR] {exc}")
        return jsonify({"error": "Erro ao gerar grafo"}), 500
    finally:
        client.close()


if __name__ == "__main__":
    app.run(debug=True, port=8080)

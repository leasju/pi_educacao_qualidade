<div align="center">
  <img src="https://raw.githubusercontent.com/leasju/pi_educacao_qualidade/main/static/edustats-logo-figma%201.png" alt="edu.stats" height="80"/>  
   
  <h3>Desigualdades Educacionais na Região Metropolitana de Campinas</h3>

  <p>
    <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white"/>
    <img src="https://img.shields.io/badge/MongoDB-47A248?style=for-the-badge&logo=mongodb&logoColor=white"/>
    <img src="https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white"/>
    <img src="https://img.shields.io/badge/Pandas-150458?style=for-the-badge&logo=pandas&logoColor=white"/>
  </p>

  <p>
    <a href="https://edustats-uckc.onrender.com">
      <img src="https://img.shields.io/badge/🌐_Acessar_Plataforma-F97316?style=for-the-badge"/>
    </a>
    <a href="https://github.com/leasju/pi_educacao_qualidade/blob/main/Notebooks/PI_AN%C3%81LISE.ipynb">
      <img src="https://img.shields.io/badge/📓_Ver_Notebook-gray?style=for-the-badge"/>
    </a>
  </p>

  <br/>

  <sub>
    Projeto Integrador · Bancos de Dados Não Relacionais · PUC-Campinas · 2026<br/>
    Prof. Felipe Cavalaro · Ciência de Dados e Inteligência Artificial
  </sub>
</div>

---

## 📌 Sobre o Projeto

A Região Metropolitana de Campinas concentra mais de **300 mil alunos** no Ensino Fundamental público. Apesar disso, os dados que explicam as diferenças de desempenho entre municípios estão fragmentados em bases federais e estaduais que nunca foram integradas.

O **edu.stats** resolve esse problema construindo um pipeline ELT que unifica dados de infraestrutura (INEP), proficiência (SARESP), fluxo escolar e absenteísmo docente (SEDUC-SP) em um repositório NoSQL, expondo os cruzamentos em um painel analítico interativo para apoiar gestores públicos da RMC.

---

## ✨ Funcionalidades

- 📊 **Painel analítico** com 6 gráficos interativos filtráveis por município, ano, competência e série
- 🕸️ **Grafos bipartidos** correlacionando municípios com faixas de SARESP e taxas de ausência docente
- 🔀 **Comparativo por município** com troca dinâmica entre barras, dispersão, linhas e radar
- 🤖 **Assistente IA** integrado via Open Router para interpretação dos dados em linguagem acessível

---

## 🛠️ Tecnologias

| Camada | Tecnologia |
|---|---|
| 🐍 Linguagem | Python 3.x |
| 🍃 Banco de Dados | MongoDB Atlas |
| 🔄 Pipeline ELT | Pandas · PyMongo · unicodedata |
| 📈 Análise Estatística | Scikit-learn · Seaborn · Matplotlib |
| 🕸️ Análise de Redes | NetworkX |
| 🌐 Back-end / Front-end | Flask |
| 🤖 IA Conversacional | Open Router |
| 🔀 Versionamento | Git / GitHub |

---

## 📁 Estrutura do Repositório

```
pi_educacao_qualidade/
├── 📂 Datasets Tratados/       # CSVs normalizados prontos para carga
├── 📂 Notebooks/
│   ├── PI_ANÁLISE.ipynb        # Pipeline ELT + gráficos e grafos
│   └── PI_ELT.ipynb            # Extração e tratamento dos dados brutos
├── 📂 app/                     # Aplicação Flask
├── .env.example                # Modelo de variáveis de ambiente
├── requirements.txt
└── README.md
```

---
## 🚀 Como Executar

**1. Clone o repositório**
```bash
git clone https://github.com/leasju/pi_educacao_qualidade.git
cd pi_educacao_qualidade
```

**2. Instale as dependências**
```bash
pip install -r requirements.txt
```

**3. Configure o banco de dados**

O projeto utiliza MongoDB Atlas como banco de dados. Para rodar localmente:

1. Crie uma conta gratuita em [mongodb.com/atlas](https://www.mongodb.com/atlas)
2. Crie um cluster gratuito (M0)
3. Obtenha a URI de conexão no painel do Atlas
4. Crie um arquivo `.env` na raiz do projeto:
```
MONGODB_URI=sua_uri_do_mongodb_atlas
```
5. Execute o notebook `Notebooks/PI_ANÁLISE.ipynb` — ele já carrega automaticamente os dados da pasta `Datasets Tratados/` no seu banco

**4. Execute a aplicação**
```bash
python app/app.py
```


Acesse em `http://localhost:5000`
---

## 🗃️ Fontes de Dados

Todos os dados são públicos e cobrem o período de **2022 a 2024**:

| Dataset | Fonte | Portal |
|---|---|---|
| 📝 SARESP | SEDUC-SP | [dados.educacao.sp.gov.br](https://dados.educacao.sp.gov.br/) |
| 🔄 Fluxo Escolar | SEDUC-SP | [dados.educacao.sp.gov.br](https://dados.educacao.sp.gov.br/) |
| 🏫 Ausências Docentes | SEDUC-SP | [dados.educacao.sp.gov.br](https://dados.educacao.sp.gov.br/) |
| 📊 Censo Escolar | INEP | [gov.br/inep](https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/censo-escolar) |

---

## 👥 Integrantes

<div align="center">

| | Nome | GitHub |
|---|---|---|
| 👩‍💻 | Julia Leandro | [@leasju](https://github.com/leasju) |
| 👨‍💻 | Enzo Guerra | [@vooort](https://github.com/vooort) |
| 👩‍💻 | Alice Pasolini | [@paso-lini](https://github.com/paso-lini) |
| 👩‍💻 | Lavínia Oliveira | [@LaviniaOliveira-2007](https://github.com/LaviniaOliveira-2007) |
| 👨‍💻 | Guilherme Cintra | [@GeeGum065](https://github.com/GeeGum065) |

</div>

---

<div align="center">
  <sub>Feito com 🧡 por estudantes de Ciência de Dados da PUC-Campinas · 2026</sub>
</div>

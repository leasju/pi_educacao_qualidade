# PI: Educação de Qualidade na RMC - Análise de Dados e MongoDB

Este projeto é parte do componente curricular **Bancos de Dados Não Relacionais (Projeto Integrador)** do curso de Ciência de Dados e Inteligência Artificial da **Escola Politécnica - PUC-Campinas**.

## Sobre o Projeto
O objetivo é analisar a qualidade educacional no Ensino Fundamental da Região Metropolitana de Campinas (RMC) através de uma perspectiva sistêmica e multidimensional. O projeto resolve o problema da fragmentação de dados governamentais, integrando bases de infraestrutura (Federal) e desempenho/gestão (Estadual) em um repositório NoSQL.

### Problemática
Atualmente, dados de proficiência (SARESP) e assiduidade docente (SEDUC-SP) residem em silos isolados dos dados de infraestrutura (INEP). Essa falta de interoperabilidade técnica dificulta consultas que correlacionem o impacto da estrutura física no aprendizado discente.

## Tecnologias Utilizadas
- **Linguagem:** Python 3.x
- **Banco de Dados:** MongoDB (NoSQL orientado a documentos)
- **Processamento de Dados:** Pandas
- **Análise de Redes:** NetworkX
- **Interface Visual:** Streamlit
- **Versionamento:** GitHub

## Estrutura de Dados
O projeto integra quatro frentes de dados (2022-2024):
1. **SARESP:** Médias de proficiência em Língua Portuguesa e Matemática.
2. **Fluxo Escolar:** Taxas de aprovação e reprovação.
3. **Ausências de Servidores:** Impacto do absenteísmo docente.
4. **Censo Escolar (INEP):** Infraestrutura física (Laboratórios, Internet, Bibliotecas).

## 🚀 Como Executar o Projeto

1. **Clone o repositório:**
   ```bash
   git clone [https://github.com/leasju/pi_educacao_qualidade.git](https://github.com/leasju/pi_educacao_qualidade.git)

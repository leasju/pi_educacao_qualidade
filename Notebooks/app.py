import importnb  # noqa: F401
import streamlit as st

# Importar o notebook como módulo
with importnb.Notebook():
    import PI_ANÁLISE as pi

# Dashboard interativo
for itens in pi.arquivos.values():
    pi.visualizar(itens)
import os
from flask import Flask, render_template

app = Flask(__name__)



BASE_DIR = os.path.dirname(os.path.abspath(__file__))

caminho_index = os.path.join(BASE_DIR, "Template", "index.html")

@app.route("/")
def home():
    return render_template(caminho_index)
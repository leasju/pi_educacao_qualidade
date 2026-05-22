import plotly.express as px
from flask import Flask, render_template

app = Flask(__name__, template_folder="Template")

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

    return render_template(
        "index.html", graph_html=graph_html)

if __name__ == "__main__":
    app.run(debug=True, port=8080)



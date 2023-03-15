import re

import numpy
import pandas as pd
from flasgger import LazyJSONEncoder, LazyString, Swagger, swag_from
from flask import Flask, jsonify, render_template, request

abusive = ["benci", "jelek", "bego", "julid"]

app = Flask(__name__)

###############################################################################################################
app.json_encoder = LazyJSONEncoder

swagger_template = dict(
    info={
        "title": LazyString(
            lambda: "API Documentation for Data Processing and Modeling"
        ),
        "version": LazyString(lambda: "1.0.0"),
        "description": LazyString(
            lambda: "Dokumentasi API untuk Data Processing dan Modeling"
        ),
    },
    host=LazyString(lambda: request.host),
)

swagger_config = {
    "headers": [],
    "specs": [{"endpoint": "docs", "route": "/docs.json"}],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/docs/",
}

swagger = Swagger(app, template=swagger_template, config=swagger_config)
###############################################################################################################


@app.route("/")
def home():
    return "hello"


@swag_from("docs/post16.yml", methods=["POST"])
@app.route("/gold", methods=["POST"])
def gold():
    input_json = request.get_json(force=True)
    text = input_json["Tweet"]
    text = text.lower()
    text = re.split(" ", text)

    for i in text:
        for j in abusive:
            if i == j:
                index = text.index(i)
                text[index] = "**sensor**"

    text = " ".join(map(str, text))
    text = {"Tweet": text}

    return jsonify(text)


@swag_from("docs/upload16.yml", methods=["POST"])
@app.route("/upload", methods=["POST"])
def uploadDoc():
    file = request.files["file"]

    try:
        data = pd.read_csv(file, encoding="iso-8859-1", error_bad_lines=False)
    except:
        data = pd.read_csv(file, encoding="utf-8", error_bad_lines=False)

    data["Tweet_New"] = data["Tweet"].str.lower()

    data = data.to_dict("records")
    data = data[0]

    return jsonify(data)


if __name__ == "__main__":
    app.run()


### run flask otomatis debug
# flask --app test_demo_swag --debug run


import json

### testing api
import requests

data = {"Tweet": "saya benci kamu karena kamu bego dan sangat jelek"}
json_object = json.dumps(data)
r = requests.post(url="http://127.0.0.1:5000/gold", data=json_object)
print(r.text)

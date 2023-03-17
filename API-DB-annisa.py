import csv
import json
import os
import re
import sqlite3

import numpy as np
import pandas as pd
import requests
from flasgger import LazyJSONEncoder, LazyString, Swagger, swag_from
from flask import Flask, jsonify, render_template, render_template_string, request

# membaca data dari file CSV
df_data_tweet = pd.read_csv("data.csv", encoding="latin-1")

# membuat mapping antara kata tidak baku dan baku
df_new_kamusalay = pd.read_csv("new_kamusalay.csv", encoding="latin-1", header=None)
df_new_kamusalay = df_new_kamusalay.rename(columns={0: "original", 1: "new"})
df_new_kamusalay = df_new_kamusalay.set_index("original")["new"].to_dict()

# membaca data kata abusive dari file CSV
df_abusive = pd.read_csv("abusive.csv", header=None)
df_abusive = df_abusive.rename(columns={0: "ABUSIVE"})


# bersihkan dulu kata
def cleansing_stop_word(text):
    text = re.sub("-", " ", text)  # Remove tanda strip
    text = re.sub("[^0-9a-zA-Z]+", " ", text)  # Remove all Symbol
    text = re.sub("  +", " ", text)  # Remove extra spaces
    text = re.sub("\n", " ", text)  # Remove every '\n'
    text = re.sub("#", " ", text)  # Remove every retweet symbol
    text = re.sub("user", " ", text)  # Remove every username
    text = re.sub("USER", " ", text)  # Remove every username
    text = re.sub(
        "((www\.[^\s]+)|(https?://[^\s]+)|(http?://[^\s]+))", " ", text
    )  # Remove every URL
    text = re.sub("[\d\.]+", "", text)  # Remove angka
    text = re.sub("!", " ", text)
    text = re.sub(r"[\t\s]+", " ", text)  # Menghapus spasi berlebih
    text = re.sub(r"[^\w\s]", "", text)  # Menghapus tanda baca
    return text.lower()


# change word
def change_word(text):
    # Cleansing Kata Alay
    for word in text.split(" "):
        if word in df_new_kamusalay:
            text = text.replace(word, df_new_kamusalay[word])
    # Cleansing Kata Abusive
    for word in text.split(" "):
        if word in df_abusive.ABUSIVE.values:
            text = text.replace(word, "***")
    text = text.strip()  # Remove Space awal akhir
    return text.lower()


def preprocessing(text):
    text = cleansing_stop_word(text)  # 1
    text = change_word(text)  # 2
    return text


# Preprocessing setiap kalimat dalam data
for i, row in df_data_tweet.iterrows():
    kalimat = row["Tweet"]
    kalimat = preprocessing(kalimat)
    df_data_tweet.loc[i, "Tweet"] = kalimat


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
    return render_template("1_index.html")

# GET API DATA DARI TABLE INPUT
@swag_from("docs/get_tweet.yml", methods=["GET"])
@app.route("/input", methods=["GET"])
def get_api_input():
    conn = sqlite3.connect("api_db_tweet.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM text_tweet")
    rows = cursor.fetchall()
    conn.close()

    append_row = []
    for row in rows:
        append_row.append({"id": row[0], "tweet": row[1], "tweet_baru": row[2]})

    json_response = {"Get API from Output Cleansing": append_row}

    response_data = jsonify(json_response)
    return response_data

@swag_from("docs/post16.yml", methods=["POST"])
@app.route("/input", methods=["POST"])
def Challenge_gold():
    input_json = request.get_json(force=True)
    text = input_json["Tweet"]
    Hasil = preprocessing(text)  # memproses keseluruhan teks

    df = pd.DataFrame(
        {"id": [None], "tweet": [text]}
    )  # menambahkan nilai None ke kolom id
    with sqlite3.connect("api_db_tweet.db") as conn:
        cursor = conn.cursor()

        # menambahkan tweet ke dalam tabel text_tweet
        cursor.execute(
            "INSERT INTO text_tweet (id, tweet, tweet_baru) VALUES (?, ?, ?)",
            (None, text, Hasil),  # menggunakan None sebagai nilai awal untuk id
        )

        conn.commit()

    response = {"tweet": text, "Hasil": Hasil}
    return jsonify(response)


@swag_from("docs/upload16.yml", methods=["POST"])
@app.route("/upload", methods=["POST"])
def uploadDoc():
    # Mengunggah file CSV
    file = request.files["file"]

    try:
        data = pd.read_csv(file, encoding="iso-8859-1", error_bad_lines=False)
    except:
        data = pd.read_csv(file, encoding="utf-8", error_bad_lines=False)

    # Memproses setiap baris dari file CSV dan menyimpannya ke dalam database
    with sqlite3.connect("api_db_tweet.db") as conn:
        cursor = conn.cursor()
        for row in data.iterrows():
            text = row[1]["Tweet"]
            hasil = preprocessing(text)

            # Menyimpan data ke dalam database SQLite
            df = pd.DataFrame({"id": [None], "tweet": [text]})
            df.to_sql("upload_text_tweet", conn, if_exists="append", index=False)
            cursor.execute(
                "INSERT INTO upload_text_tweet (tweet, tweet_baru) VALUES (?, ?)",
                (text, hasil),
            )

        conn.commit()

    response = {"status": "success"}
    return json.dumps(response)


#####################################################################################################################################################################

# PUT dan DELETE berdasarkan id dalam text_tweet


@swag_from("docs/put.yml", methods=["PUT"])
@app.route("/PUT/<int:id>", methods=["PUT"])
def update_tweet_id(id):
    input_json = request.get_json(force=True)
    text = input_json["Tweet"]
    Hasil = preprocessing(text)  # memproses keseluruhan teks

    with sqlite3.connect("api_db_tweet.db") as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE text_tweet SET tweet = ?, tweet_baru = ? WHERE id = ?",
            (text, Hasil, id),
        )
        conn.commit()
    response = {"id": id, "tweet": text, "tweet_baru": Hasil}
    return json.dumps(response)


@swag_from("docs/delete.yml", methods=["DELETE"])
@app.route("/DELETE/<int:id>", methods=["DELETE"])
def delete_tweet_id(id):
    with sqlite3.connect("api_db_tweet.db") as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM text_tweet WHERE id = ?", (id,))
        conn.commit()

    response = {"status": "success delete"}
    return json.dumps(response)


if __name__ == "__main__":
    # app.debug = True
    app.run()


### run flask otomatis debug
# flask --app test_demo_swag --debug run


# import json

### testing api
import requests

# data = {"Tweet": "saya benci kamu karena kamu bego dan sangat jelek"}
# json_object = json.dumps(data)
# r = requests.post(url="http://127.0.0.1:5000/gold", data=json_object)
# print(r.text)

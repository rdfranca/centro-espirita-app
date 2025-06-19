from flask import Flask, render_template, request, redirect
import mysql.connector
import os

app = Flask(__name__)

@app.route("/")
def index():
    conn = mysql.connector.connect(
        host=os.getenv('DB_HOST'),
        port=int(os.getenv('DB_PORT', 3306)),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME')
    )
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM trabalhadores ORDER BY nome")
    trabalhadores = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("index.html", trabalhadores=trabalhadores)

@app.route("/cadastrar")
def cadastrar():
    return render_template("cadastrar.html")

@app.route("/inserir", methods=["POST"])
def inserir():
    nome = request.form['nome']
    cpf = request.form['cpf']
    celular = request.form.get('celular', '')
    profissao = request.form.get('profissao', '')
    setor = request.form.get('setor', '')

    conn = mysql.connector.connect(
        host=os.getenv('DB_HOST'),
        port=int(os.getenv('DB_PORT', 3306)),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME')
    )
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO trabalhadores (nome, cpf, celular, profissao, setor) VALUES (%s, %s, %s, %s, %s)",
        (nome, cpf, celular, profissao, setor)
    )
    conn.commit()
    cursor.close()
    conn.close()
    return redirect("/")

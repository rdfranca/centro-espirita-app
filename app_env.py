from flask import Flask, render_template, request, redirect
import mysql.connector
import os

app = Flask(__name__)

def get_connection():
    return mysql.connector.connect(
        host=os.getenv('DB_HOST'),
        port=int(os.getenv('DB_PORT', 3306)),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME')
    )

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/buscar", methods=["POST"])
def buscar():
    termo = request.form['termo']
    tipo = request.form['tipo']
    query = ""
    if tipo == "nome":
        query = "SELECT * FROM trabalhadores WHERE nome LIKE %s"
    elif tipo == "cpf":
        query = "SELECT * FROM trabalhadores WHERE cpf = %s"
    elif tipo == "setor":
        query = "SELECT * FROM trabalhadores WHERE setor LIKE %s"

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query, ('%' + termo + '%',))
    resultados = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("resultado.html", resultados=resultados)

@app.route("/cadastrar")
def cadastrar():
    return render_template("cadastrar.html")

@app.route("/inserir", methods=["POST"])
def inserir():
    nome = request.form['nome']
    cpf = request.form['cpf'][:20]
    celular = request.form.get('celular', '')
    profissao = request.form.get('profissao', '')
    setor = request.form.get('setor', '')

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO trabalhadores (nome, cpf, celular, profissao, setor) VALUES (%s, %s, %s, %s, %s)",
        (nome, cpf, celular, profissao, setor)
    )
    conn.commit()
    cursor.close()
    conn.close()
    return redirect("/")

@app.route("/editar-form", methods=["POST"])
def editar_form():
    return render_template("editar.html",
                           id=request.form['id'],
                           nome=request.form['nome'],
                           cpf=request.form['cpf'],
                           celular=request.form['celular'],
                           profissao=request.form['profissao'],
                           setor=request.form['setor'])

@app.route("/editar", methods=["POST"])
def editar():
    id_trab = request.form['id']
    nome = request.form['nome']
    cpf = request.form['cpf'][:20]
    celular = request.form['celular']
    profissao = request.form['profissao']
    setor = request.form['setor']

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE trabalhadores SET nome = %s, cpf = %s, celular = %s, profissao = %s, setor = %s WHERE id = %s",
        (nome, cpf, celular, profissao, setor, id_trab)
    )
    conn.commit()
    cursor.close()
    conn.close()
    return redirect("/")

from flask import Flask, render_template, request, redirect, jsonify
import psycopg2
import os

app = Flask(__name__)

def conectar():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST"),
        database=os.environ.get("DB_NAME"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
        port=os.environ.get("DB_PORT", 5432)
    )

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/cadastrar")
def cadastrar():
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome FROM setores ORDER BY nome")
    setores = cursor.fetchall()
    cursor.execute("SELECT id, nome, setor_id FROM funcao ORDER BY nome")
    funcoes = cursor.fetchall()
    conn.close()
    return render_template("cadastrar.html", setores=setores, funcoes=funcoes)

@app.route("/funcoes/<int:setor_id>")
def funcoes_por_setor(setor_id):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome FROM funcao WHERE setor_id = %s ORDER BY nome", (setor_id,))
    funcoes = cursor.fetchall()
    conn.close()
    return jsonify(funcoes)


@app.route("/inserir", methods=["POST"])
def inserir():
    conn = conectar()
    cursor = conn.cursor()
    nome = request.form.get("nome")
    cpf = request.form.get("cpf")
    data_nascimento = request.form.get("data_nascimento")
    telefone = request.form.get("celular")
    email = request.form.get("email")
    setor_id = request.form.get("setor")
    funcao_id = request.form.get("funcao")
    turno = request.form.get("turno")

    cursor.execute("""
        INSERT INTO trabalhador (nome, cpf, data_nascimento, telefone, email)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
    """, (nome, cpf, data_nascimento, telefone, email))
    trabalhador_id = cursor.fetchone()[0]

    cursor.execute("""
        INSERT INTO trabalhador_setor_funcao (trabalhador_id, setor_id, funcao_id, turno)
        VALUES (%s, %s, %s, %s)
    """, (trabalhador_id, setor_id, funcao_id, turno))

    conn.commit()
    conn.close()

    return redirect("/")

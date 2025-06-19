
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
        query = "SELECT * FROM trabalhadores WHERE setores LIKE %s"

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
    data_nascimento = request.form.get('data_nascimento', '')
    celular = request.form.get('celular', '')
    profissao = request.form.get('profissao', '')
    email = request.form.get('email', '')
    endereco = request.form.get('endereco', '')
    cep = request.form.get('cep', '')
    bairro = request.form.get('bairro', '')
    setores = ', '.join(request.form.getlist('setores'))

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO trabalhadores 
        (nome, cpf, data_nascimento, celular, profissao, email, endereco, cep, bairro, setores) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (nome, cpf, data_nascimento, celular, profissao, email, endereco, cep, bairro, setores)
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
                           data_nascimento=request.form['data_nascimento'],
                           celular=request.form['celular'],
                           profissao=request.form['profissao'],
                           email=request.form['email'],
                           endereco=request.form['endereco'],
                           cep=request.form['cep'],
                           bairro=request.form['bairro'],
                           setores=request.form['setores'])

@app.route("/editar", methods=["POST"])
def editar():
    id_trab = request.form['id']
    nome = request.form['nome']
    cpf = request.form['cpf'][:20]
    data_nascimento = request.form['data_nascimento']
    celular = request.form['celular']
    profissao = request.form['profissao']
    email = request.form['email']
    endereco = request.form['endereco']
    cep = request.form['cep']
    bairro = request.form['bairro']
    setores = ', '.join(request.form.getlist('setores'))

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """UPDATE trabalhadores SET 
        nome = %s, cpf = %s, data_nascimento = %s, celular = %s,
        profissao = %s, email = %s, endereco = %s, cep = %s, bairro = %s, setores = %s
        WHERE id = %s""",
        (nome, cpf, data_nascimento, celular, profissao, email, endereco, cep, bairro, setores, id_trab)
    )
    conn.commit()
    cursor.close()
    conn.close()
    return redirect("/")

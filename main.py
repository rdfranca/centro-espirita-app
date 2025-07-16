from flask import Flask, render_template, request, redirect, jsonify, url_for
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
    return redirect(url_for("login"))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == 'admin' and password == 'admin':
            return redirect(url_for('index'))
        else:
            return "Usuário ou senha inválidos"
    return render_template('login.html')


@app.route("/buscar", methods=["GET"])
def buscar():
    nome = request.args.get("nome")
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT t.id, t.nome, t.cpf, t.celular, t.data_nascimento,
               ARRAY_AGG(DISTINCT s.nome) AS setores,
               ARRAY_AGG(DISTINCT f.nome) AS funcoes,
               ARRAY_AGG(DISTINCT tsf.turno) AS turnos
        FROM trabalhador t
        LEFT JOIN trabalhador_setor_funcao tsf ON t.id = tsf.trabalhador_id
        LEFT JOIN setores s ON tsf.setor_id = s.id
        LEFT JOIN funcao f ON tsf.funcao_id = f.id
        WHERE t.nome ILIKE %s OR t.cpf ILIKE %s
        GROUP BY t.id
    """, (f"%{nome}%", f"%{nome}%"))
    resultados = cursor.fetchall()
    conn.close()
    return render_template("resultado.html", resultados=resultados)

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
    celular = request.form.get("celular")
    email = request.form.get("email")
    setor_id = request.form.get("setor")
    funcao_id = request.form.get("funcao")
    turno = request.form.get("turno")

    cursor.execute("""
        INSERT INTO trabalhador (nome, cpf, data_nascimento, celular, email)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
    """, (nome, cpf, data_nascimento, celular, email))
    trabalhador_id = cursor.fetchone()[0]

    cursor.execute("""
        INSERT INTO trabalhador_setor_funcao (trabalhador_id, setor_id, funcao_id, turno)
        VALUES (%s, %s, %s, %s)
    """, (trabalhador_id, setor_id, funcao_id, turno))

    conn.commit()
    conn.close()

    return redirect("/")

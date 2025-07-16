
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
    data_nascimento = request.form.get("nascimento")
    celular = request.form.get("celular")
    profissao = request.form.get("profissao")

    cep = request.form.get("cep")
    rua = request.form.get("rua")
    numero = request.form.get("numero")
    bairro = request.form.get("bairro")
    cidade = request.form.get("cidade")
    estado = request.form.get("estado")

    setores = request.form.getlist("setores[]")
    funcoes = request.form.getlist("funcoes[]")
    turnos = request.form.getlist("turnos[]")

    cursor.execute("""
        INSERT INTO trabalhador (nome, cpf, data_nascimento, celular, profissao)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
    """, (nome, cpf, data_nascimento, celular, profissao))
    trabalhador_id = cursor.fetchone()[0]

    cursor.execute("""
        INSERT INTO endereco (trabalhador_id, cep, rua, numero, bairro, cidade, estado)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (trabalhador_id, cep, rua, numero, bairro, cidade, estado))

    for setor_id, funcao_id, turno in zip(setores, funcoes, turnos):
        cursor.execute("""
            INSERT INTO trabalhador_setor_funcao (trabalhador_id, setor_id, funcao_id, turno)
            VALUES (%s, %s, %s, %s)
        """, (trabalhador_id, setor_id, funcao_id, turno))

    conn.commit()
    conn.close()

    return redirect("/")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

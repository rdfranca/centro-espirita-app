
import os
import psycopg2
from flask import Flask, render_template, request, redirect

app = Flask(__name__)

def conectar():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/buscar", methods=["POST"])
def buscar():
    nome = request.form["nome"]
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT t.id, t.nome, t.cpf, t.celular, t.profissao, t.data_nascimento, e.cep, e.rua, e.numero, e.bairro, e.cidade, e.estado,
               ARRAY_AGG(DISTINCT s.nome) AS setores,
               ARRAY_AGG(DISTINCT f.nome) AS funcoes,
               ARRAY_AGG(DISTINCT tsf.turno) AS turnos
        FROM trabalhador t
        LEFT JOIN endereco e ON t.id = e.trabalhador_id
        LEFT JOIN trabalhador_setores_funcao tsf ON t.id = tsf.trabalhador_id
        LEFT JOIN setores s ON tsf.setores_id = s.id
        LEFT JOIN funcao f ON tsf.funcao_id = f.id
        WHERE t.nome ILIKE %s OR t.cpf ILIKE %s
        GROUP BY t.id, e.cep, e.rua, e.numero, e.bairro, e.cidade, e.estado
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
    cursor.execute("SELECT id, nome FROM funcao ORDER BY nome")
    funcoes = cursor.fetchall()
    conn.close()
    return render_template("cadastrar.html", setores=setores, funcoes=funcoes)

@app.route("/inserir", methods=["POST"])
def inserir():
    nome = request.form["nome"]
    cpf = request.form["cpf"]
    celular = request.form["celular"]
    profissao = request.form["profissao"]
    nascimento = request.form["nascimento"]

    cep = request.form["cep"]
    rua = request.form["rua"]
    numero = request.form["numero"]
    bairro = request.form["bairro"]
    cidade = request.form["cidade"]
    estado = request.form["estado"]

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO trabalhador (nome, cpf, celular, profissao, data_nascimento)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
    """, (nome, cpf, celular, profissao, nascimento))
    trabalhador_id = cursor.fetchone()[0]

    cursor.execute("""
        INSERT INTO endereco (trabalhador_id, cep, rua, numero, bairro, cidade, estado)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (trabalhador_id, cep, rua, numero, bairro, cidade, estado))

    setores = request.form.getlist("setores[]")
    funcoes = request.form.getlist("funcoes[]")
    turnos = request.form.getlist("turnos[]")

    for setores_id, funcao_id, turno in zip(setores, funcoes, turnos):
        cursor.execute("""
            INSERT INTO trabalhador_setores_funcao (trabalhador_id, setores_id, funcao_id, turno)
            VALUES (%s, %s, %s, %s)
        """, (trabalhador_id, setores_id, funcao_id, turno))

    conn.commit()
    conn.close()
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)

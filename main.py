
import os
import psycopg2
from flask import Flask, render_template, request, redirect

app = Flask(__name__)

# Conexão com o banco de dados PostgreSQL (Supabase)
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
    termo = request.form["termo"]
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT t.id, t.nome, t.cpf, t.celular, t.profissao, e.cep, e.rua, e.numero, e.bairro, e.cidade, e.estado,
               ARRAY_AGG(s.nome) as setores
        FROM trabalhadores t
        LEFT JOIN enderecos e ON t.id = e.trabalhador_id
        LEFT JOIN trabalhador_setor ts ON t.id = ts.trabalhador_id
        LEFT JOIN setores s ON ts.setor_id = s.id
        WHERE t.nome ILIKE %s OR t.cpf ILIKE %s
        GROUP BY t.id, e.cep, e.rua, e.numero, e.bairro, e.cidade, e.estado
    """, (f"%{termo}%", f"%{termo}%"))
    resultados = cursor.fetchall()
    conn.close()
    return render_template("resultado.html", resultados=resultados)

@app.route("/cadastrar")
def cadastrar():
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome FROM setores ORDER BY nome")
    setores = cursor.fetchall()
    conn.close()
    return render_template("cadastrar.html", setores=setores)

@app.route("/inserir", methods=["POST"])
def inserir():
    nome = request.form["nome"]
    cpf = request.form["cpf"]
    celular = request.form["celular"]
    profissao = request.form["profissao"]
    nascimento = request.form["nascimento"]
    setores = request.form.getlist("setores")

    cep = request.form["cep"]
    rua = request.form["rua"]
    numero = request.form["numero"]
    bairro = request.form["bairro"]
    cidade = request.form["cidade"]
    estado = request.form["estado"]

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO trabalhadores (nome, cpf, celular, profissao, data_nascimento)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
    """, (nome, cpf, celular, profissao, nascimento))
    trabalhador_id = cursor.fetchone()[0]

    cursor.execute("""
        INSERT INTO enderecos (trabalhador_id, cep, rua, numero, bairro, cidade, estado)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (trabalhador_id, cep, rua, numero, bairro, cidade, estado))

    for setor_id in setores:
        cursor.execute("""
            INSERT INTO trabalhador_setor (trabalhador_id, setor_id)
            VALUES (%s, %s)
        """, (trabalhador_id, setor_id))

    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/editar-form", methods=["POST"])
def editar_form():
    trabalhador_id = request.form["id"]
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("SELECT id, nome, cpf, celular, profissao, data_nascimento FROM trabalhadores WHERE id = %s", (trabalhador_id,))
    trabalhador = cursor.fetchone()

    cursor.execute("SELECT * FROM enderecos WHERE trabalhador_id = %s", (trabalhador_id,))
    endereco = cursor.fetchone()

    cursor.execute("SELECT setor_id FROM trabalhador_setor WHERE trabalhador_id = %s", (trabalhador_id,))
    setores_trabalhador = [row[0] for row in cursor.fetchall()]

    cursor.execute("SELECT id, nome FROM setores ORDER BY nome")
    todos_setores = cursor.fetchall()

    conn.close()
    return render_template("editar.html", trabalhador=trabalhador, endereco=endereco, setores_trabalhador=setores_trabalhador, todos_setores=todos_setores)

@app.route("/editar", methods=["POST"])
def editar():
    trabalhador_id = request.form["id"]
    nome = request.form["nome"]
    cpf = request.form["cpf"]
    celular = request.form["celular"]
    profissao = request.form["profissao"]
    nascimento = request.form["nascimento"]
    setores = request.form.getlist("setores")

    cep = request.form["cep"]
    rua = request.form["rua"]
    numero = request.form["numero"]
    bairro = request.form["bairro"]
    cidade = request.form["cidade"]
    estado = request.form["estado"]

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE trabalhadores
        SET nome=%s, cpf=%s, celular=%s, profissao=%s, data_nascimento=%s
        WHERE id=%s
    """, (nome, cpf, celular, profissao, nascimento, trabalhador_id))

    cursor.execute("""
        UPDATE enderecos
        SET cep=%s, rua=%s, numero=%s, bairro=%s, cidade=%s, estado=%s
        WHERE trabalhador_id=%s
    """, (cep, rua, numero, bairro, cidade, estado, trabalhador_id))

    cursor.execute("DELETE FROM trabalhador_setor WHERE trabalhador_id=%s", (trabalhador_id,))
    for setor_id in setores:
        cursor.execute("""
            INSERT INTO trabalhador_setor (trabalhador_id, setor_id)
            VALUES (%s, %s)
        """, (trabalhador_id, setor_id))

    conn.commit()
    conn.close()
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)

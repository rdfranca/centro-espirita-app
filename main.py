
from flask import Flask, render_template, request, redirect, jsonify
import psycopg2

app = Flask(__name__)

def conectar():
    return psycopg2.connect(
        host="localhost",
        database="seubanco",
        user="seuusuario",
        password="suasenha"
    )

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
    resultados = cursor.fetchall()
    conn.close()
    return jsonify(resultados)

@app.route("/")
def index():
    return redirect("/cadastrar")

if __name__ == "__main__":
    app.run(debug=True)

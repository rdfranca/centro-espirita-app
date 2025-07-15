
from flask import Flask, render_template, request, redirect, url_for
from app_env import conectar
app = Flask(__name__)

@app.route('/')
def index():
    conn = conectar()
    cur = conn.cursor()
    cur.execute("SELECT * FROM trabalhador")
    trabalhadores = cur.fetchall()
    conn.close()
    return render_template("index.html", trabalhadores=trabalhadores)

@app.route('/cadastrar', methods=['GET', 'POST'])
def cadastrar():
    conn = conectar()
    cur = conn.cursor()
    if request.method == 'POST':
        nome = request.form['nome']
        cur.execute("INSERT INTO trabalhador (nome) VALUES (%s)", (nome,))
        conn.commit()
        return redirect(url_for('index'))
    conn.close()
    return render_template("cadastrar.html")

@app.route('/funcoes/<int:setor_id>')
def funcoes(setor_id):
    conn = conectar()
    cur = conn.cursor()
    cur.execute("SELECT id, nome FROM funcao WHERE setor_id = %s", (setor_id,))
    funcoes = cur.fetchall()
    conn.close()
    return {'funcoes': funcoes}

if __name__ == '__main__':
    app.run(debug=True)

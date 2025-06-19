
from flask import Flask, render_template, request, redirect
import mysql.connector
import os

app = Flask(__name__)

# Conexão com o banco de dados MySQL usando variáveis de ambiente
conn = mysql.connector.connect(
    host=os.getenv('DB_HOST', 'localhost'),
    port=int(os.getenv('DB_PORT', 3306)),
    user=os.getenv('DB_USER', 'root'),
    password=os.getenv('DB_PASSWORD', ''),
    database=os.getenv('DB_NAME', 'centro_espirita')
)
cursor = conn.cursor(dictionary=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/buscar', methods=['POST'])
def buscar():
    tipo = request.form['tipo']
    termo = request.form['termo']
    query = ""
    if tipo == 'nome':
        query = "SELECT * FROM trabalhadores WHERE nome LIKE %s"
    elif tipo == 'cpf':
        query = "SELECT * FROM trabalhadores WHERE cpf = %s"
    elif tipo == 'setor':
        query = "SELECT * FROM trabalhadores WHERE setor LIKE %s"
    cursor.execute(query, ('%' + termo + '%',))
    resultados = cursor.fetchall()
    return render_template('resultado.html', resultados=resultados)

@app.route('/editar-form', methods=['POST'])
def editar_form():
    return render_template('editar.html', nome=request.form['nome'],
                           celular=request.form['celular'],
                           profissao=request.form['profissao'],
                           setor=request.form['setor'],
                           id=request.form['id'])

@app.route('/editar', methods=['POST'])
def editar():
    id_trab = request.form['id']
    celular = request.form['celular']
    profissao = request.form['profissao']
    setor = request.form['setor']
    cursor.execute("""UPDATE trabalhadores 
                      SET celular = %s, profissao = %s, setor = %s 
                      WHERE id = %s""", (celular, profissao, setor, id_trab))
    conn.commit()
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)

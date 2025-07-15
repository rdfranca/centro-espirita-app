from flask import Flask, render_template, request, redirect, url_for
import psycopg2

app = Flask(__name__)

def conectar():
    return psycopg2.connect(
        host="localhost",
        database="seu_banco",
        user="seu_usuario",
        password="sua_senha"
    )

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/cadastrar')
def cadastrar():
    return render_template('cadastrar.html')

# Outras rotas...

if __name__ == '__main__':
    app.run()

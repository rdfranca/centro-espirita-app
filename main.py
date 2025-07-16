
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        # Aqui você pode colocar validação de usuário/senha
        if username == 'admin' and password == 'admin':
            return redirect(url_for('buscar_ou_cadastrar'))
        else:
            return "Usuário ou senha inválidos"
    return render_template('login.html')

@app.route('/buscar_ou_cadastrar')
def buscar_ou_cadastrar():
    return render_template('index.html')

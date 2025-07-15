
from flask import Flask, render_template, request, redirect

app = Flask(__name__)

trabalhadores = []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/cadastrar', methods=['GET', 'POST'])
def cadastrar():
    if request.method == 'POST':
        nome = request.form.get('nome')
        if nome:
            trabalhadores.append(nome)
            return redirect('/')
    return render_template('cadastrar.html')

@app.route('/buscar')
def buscar():
    nome = request.args.get('nome', '').lower()
    if nome:
        resultados = [n for n in trabalhadores if nome in n.lower()]
    else:
        resultados = []
    return render_template('buscar.html', resultados=resultados)

if __name__ == '__main__':
    app.run(debug=True)

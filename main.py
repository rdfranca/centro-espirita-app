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
           return redirect(url_for('painel'))
        else:
            return "Usuário ou senha inválidos"
    return render_template('login.html')

@app.route('/painel')
def painel():
    return render_template('index.html')


@app.route("/buscar", methods=["GET"])
def buscar():
    nome = request.args.get("nome")
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT t.id, t.nome, t.cpf, t.celular, t.profissao, t.data_nascimento,
               e.cep, e.rua, e.numero, e.bairro, e.cidade, e.estado
        FROM trabalhador t
        LEFT JOIN endereco e ON t.id = e.trabalhador_id
        WHERE t.nome ILIKE %s OR t.cpf ILIKE %s
    """, (f"%{nome}%", f"%{nome}%"))
    trabalhadores = cursor.fetchall()

    resultados = []
    for t in trabalhadores:
        cursor.execute("""
            SELECT DISTINCT s.nome, f.nome, tsf.turno
            FROM trabalhador_setor_funcao tsf
            LEFT JOIN setores s ON tsf.setor_id = s.id
            LEFT JOIN funcao f ON tsf.funcao_id = f.id
            WHERE tsf.trabalhador_id = %s
        """, (t[0],))
        vinculos = cursor.fetchall()

        vinculos_formatados = []
        for v in vinculos:
            setor, funcao, turno = v
            if setor and funcao and turno:
                vinculos_formatados.append({
                    "setor": setor,
                    "funcao": funcao,
                    "turno": turno
                })

        resultados.append({
            "id": t[0], 
            "nome": t[1],
            "cpf": t[2],
            "celular": t[3],
            "profissao": t[4],
            "nascimento": t[5],
            "cep": t[6],
            "rua": t[7],
            "numero": t[8],
            "bairro": t[9],
            "cidade": t[10],
            "estado": t[11],
            "vinculos": vinculos_formatados
        })

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


def validar_cpf(cpf):
    if not cpf.isdigit() or len(cpf) != 11:
        return False

    if cpf == cpf[0] * 11:
        return False

    def calc_digito(cpf, peso):
        soma = sum(int(dig) * p for dig, p in zip(cpf, peso))
        resto = soma % 11
        return '0' if resto < 2 else str(11 - resto)

    digito1 = calc_digito(cpf[:9], range(10, 1, -1))
    digito2 = calc_digito(cpf[:9] + digito1, range(11, 1, -1))

    return cpf[-2:] == digito1 + digito2


@app.route("/inserir", methods=["POST"])
def inserir():
    conn = conectar()
    cursor = conn.cursor()

    nome = request.form.get("nome")
    cpf = request.form.get("cpf")
    if not validar_cpf(cpf):
        return "CPF inválido. Certifique-se de digitar um CPF válido com 11 dígitos.", 400

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

@app.route('/editar/<int:trabalhador_id>')
def editar(trabalhador_id):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT t.id, t.nome, t.cpf, t.celular, t.profissao, t.data_nascimento,
               e.cep, e.rua, e.numero, e.bairro, e.cidade, e.estado
        FROM trabalhador t
        LEFT JOIN endereco e ON t.id = e.trabalhador_id
        WHERE t.id = %s
    """, (trabalhador_id,))
    trabalhador = cursor.fetchone()

    cursor.execute("SELECT id, nome FROM setores")
    setores = cursor.fetchall()

    cursor.execute("SELECT id, nome, setor_id FROM funcao")
    funcoes = cursor.fetchall()

    cursor.execute("""
        SELECT tsf.setor_id, tsf.funcao_id, tsf.turno
        FROM trabalhador_setor_funcao tsf
        WHERE tsf.trabalhador_id = %s
    """, (trabalhador_id,))
    vinculos = cursor.fetchall()

    return render_template("editar.html", trabalhador=trabalhador, setores=setores, funcoes=funcoes, vinculos=vinculos)

@app.route('/atualizar/<int:trabalhador_id>', methods=['POST'])
def atualizar(trabalhador_id):
    conn = conectar()
    cursor = conn.cursor()

    nome = request.form.get("nome")
    cpf = request.form.get("cpf")
    celular = request.form.get("celular")
    profissao = request.form.get("profissao")
    nascimento = request.form.get("nascimento")

    cep = request.form.get("cep")
    rua = request.form.get("rua")
    numero = request.form.get("numero")
    bairro = request.form.get("bairro")
    cidade = request.form.get("cidade")
    estado = request.form.get("estado")

    setores = request.form.getlist("setores[]")
    funcoes = request.form.getlist("funcoes[]")
    turnos = request.form.getlist("turnos[]")

    # Atualizar trabalhador
    cursor.execute("""
        UPDATE trabalhador SET nome=%s, cpf=%s, celular=%s, profissao=%s, data_nascimento=%s
        WHERE id=%s
    """, (nome, cpf, celular, profissao, nascimento, trabalhador_id))

    # Atualizar endereço
    cursor.execute("""
        UPDATE endereco SET cep=%s, rua=%s, numero=%s, bairro=%s, cidade=%s, estado=%s
        WHERE trabalhador_id=%s
    """, (cep, rua, numero, bairro, cidade, estado, trabalhador_id))

    # Apagar vínculos antigos
    cursor.execute("DELETE FROM trabalhador_setor_funcao WHERE trabalhador_id=%s", (trabalhador_id,))

    # Inserir novos vínculos
    for setor_id, funcao_id, turno in zip(setores, funcoes, turnos):
        cursor.execute("""
            INSERT INTO trabalhador_setor_funcao (trabalhador_id, setor_id, funcao_id, turno)
            VALUES (%s, %s, %s, %s)
        """, (trabalhador_id, setor_id, funcao_id, turno))

    conn.commit()
    conn.close()
    return redirect("/")

@app.route('/api/relatorios')
def api_relatorios():
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT 
            t.id, t.nome, t.cpf, t.celular, t.profissao, t.data_nascimento,
            e.cep, e.rua, e.numero, e.bairro, e.cidade, e.estado,
            s.nome AS setor, f.nome AS funcao, tsf.turno
        FROM trabalhador t
        LEFT JOIN endereco e ON t.id = e.trabalhador_id
        LEFT JOIN trabalhador_setor_funcao tsf ON t.id = tsf.trabalhador_id
        LEFT JOIN setores s ON tsf.setor_id = s.id
        LEFT JOIN funcao f ON tsf.funcao_id = f.id
    """

    cursor.execute(query)
    dados = cursor.fetchall()

    lista = []
    for row in dados:
        lista.append({
            "id": row[0],
            "nome": row[1],
            "cpf": row[2],
            "celular": row[3],
            "profissao": row[4],
            "nascimento": row[5],
            "cep": row[6],
            "rua": row[7],
            "numero": row[8],
            "bairro": row[9],
            "cidade": row[10],
            "estado": row[11],
            "setor": row[12],
            "funcao": row[13],
            "turno": row[14]
        })

    conn.close()
    return jsonify(lista)

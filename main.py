from flask import Flask, render_template, request, redirect, jsonify, url_for, session, flash
import psycopg2
import os
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from collections import defaultdict

app = Flask(__name__)

app.secret_key = os.environ.get("FLASK_SECRET_KEY", "sua_chave_secreta_muito_segura_e_aleatoria_aqui_12345")
ID_SETOR_ENSINO = 11

def conectar():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST"),
        database=os.environ.get("DB_NAME"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
        port=os.environ.get("DB_PORT", 5432)
    )

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'trabalhador_id' not in session:
            flash("Você precisa fazer login para acessar esta página.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route("/")
def index():
    return redirect(url_for("login"))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('username')
        password = request.form.get('password')

        conn = conectar()
        cursor = conn.cursor()
        cursor.execute("SELECT id, senha_hash FROM trabalhador WHERE email = %s", (email,))
        trabalhador_data = cursor.fetchone()
        conn.close()

        if trabalhador_data and trabalhador_data[1] and check_password_hash(trabalhador_data[1], password):
            session['trabalhador_id'] = trabalhador_data[0]
            flash("Login realizado com sucesso!", "success")
            return redirect(url_for('painel'))
        else:
            flash("Usuário (Email) ou senha inválidos.", "danger")
            return render_template('login.html')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('trabalhador_id', None)
    flash("Você foi desconectado.", "info")
    return redirect(url_for('login'))

@app.route('/painel')
@login_required
def painel():
    return render_template('index.html')

@app.route("/buscar", methods=["GET"])
@login_required
def buscar():
    nome_busca = request.args.get("nome", "").strip()
    conn = conectar()
    cursor = conn.cursor()

    trabalhadores_agrupados = defaultdict(lambda: {
        "id": None, "nome": None, "cpf": None, "celular": None, "profissao": None,
        "nascimento": None, "cep": None, "rua": None, "numero": None, "bairro": None,
        "cidade": None, "estado": None, "complemento": None, "email": None,
        "vinculos": [], "cursos_ensino": []
    })

    if nome_busca:
        cursor.execute("""
            SELECT DISTINCT ON (t.id) t.id, t.nome, t.cpf, t.celular, t.profissao, t.data_nascimento,
                   e.cep, e.rua, e.numero, e.bairro, e.cidade, e.estado, e.complemento, t.email
            FROM trabalhador t
            LEFT JOIN endereco e ON t.id = e.trabalhador_id
            WHERE t.nome ILIKE %s OR t.cpf ILIKE %s
            ORDER BY t.id
        """, (f"%{nome_busca}%", f"%{nome_busca}%"))
        trabalhadores_raw = cursor.fetchall()

        for t_data in trabalhadores_raw:
            trabalhador_id = t_data[0]
            trabalhadores_agrupados[trabalhador_id].update({
                "id": t_data[0],
                "nome": t_data[1],
                "cpf": t_data[2],
                "celular": t_data[3],
                "profissao": t_data[4],
                "nascimento": t_data[5],
                "cep": t_data[6],
                "rua": t_data[7],
                "numero": t_data[8],
                "bairro": t_data[9],
                "cidade": t_data[10],
                "estado": t_data[11],
                "complemento": t_data[12],
                "email": t_data[13]
            })

        if trabalhadores_agrupados:
            trabalhador_ids = tuple(trabalhadores_agrupados.keys())
            cursor.execute(f"""
                SELECT tsf.trabalhador_id, s.nome, f.nome, tsf.turno, tsf.dias_da_semana
                FROM trabalhador_setor_funcao tsf
                LEFT JOIN setores s ON tsf.setor_id = s.id
                LEFT JOIN funcao f ON tsf.funcao_id = f.id
                WHERE tsf.trabalhador_id IN %s
            """, (trabalhador_ids,))
            vinculos_raw = cursor.fetchall()

            vinculos_por_trabalhador = defaultdict(lambda: defaultdict(lambda: {
                "funcoes": set(), "turnos": set(), "dias": set()
            }))

            for v_data in vinculos_raw:
                trabalhador_id = v_data[0]
                setor, funcao, turno, dias_da_semana = v_data[1], v_data[2], v_data[3], v_data[4]
                if setor and funcao and turno:
                    chave = setor.strip().lower()
                    vinculos_por_trabalhador[trabalhador_id][chave]["funcoes"].add(funcao)
                    vinculos_por_trabalhador[trabalhador_id][chave]["turnos"].add(turno)
                    if dias_da_semana:
                        vinculos_por_trabalhador[trabalhador_id][chave]["dias"].add(dias_da_semana)

            for trabalhador_id, setores_info in vinculos_por_trabalhador.items():
                for setor_nome, info in setores_info.items():
                    trabalhadores_agrupados[trabalhador_id]["vinculos"].append({
                        "setor": setor_nome,
                        "funcao": ", ".join(sorted(info["funcoes"])),
                        "turno": ", ".join(sorted(info["turnos"])),
                        "dias_da_semana": ", ".join(sorted(info["dias"]))
                    })

            cursor.execute(f"""
                SELECT tce.trabalhador_id, ce.nome
                FROM trabalhador_curso_ensino tce
                JOIN cursos_ensino ce ON tce.curso_id = ce.id
                WHERE tce.trabalhador_id IN %s
            """, (trabalhador_ids,))
            cursos_raw = cursor.fetchall()

            for c_data in cursos_raw:
                trabalhador_id = c_data[0]
                curso_nome = c_data[1]
                trabalhadores_agrupados[trabalhador_id]["cursos_ensino"].append(curso_nome)

    resultados = list(trabalhadores_agrupados.values())
    conn.close()
    return render_template("resultado.html", resultados=resultados)

@app.route('/editar/<int:trabalhador_id>', methods=['GET', 'POST'])
@login_required
def editar(trabalhador_id):
    return render_template("editar.html", trabalhador_id=trabalhador_id)

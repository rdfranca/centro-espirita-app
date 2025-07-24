from flask import Flask, render_template, request, redirect, jsonify, url_for, session, flash
import psycopg2
import os
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)

# --- CONFIGURAÇÃO DE SESSÃO ---
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "sua_chave_secreta_muito_segura_e_aleatoria_aqui_12345")
# --- FIM CONFIGURAÇÃO DE SESSÃO ---


def conectar():
    """
    Função para estabelecer conexão com o banco de dados PostgreSQL.
    As credenciais são obtidas de variáveis de ambiente.
    """
    return psycopg2.connect(
        host=os.environ.get("DB_HOST"),
        database=os.environ.get("DB_NAME"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
        port=os.environ.get("DB_PORT", 5432)
    )

# --- DECORADOR PARA PROTEGER ROTAS ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'trabalhador_id' not in session:
            flash("Você precisa fazer login para acessar esta página.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function
# --- FIM DECORADOR ---

@app.route("/")
def index():
    """Redireciona para a página de login."""
    return redirect(url_for("login"))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Lida com a autenticação do usuário.
    Agora verifica email e senha_hash no banco de dados e armazena o ID na sessão.
    """
    if request.method == 'POST':
        email = request.form.get('username')
        password = request.form.get('password')

        conn = conectar()
        cursor = conn.cursor()
        cursor.execute("SELECT id, senha_hash FROM trabalhador WHERE email = %s", (email,))
        trabalhador_data = cursor.fetchone()
        conn.close()

        if trabalhador_data and trabalhador_data[1] and check_password_hash(trabalhador_data[1], password):
            # Autenticação bem-sucedida
            session['trabalhador_id'] = trabalhador_data[0] # Armazena o ID do trabalhador na sessão
            flash("Login realizado com sucesso!", "success")
            return redirect(url_for('painel'))
        else:
            flash("Usuário (Email) ou senha inválidos.", "danger")
            return render_template('login.html') # Renderiza o login novamente com a mensagem de erro
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Remove o usuário da sessão."""
    session.pop('trabalhador_id', None)
    flash("Você foi desconectado.", "info")
    return redirect(url_for('login'))

@app.route('/painel')
@login_required # Protege esta rota
def painel():
    """Renderiza a página do painel principal."""
    return render_template('index.html')

@app.route("/buscar", methods=["GET"])
@login_required # Protege esta rota
def buscar():
    """
    Busca trabalhadores por nome ou CPF e retorna os resultados.
    Inclui os vínculos de setor, função e turno de cada trabalhador.
    """
    nome = request.args.get("nome")
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT t.id, t.nome, t.cpf, t.celular, t.profissao, t.data_nascimento,
               e.cep, e.rua, e.numero, e.bairro, e.cidade, e.estado, e.complemento, t.email
        FROM trabalhador t
        LEFT JOIN endereco e ON t.id = e.trabalhador_id
        WHERE t.nome ILIKE %s OR t.cpf ILIKE %s
    """, (f"%{nome}%", f"%{nome}%"))
    trabalhadores = cursor.fetchall()

    resultados = []
    for t in trabalhadores:
        cursor.execute("""
            SELECT DISTINCT s.nome, f.nome, tsf.turno, tsf.dias_da_semana
            FROM trabalhador_setor_funcao tsf
            LEFT JOIN setores s ON tsf.setor_id = s.id
            LEFT JOIN funcao f ON tsf.funcao_id = f.id
            WHERE tsf.trabalhador_id = %s
        """, (t[0],))
        vinculos = cursor.fetchall()

        vinculos_formatados = []
        for v in vinculos:
            setor, funcao, turno, dias_da_semana = v
            if setor and funcao and turno:
                vinculos_formatados.append({
                    "setor": setor,
                    "funcao": funcao,
                    "turno": turno,
                    "dias_da_semana": dias_da_semana
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
            "complemento": t[12],
            "email": t[13],
            "vinculos": vinculos_formatados
        })

    conn.close()
    return render_template("resultado.html", resultados=resultados)

@app.route("/cadastrar")
@login_required # Protege esta rota
def cadastrar():
    """
    Renderiza a página de cadastro de trabalhadores.
    Busca todos os setores para preencher os selects iniciais.
    """
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome FROM setores ORDER BY nome")
    setores = cursor.fetchall()
    conn.close()
    return render_template("cadastrar.html", setores=setores) # Passa apenas setores

@app.route('/api/funcoes_por_setor/<int:setor_id>', methods=['GET'])
@login_required # Protege esta rota
def api_funcoes_por_setor(setor_id):
    """
    Retorna as funções associadas a um setor específico para uso em filtros e formulários, em formato JSON.
    """
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute('SELECT id, nome FROM funcao WHERE setor_id = %s ORDER BY nome', (setor_id,))
    funcoes = cursor.fetchall()
    conn.close()
    return jsonify([{'id': f[0], 'nome': f[1]} for f in funcoes])

def validar_cpf(cpf):
    """
    Valida um número de CPF.
    Retorna True se o CPF for válido, False caso contrário.
    """
    # Remove caracteres não numéricos
    cpf = ''.join(filter(str.isdigit, cpf))

    if not cpf or len(cpf) != 11:
        return False

    # Verifica se todos os dígitos são iguais (ex: "111.111.111-11")
    if cpf == cpf[0] * 11:
        return False

    # Validação do primeiro dígito verificador
    soma = 0
    for i in range(9):
        soma += int(cpf[i]) * (10 - i)
    resto = (soma * 10) % 11
    if resto == 10 or resto == 11:
        resto = 0
    if resto != int(cpf[9]):
        return False

    # Validação do segundo dígito verificador
    soma = 0
    for i in range(10):
        soma += int(cpf[i]) * (11 - i)
    resto = (soma * 10) % 11
    if resto == 10 or resto == 11:
        resto = 0
    if resto != int(cpf[10]):
        return False

    return True

@app.route("/inserir", methods=["POST"])
@login_required # Protege esta rota
def inserir():
    """
    Insere um novo trabalhador, seu endereço, email, senha e seus vínculos de setor/função/turno no banco de dados.
    """
    conn = conectar()
    cursor = conn.cursor()

    nome = request.form.get("nome")
    cpf = request.form.get("cpf").replace('.', '').replace('-', '') # Remove máscara
    if not validar_cpf(cpf):
        conn.close()
        flash("CPF inválido. Certifique-se de digitar um CPF válido com 11 dígitos.", "danger")
        return redirect(url_for('cadastrar'))

    data_nascimento = request.form.get("nascimento")
    celular = request.form.get("celular")
    profissao = request.form.get("profissao")

    email = request.form.get("email")
    password = request.form.get("password")
    hashed_password = generate_password_hash(password)

    cep = request.form.get("cep")
    rua = request.form.get("rua")
    numero = request.form.get("numero")
    bairro = request.form.get("bairro")
    cidade = request.form.get("cidade")
    estado = request.form.get("estado")
    complemento = request.form.get("complemento")

    setores = request.form.getlist("setores[]")
    funcoes = request.form.getlist("funcoes[]")
    turnos = request.form.getlist("turnos[]")
    dias_da_semana_por_vinculo = request.form.getlist("dias_da_semana[]")


    try:
        cursor.execute("""
            INSERT INTO trabalhador (nome, cpf, data_nascimento, celular, profissao, email, senha_hash)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (nome, cpf, data_nascimento, celular, profissao, email, hashed_password))
        trabalhador_id = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO endereco (trabalhador_id, cep, rua, numero, bairro, cidade, estado, complemento)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (trabalhador_id, cep, rua, numero, bairro, cidade, estado, complemento))

        for i in range(len(setores)):
            setor_id = setores[i]
            funcao_id = funcoes[i]
            turno = turnos[i]
            dias_da_semana_str = dias_da_semana_por_vinculo[i] if i < len(dias_da_semana_por_vinculo) else ""

            cursor.execute("""
                INSERT INTO trabalhador_setor_funcao (trabalhador_id, setor_id, funcao_id, turno, dias_da_semana)
                VALUES (%s, %s, %s, %s, %s)
            """, (trabalhador_id, setor_id, funcao_id, turno, dias_da_semana_str))

        conn.commit()
        flash("Trabalhador cadastrado com sucesso!", "success")
        return redirect(url_for('painel'))
    except Exception as e:
        conn.rollback()
        flash(f"Erro ao cadastrar trabalhador: {str(e)}", "danger")
        return redirect(url_for('cadastrar'))
    finally:
        conn.close()


@app.route('/editar/<int:trabalhador_id>')
@login_required # Protege esta rota
def editar(trabalhador_id):
    """
    Renderiza a página de edição de um trabalhador específico.
    Busca os dados do trabalhador, setores e vínculos existentes.
    """
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT t.id, t.nome, t.cpf, t.celular, t.profissao, t.data_nascimento,
               e.cep, e.rua, e.numero, e.bairro, e.cidade, e.estado, e.complemento, t.email, t.senha_hash
        FROM trabalhador t
        LEFT JOIN endereco e ON t.id = e.trabalhador_id
        WHERE t.id = %s
    """, (trabalhador_id,))
    trabalhador = cursor.fetchone()

    cursor.execute("SELECT id, nome FROM setores ORDER BY nome")
    setores = cursor.fetchall()

    cursor.execute("""
        SELECT tsf.setor_id, tsf.funcao_id, tsf.turno, tsf.dias_da_semana
        FROM trabalhador_setor_funcao tsf
        WHERE tsf.trabalhador_id = %s
    """, (trabalhador_id,))
    vinculos = cursor.fetchall()

    conn.close()
    return render_template("editar.html", trabalhador=trabalhador, setores=setores, vinculos=vinculos)


@app.route('/atualizar/<int:trabalhador_id>', methods=['POST'])
@login_required # Protege esta rota
def atualizar(trabalhador_id):
    """
    Atualiza os dados de um trabalhador existente, seu endereço e seus vínculos.
    """
    conn = conectar()
    cursor = conn.cursor()

    nome = request.form.get("nome")
    cpf = request.form.get("cpf").replace('.', '').replace('-', '') # Remove máscara
    if not validar_cpf(cpf): # Valida o CPF novamente
        conn.close()
        flash("CPF inválido. Certifique-se de digitar um CPF válido com 11 dígitos.", "danger")
        return redirect(url_for('editar', trabalhador_id=trabalhador_id))

    celular = request.form.get("celular")
    profissao = request.form.get("profissao")
    nascimento = request.form.get("nascimento")

    email = request.form.get("email")
    password = request.form.get("password")

    setores = request.form.getlist("setores[]")
    funcoes = request.form.getlist("funcoes[]")
    turnos = request.form.getlist("turnos[]")
    dias_da_semana_por_vinculo = request.form.getlist("dias_da_semana[]")

    try:
        # Apenas atualiza o hash da senha se uma nova senha for fornecida
        if password:
            hashed_password = generate_password_hash(password)
            cursor.execute("""
                UPDATE trabalhador SET nome=%s, cpf=%s, celular=%s, profissao=%s, data_nascimento=%s,
                email=%s, senha_hash=%s
                WHERE id=%s
            """, (nome, cpf, celular, profissao, nascimento, email, hashed_password, trabalhador_id))
        else:
            cursor.execute("""
                UPDATE trabalhador SET nome=%s, cpf=%s, celular=%s, profissao=%s, data_nascimento=%s,
                email=%s
                WHERE id=%s
            """, (nome, cpf, celular, profissao, nascimento, email, trabalhador_id))


        cep = request.form.get("cep")
        rua = request.form.get("rua")
        numero = request.form.get("numero")
        bairro = request.form.get("bairro")
        cidade = request.form.get("cidade")
        estado = request.form.get("estado")
        complemento = request.form.get("complemento")

        # Atualizar endereço
        cursor.execute("""
            UPDATE endereco SET cep=%s, rua=%s, numero=%s, bairro=%s, cidade=%s, estado=%s, complemento=%s
            WHERE trabalhador_id=%s
        """, (cep, rua, numero, bairro, cidade, estado, complemento, trabalhador_id))

        # Apagar vínculos antigos
        cursor.execute("DELETE FROM trabalhador_setor_funcao WHERE trabalhador_id=%s", (trabalhador_id,))

        # Inserir novos vínculos
        for i in range(len(setores)):
            setor_id = setores[i]
            funcao_id = funcoes[i]
            turno = turnos[i]
            dias_da_semana_str = dias_da_semana_por_vinculo[i] if i < len(dias_da_semana_por_vinculo) else ""

            cursor.execute("""
                INSERT INTO trabalhador_setor_funcao (trabalhador_id, setor_id, funcao_id, turno, dias_da_semana)
                VALUES (%s, %s, %s, %s, %s)
            """, (trabalhador_id, setor_id, funcao_id, turno, dias_da_semana_str))

        conn.commit()
        flash("Dados do trabalhador atualizados com sucesso!", "success")
        return redirect(url_for('painel'))
    except Exception as e:
        conn.rollback()
        flash(f"Erro ao atualizar trabalhador: {str(e)}", "danger")
        return redirect(url_for('editar', trabalhador_id=trabalhador_id))
    finally:
        conn.close()

@app.route('/deletar/<int:trabalhador_id>', methods=['POST'])
@login_required # Protege esta rota
def deletar_trabalhador(trabalhador_id):
    """
    Exclui um trabalhador e todos os seus dados relacionados (endereço e vínculos) do banco de dados.
    """
    conn = conectar()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM trabalhador_setor_funcao WHERE trabalhador_id = %s", (trabalhador_id,))
        cursor.execute("DELETE FROM endereco WHERE trabalhador_id = %s", (trabalhador_id,))
        cursor.execute("DELETE FROM trabalhador WHERE id = %s", (trabalhador_id,))
        conn.commit()
        flash("Trabalhador excluído com sucesso!", "success")
        return jsonify({"success": True, "message": "Trabalhador excluído com sucesso!"}), 200
    except Exception as e:
        conn.rollback()
        print(f"Erro ao excluir trabalhador: {e}")
        flash(f"Erro ao excluir trabalhador: {str(e)}", "danger")
        return jsonify({"success": False, "message": f"Erro ao excluir trabalhador: {str(e)}"}), 500
    finally:
        conn.close()

@app.route('/relatorios')
@login_required # Protege esta rota
def relatorios():
    """Renderiza a página de relatórios."""
    return render_template("relatorios.html")

@app.route('/api/relatorios')
@login_required # Protege esta rota
def api_relatorios():
    """
    Retorna todos os dados de trabalhadores, endereços e seus vínculos em formato JSON.
    """
    conn = conectar()
    cursor = conn.cursor()

    query = """
        SELECT
            t.id, t.nome, t.cpf, t.celular, t.profissao, t.data_nascimento,
            e.cep, e.rua, e.numero, e.bairro, e.cidade, e.estado, e.complemento,
            s.nome AS setor, f.nome AS funcao, tsf.turno, tsf.dias_da_semana,
            t.email
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
            "complemento": row[12],
            "setor": row[13],
            "funcao": row[14],
            "turno": row[15],
            "dias_da_semana": row[16],
            "email": row[17]
        })

    conn.close()
    return jsonify(lista)

@app.route('/api/setores_para_filtro', methods=['GET'])
@login_required # Protege esta rota
def api_setores_para_filtro():
    """
    Retorna todos os setores disponíveis para uso em filtros, em formato JSON.
    """
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute('SELECT id, nome FROM setores ORDER BY nome')
    setores = cursor.fetchall()
    conn.close()
    return jsonify([{'id': s[0], 'nome': s[1]} for s in setores])

if __name__ == '__main__':
    app.run(debug=True)
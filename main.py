from flask import Flask, render_template, request, redirect, jsonify, url_for, session, flash
import psycopg2
import os
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import uuid 

app = Flask(__name__)

# --- CONFIGURAÇÃO DE SESSÃO ---
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "sua_chave_secreta_muito_segura_e_aleatoria_aqui_12345")
# --- FIM CONFIGURAÇÃO DE SESSÃO ---

# ATENÇÃO: SUBSTITUA PELO ID REAL DO SETOR 'ENSINO' QUE VOCÊ OBTEVE NO BANCO DE DADOS.
# Para obter este ID, execute no seu banco de dados: SELECT id FROM setores WHERE lower(nome) = 'ensino';
# Se o setor 'Ensino' não existir, cadastre-o primeiro na página 'Gerenciar Estrutura'.
ID_SETOR_ENSINO = 11 # <<<<<<<< SUBSTITUA ESTE VALOR PELO ID REAL DO SEU SETOR 'ENSINO'

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
            session['usuario'] = trabalhador_data[0]
            flash("Login realizado com sucesso!", "success")
            return redirect(url_for('painel'))
        else:
            flash("Usuário (Email) ou senha inválidos.", "danger")
            return render_template('login.html')
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Remove o usuário da sessão."""
    session.pop('trabalhador_id', None)
    flash("Você foi desconectado.", "info")
    return redirect(url_for('login'))

@app.route('/painel')
@login_required
def painel():
    """Renderiza a página do painel principal."""
    return render_template('index.html')

@app.route("/buscar", methods=["GET"])
@login_required
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

        # NOVO: Buscar cursos associados ao trabalhador para exibir nos resultados
        cursor.execute("""
            SELECT ce.nome
            FROM trabalhador_curso_ensino tce
            JOIN cursos_ensino ce ON tce.curso_id = ce.id
            WHERE tce.trabalhador_id = %s
        """, (t[0],))
        cursos_trabalhador = [row[0] for row in cursor.fetchall()]


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
            "vinculos": vinculos_formatados,
            "cursos_ensino": cursos_trabalhador # NOVO: Adiciona cursos ao resultado
        })

    conn.close()
    return render_template("resultado.html", resultados=resultados)

@app.route("/cadastrar")
#@login_required
def cadastrar():
    """
    Renderiza a página de cadastro de trabalhadores.
    Busca todos os setores, cursos disponíveis e mapeamento de função para setor.
    """
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome FROM setores ORDER BY nome")
    setores = cursor.fetchall()
    
    cursor.execute("SELECT id, nome FROM cursos_ensino ORDER BY nome")
    cursos_disponiveis = cursor.fetchall()

    # NOVO: Mapeamento de funcao_id para setor_id
    cursor.execute("SELECT id, setor_id FROM funcao")
    funcao_setor_map = {row[0]: row[1] for row in cursor.fetchall()}

    conn.close()
    return render_template("cadastrar.html", setores=setores,
                           cursos_disponiveis=cursos_disponiveis,
                           id_setor_ensino=ID_SETOR_ENSINO,       # ID do SETOR Ensino
                           funcao_setor_map=funcao_setor_map)    # Mapeamento funcao->setor

@app.route('/api/funcoes_por_setor/<int:setor_id>', methods=['GET'])
@login_required
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

def enviar_email_confirmacao(destinatario, nome, assunto='Cadastro no Centro Espírita confirmado', corpo=None):
    if not corpo:
        corpo = f"""
        <p>Olá, {nome}!</p>
        <p>Seu cadastro foi realizado com sucesso em nosso sistema.</p>
        <p>Seja muito bem-vindo(a) ao nosso Centro Espírita 🙏✨</p>
        <p>Com carinho,<br>Equipe Luz do Consolador</p>
        """

    mensagem = Mail(
        from_email='ti@ensinounificadocre.com.br',
        to_emails=destinatario,
        subject=assunto,
        html_content=corpo
    )

    try:
        sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        sg.send(mensagem)
    except Exception as e:
        print(f"Erro ao enviar e-mail: {str(e)}")

@app.route("/inserir", methods=["POST"])
@login_required
def inserir():
    """
    Insere um novo trabalhador, seu endereço, email, senha, vínculos e cursos de ensino no banco de dados.
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
    print("VÍNCULOS ENVIADOS:")
    print(list(zip(setores, funcoes, turnos, dias_da_semana_por_vinculo)))
    cursos_selecionados = request.form.getlist("cursos_ensino[]") # Pega os cursos selecionados do formulário

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

        for setor_id, funcao_id, turno, dias_da_semana_str in zip(setores, funcoes, turnos, dias_da_semana_por_vinculo):
            cursor.execute("""
                INSERT INTO trabalhador_setor_funcao (trabalhador_id, setor_id, funcao_id, turno, dias_da_semana)
                VALUES (%s, %s, %s, %s, %s)
             """, (trabalhador_id, setor_id, funcao_id, turno, dias_da_semana_str))
        
        # Inserir cursos de ensino selecionados para o trabalhador
        for curso_id in cursos_selecionados:
            cursor.execute("""
                INSERT INTO trabalhador_curso_ensino (trabalhador_id, curso_id)
                VALUES (%s, %s)
            """, (trabalhador_id, curso_id))

        conn.commit()
        flash("Trabalhador cadastrado com sucesso!", "success")
        enviar_email_confirmacao(email, nome)
        return redirect(url_for('painel'))
    except Exception as e:
        conn.rollback()
        flash(f"Erro ao cadastrar trabalhador: {str(e)}", "danger")
        return redirect(url_for('cadastrar'))
    finally:
        conn.close()


@app.route('/editar/<int:trabalhador_id>')
@login_required
def editar(trabalhador_id):
    """
    Renderiza a página de edição de um trabalhador específico.
    Busca os dados do trabalhador, setores, vínculos existentes, cursos associados e mapeamento de função para setor.
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

    cursor.execute("SELECT id, nome FROM cursos_ensino ORDER BY nome")
    cursos_disponiveis = cursor.fetchall()

    cursor.execute("""
        SELECT tce.curso_id
        FROM trabalhador_curso_ensino tce
        WHERE tce.trabalhador_id = %s
    """, (trabalhador_id,))
    cursos_selecionados_ids = [row[0] for row in cursor.fetchall()]

    # Mapeamento de funcao_id para setor_id
    cursor.execute("SELECT id, setor_id FROM funcao")
    funcao_setor_map = {row[0]: row[1] for row in cursor.fetchall()}

    conn.close()
    return render_template("editar.html", trabalhador=trabalhador, setores=setores, vinculos=vinculos,
                           cursos_disponiveis=cursos_disponiveis,
                           cursos_selecionados_ids=cursos_selecionados_ids,
                           id_setor_ensino=ID_SETOR_ENSINO,
                           funcao_setor_map=funcao_setor_map)


@app.route('/atualizar/<int:trabalhador_id>', methods=['POST'])
@login_required
def atualizar(trabalhador_id):
    """
    Atualiza os dados de um trabalhador existente, seu endereço, vínculos e cursos de ensino.
    """
    conn = conectar()
    cursor = conn.cursor()

    nome = request.form.get("nome")
    cpf = request.form.get("cpf").replace('.', '').replace('-', '')
    if not validar_cpf(cpf):
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

    cursos_selecionados = request.form.getlist("cursos_ensino[]")


    try:
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

        cursor.execute("""
            UPDATE endereco SET cep=%s, rua=%s, numero=%s, bairro=%s, cidade=%s, estado=%s, complemento=%s
            WHERE trabalhador_id=%s
        """, (cep, rua, numero, bairro, cidade, estado, complemento, trabalhador_id))

        cursor.execute("DELETE FROM trabalhador_setor_funcao WHERE trabalhador_id=%s", (trabalhador_id,))
        for i in range(len(setores)):
            setor_id = setores[i]
            funcao_id = funcoes[i]
            turno = turnos[i]
            dias_da_semana_str = dias_da_semana_por_vinculo[i] if i < len(dias_da_semana_por_vinculo) else ""

            cursor.execute("""
                INSERT INTO trabalhador_setor_funcao (trabalhador_id, setor_id, funcao_id, turno, dias_da_semana)
                VALUES (%s, %s, %s, %s, %s)
            """, (trabalhador_id, setor_id, funcao_id, turno, dias_da_semana_str))
        
        # Excluir e reinserir cursos de ensino para o trabalhador
        cursor.execute("DELETE FROM trabalhador_curso_ensino WHERE trabalhador_id = %s", (trabalhador_id,))
        for curso_id in cursos_selecionados:
            cursor.execute("""
                INSERT INTO trabalhador_curso_ensino (trabalhador_id, curso_id)
                VALUES (%s, %s)
            """, (trabalhador_id, curso_id))


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
@login_required
def deletar_trabalhador(trabalhador_id):
    """
    Exclui um trabalhador e todos os seus dados relacionados (endereço e vínculos) do banco de dados.
    """
    conn = conectar()
    cursor = conn.cursor()
    try:
        # NOVO: Remover vínculos de cursos de ensino
        cursor.execute("DELETE FROM trabalhador_curso_ensino WHERE trabalhador_id = %s", (trabalhador_id,))
        
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
@login_required
def relatorios():
    """Renderiza a página de relatórios."""
    return render_template("relatorios.html")

@app.route('/api/relatorios')
@login_required
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
        # NOVO: Buscar cursos para cada trabalhador no relatório
        cursor.execute("""
            SELECT ce.nome
            FROM trabalhador_curso_ensino tce
            JOIN cursos_ensino ce ON tce.curso_id = ce.id
            WHERE tce.trabalhador_id = %s
        """, (row[0],))
        cursos_trabalhador = [c[0] for c in cursor.fetchall()]

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
            "email": row[17],
            "cursos_ensino": cursos_trabalhador # NOVO: Adiciona os cursos
        })

    conn.close()
    return jsonify(lista)

@app.route('/api/setores_para_filtro', methods=['GET'])
@login_required
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


# --- ROTAS PARA GERENCIAMENTO DE SETORES E FUNÇÕES ---

@app.route('/gerenciar_estrutura')
@login_required
def gerenciar_estrutura():
    conn = conectar()
    cursor = conn.cursor()

    # Buscar setores
    cursor.execute("SELECT id, nome FROM setores ORDER BY nome")
    setores = cursor.fetchall()

    # Buscar funções com seus setores
    cursor.execute("""
        SELECT f.id, f.nome, s.nome as setor_nome, f.setor_id
        FROM funcao f
        LEFT JOIN setores s ON f.setor_id = s.id
        ORDER BY s.nome, f.nome
    """)
    funcoes = cursor.fetchall()

    conn.close()
    return render_template('gerenciar_estrutura.html', setores=setores, funcoes=funcoes)

@app.route('/setor/adicionar', methods=['POST'])
@login_required
def adicionar_setor():
    nome = request.form.get('nome')
    if not nome:
        flash("O nome do setor não pode ser vazio.", "danger")
        return redirect(url_for('gerenciar_estrutura'))

    # Normaliza o nome para minúsculas e remove espaços extras
    nome_normalizado = nome.strip().lower()

    conn = conectar()
    cursor = conn.cursor()
    try:
        # Use nome_normalizado na inserção
        cursor.execute("INSERT INTO setores (nome) VALUES (%s)", (nome_normalizado,))
        conn.commit()
        flash(f"Setor '{nome}' adicionado com sucesso!", "success") # Mostra o nome original na flash
    except psycopg2.errors.UniqueViolation: # Se o nome do setor for UNIQUE
        conn.rollback()
        flash(f"O setor '{nome}' já existe.", "warning")
    except Exception as e:
        conn.rollback()
        flash(f"Erro ao adicionar setor: {str(e)}", "danger")
    finally:
        conn.close()
    return redirect(url_for('gerenciar_estrutura'))

@app.route('/setor/editar/<int:setor_id>', methods=['POST'])
@login_required
def editar_setor(setor_id):
    novo_nome = request.form.get('nome')
    if not novo_nome:
        flash("O nome do setor não pode ser vazio.", "danger")
        return redirect(url_for('gerenciar_estrutura'))

    # Normaliza o nome para minúsculas e remove espaços extras
    novo_nome_normalizado = novo_nome.strip().lower()

    conn = conectar()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE setores SET nome = %s WHERE id = %s", (novo_nome_normalizado, setor_id))
        conn.commit()
        if cursor.rowcount == 0:
            flash("Setor não encontrado.", "danger")
        else:
            flash(f"Setor atualizado para '{novo_nome}' com sucesso!", "success")
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        flash(f"O setor '{novo_nome}' já existe.", "warning")
    except Exception as e:
        conn.rollback()
        flash(f"Erro ao editar setor: {str(e)}", "danger")
    finally:
        conn.close()
    return redirect(url_for('gerenciar_estrutura'))

@app.route('/setor/deletar/<int:setor_id>', methods=['POST'])
@login_required
def deletar_setor(setor_id):
    conn = conectar()
    cursor = conn.cursor()
    try:
        # Primeiro, remover vínculos de trabalhador com funções neste setor
        cursor.execute("""
            DELETE FROM trabalhador_setor_funcao
            WHERE setor_id = %s
        """, (setor_id,))

        # NOVO: Remover vínculos de cursos de ensino para trabalhadores que tinham funções neste setor
        cursor.execute("""
            DELETE FROM trabalhador_curso_ensino
            WHERE trabalhador_id IN (
                SELECT t.id FROM trabalhador t
                JOIN trabalhador_setor_funcao tsf ON t.id = tsf.trabalhador_id
                WHERE tsf.setor_id = %s
            )
        """, (setor_id,))

        # Depois, remover funções associadas a este setor
        cursor.execute("DELETE FROM funcao WHERE setor_id = %s", (setor_id,))

        # Finalmente, remover o setor
        cursor.execute("DELETE FROM setores WHERE id = %s", (setor_id,))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({"success": False, "message": "Setor não encontrado."}), 404
        flash("Setor e suas funções/vínculos excluídos com sucesso!", "success")
        return jsonify({"success": True, "message": "Setor excluído com sucesso!"}), 200
    except Exception as e:
        conn.rollback()
        print(f"Erro ao excluir setor: {e}")
        return jsonify({"success": False, "message": f"Erro ao excluir setor: {str(e)}"}), 500
    finally:
        conn.close()

@app.route('/funcao/adicionar', methods=['POST'])
@login_required
def adicionar_funcao():
    nome = request.form.get('nome')
    setor_id = request.form.get('setor_id')

    if not nome or not setor_id:
        flash("Nome da função e setor são obrigatórios.", "danger")
        return redirect(url_for('gerenciar_estrutura'))

    # Normaliza o nome da função
    nome_normalizado = nome.strip().lower()

    conn = conectar()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO funcao (nome, setor_id) VALUES (%s, %s)", (nome_normalizado, setor_id))
        conn.commit()
        flash(f"Função '{nome}' adicionada com sucesso!", "success")
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        flash(f"A função '{nome}' já existe neste setor.", "warning")
    except Exception as e:
        conn.rollback()
        flash(f"Erro ao adicionar função: {str(e)}", "danger")
    finally:
        conn.close()
    return redirect(url_for('gerenciar_estrutura'))

@app.route('/funcao/editar/<int:funcao_id>', methods=['POST'])
@login_required
def editar_funcao(funcao_id):
    novo_nome = request.form.get('nome')
    novo_setor_id = request.form.get('setor_id')

    if not novo_nome or not novo_setor_id:
        flash("Nome da função e setor são obrigatórios.", "danger")
        return redirect(url_for('gerenciar_estrutura'))

    # Normaliza o nome da função
    novo_nome_normalizado = novo_nome.strip().lower()

    conn = conectar()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE funcao SET nome = %s, setor_id = %s WHERE id = %s", (novo_nome_normalizado, novo_setor_id, funcao_id))
        conn.commit()
        if cursor.rowcount == 0:
            flash("Função não encontrada.", "danger")
        else:
            flash(f"Função atualizada para '{novo_nome}' com sucesso!", "success")
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        flash(f"A função '{novo_nome}' já existe neste setor.", "warning")
    except Exception as e:
        conn.rollback()
        flash(f"Erro ao editar função: {str(e)}", "danger")
    finally:
        conn.close()
    return redirect(url_for('gerenciar_estrutura'))

@app.route('/funcao/deletar/<int:funcao_id>', methods=['POST'])
@login_required
def deletar_funcao(funcao_id):
    conn = conectar()
    cursor = conn.cursor()
    try:
        # Remover vínculos de trabalhador com esta função
        cursor.execute("DELETE FROM trabalhador_setor_funcao WHERE funcao_id = %s", (funcao_id,))

        # NOVO: Remover vínculos de cursos de ensino para trabalhadores que tinham esta função
        cursor.execute("""
            DELETE FROM trabalhador_curso_ensino
            WHERE trabalhador_id IN (
                SELECT t.id FROM trabalhador t
                JOIN trabalhador_setor_funcao tsf ON t.id = tsf.trabalhador_id
                WHERE tsf.funcao_id = %s
            )
        """, (funcao_id,))
        
        # Remover a função
        cursor.execute("DELETE FROM funcao WHERE id = %s", (funcao_id,))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({"success": False, "message": "Função não encontrada."}), 404
        flash("Função e seus vínculos excluídos com sucesso!", "success")
        return jsonify({"success": True, "message": "Função excluída com sucesso!"}), 200
    except Exception as e:
        conn.rollback()
        print(f"Erro ao excluir função: {e}")
        return jsonify({"success": False, "message": f"Erro ao excluir função: {str(e)}"}), 500
    finally:
        conn.close()

@app.route('/esqueci_senha', methods=['GET', 'POST'])
def esqueci_senha():
    if request.method == 'POST':
        email = request.form.get('email')

        conn = conectar()
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome FROM trabalhador WHERE email = %s", (email,))
        user = cursor.fetchone()
        conn.close()

        if user:
            token = str(uuid.uuid4())
            reset_link = url_for('resetar_senha', token=token, _external=True)

            # Salvar o token temporariamente (em produção use tabela ou Redis)
            with open(f'tokens/{token}.txt', 'w') as f:
                f.write(str(user[0]))

            enviar_email_confirmacao(
                email,
                user[1],
                assunto='Redefinição de Senha',
                corpo=f"""
                <p>Olá {user[1]},</p>
                <p>Recebemos uma solicitação para redefinir sua senha.</p>
                <p>Clique <a href='{reset_link}'>aqui</a> para criar uma nova senha.</p>
                <p>Se você não solicitou, ignore este e-mail.</p>
                """
            )
            flash("E-mail de recuperação enviado com sucesso!", "success")
        else:
            flash("Email não encontrado.", "danger")

    return render_template('esqueci_senha.html')

@app.route('/resetar_senha/<token>', methods=['GET', 'POST'])
def resetar_senha(token):
    try:
        with open(f'tokens/{token}.txt') as f:
            trabalhador_id = f.read().strip()
    except:
        flash("Token inválido ou expirado.", "danger")
        return redirect(url_for('login'))

    if request.method == 'POST':
        nova_senha = request.form.get("nova_senha")
        hashed = generate_password_hash(nova_senha)
        conn = conectar()
        cursor = conn.cursor()
        cursor.execute("UPDATE trabalhador SET senha_hash = %s WHERE id = %s", (hashed, trabalhador_id))
        conn.commit()
        conn.close()
        os.remove(f'tokens/{token}.txt')
        flash("Senha redefinida com sucesso!", "success")
        return redirect(url_for('login'))

    return render_template('resetar_senha.html')

if __name__ == '__main__':
    app.run(debug=True)

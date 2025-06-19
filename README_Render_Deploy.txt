
📦 DEPLOY NO RENDER.COM – APLICATIVO FLASK + MYSQL

1. Faça login em https://render.com
2. Clique em "New Web Service"
3. Conecte seu repositório GitHub com o projeto
4. Configure:
   - Nome: centro-espirita-app
   - Runtime: Python 3
   - Build Command: pip install -r requirements.txt
   - Start Command: gunicorn app_env:app

5. Adicione as variáveis de ambiente:
   - DB_HOST=xxxxxxxxxxxx
   - DB_USER=seu_usuario
   - DB_PASSWORD=sua_senha
   - DB_NAME=centro_espirita

✅ Teste local: `python app_env.py`


import psycopg2

def conectar():
    return psycopg2.connect(
        host="localhost",
        dbname="seubanco",
        user="seuusuario",
        password="suasenha"
    )

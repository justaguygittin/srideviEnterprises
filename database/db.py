import mysql.connector

def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="YOUR_DB_USER",
        password="YOUR_DB_PASSWORD",
        database="gsrikari_Sridevi_Enterprises"
    )
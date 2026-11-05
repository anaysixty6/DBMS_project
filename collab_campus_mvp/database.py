import mysql.connector

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Anay@144",  # Change this
        database="collab_campus",
        autocommit=True
    )

# config.py - Configuración para servidor MySQL remoto
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-cambiar'
    DB_USER = os.environ.get('DB_USER')
    DB_PASSWORD = os.environ.get('DB_PASSWORD')
    DB_HOST = os.environ.get('DB_HOST')
    DB_NAME = os.environ.get('DB_NAME')

    # Configuración para conectar a MySQL del servidor
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://ejemplo:ejemplo@ejemplo:3306/manuales'
    # Conexión directa con usuario y contraseña proporcionados
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = 'uploads'
    ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt'}
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

    # Email settings para notificaciones
    MAIL_SERVER = 'localhost'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', 'raul.lopez@mundosol.com')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', 'tu-password')
    IT_EMAIL = os.environ.get('IT_EMAIL', 'it@empresa.com')

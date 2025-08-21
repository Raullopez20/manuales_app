import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app, session, redirect, url_for, flash
from functools import wraps

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def send_notification_email(manual):
    try:
        msg = MIMEMultipart()
        msg['From'] = current_app.config['MAIL_USERNAME']
        msg['To'] = current_app.config['IT_EMAIL']
        msg['Subject'] = f'Nuevo manual subido: {manual.titulo}'
        
        body = f'''
        Se ha subido un nuevo manual al sistema:
        
        Título: {manual.titulo}
        Descripción: {manual.descripcion}
        Categoría: {manual.categoria.nombre if manual.categoria else 'Sin categoría'}
        Archivo: {manual.archivo}
        
        Saludos,
        Sistema de Manuales
        '''
        
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(current_app.config['MAIL_SERVER'], current_app.config['MAIL_PORT'])
        server.starttls()
        server.login(current_app.config['MAIL_USERNAME'], current_app.config['MAIL_PASSWORD'])
        text = msg.as_string()
        server.sendmail(current_app.config['MAIL_USERNAME'], current_app.config['IT_EMAIL'], text)
        server.quit()
        
        print("Email de notificación enviado")
    except Exception as e:
        print(f"Error enviando email: {e}")

def login_required(f):
    """Decorador para proteger rutas que requieren autenticación."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debes iniciar sesión para acceder a esta página.', 'error')
            return redirect(url_for('main.login'))
        return f(*args, **kwargs)
    return decorated_function

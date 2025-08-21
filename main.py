from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os
from datetime import datetime
from sqlalchemy import text

# Importar modelos y formularios
from app.models import db, Manual, Categoria, AuditoriaDescarga, Usuario
from app.routes import main

def create_app(config_name='development'):
    """Factory function para crear la aplicación Flask"""
    app = Flask(__name__)

    # Configuración de la aplicación
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

    # Configuración de la base de datos
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or \
        'mysql+pymysql://ejemplo:ejemplo@ejemplo:3306/manuales'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Configuración de archivos
    app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'uploads')
    app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB máximo

    # Crear directorio de uploads si no existe
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Inicializar extensiones
    db.init_app(app)
    migrate = Migrate(app, db)

    # Registrar blueprints
    app.register_blueprint(main)

    # Manejadores de errores globales
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    @app.errorhandler(413)
    def too_large(error):
        return render_template('errors/413.html'), 413

    # Context processors para hacer variables disponibles en templates
    @app.context_processor
    def inject_now():
        return {'now': datetime.utcnow}

    @app.context_processor
    def inject_categories():
        """Inyecta categorías en todos los templates"""
        from flask import session
        # Solo inyectar categorías si hay un usuario logueado
        if 'user_id' not in session:
            return {'all_categories': []}
        
        user_id = session.get('user_id')
        usuario = Usuario.query.get(user_id)
        is_admin = usuario and getattr(usuario, 'is_admin', False)
        
        if is_admin:
            return {'all_categories': Categoria.query.filter_by(activa=True).all()}
        else:
            return {'all_categories': Categoria.query.filter_by(activa=True, usuario_id=user_id).all()}

    # Comandos CLI personalizados
    @app.cli.command()
    def init_db():
        """Inicializa la base de datos con datos de ejemplo"""
        print("Creando tablas...")
        db.create_all()

        # Crear categorías de ejemplo
        categorias_ejemplo = [
            {'nombre': 'Manuales de Usuario', 'descripcion': 'Documentación para usuarios finales'},
            {'nombre': 'Procedimientos', 'descripcion': 'Procedimientos operativos estándar'},
            {'nombre': 'Documentación Técnica', 'descripcion': 'Documentación para desarrolladores y técnicos'},
            {'nombre': 'Políticas', 'descripcion': 'Políticas corporativas y normas'},
            {'nombre': 'Capacitación', 'descripcion': 'Material de formación y capacitación'},
        ]

        for cat_data in categorias_ejemplo:
            categoria = Categoria.query.filter_by(nombre=cat_data['nombre']).first()
            if not categoria:
                categoria = Categoria(**cat_data)
                db.session.add(categoria)
                print(f"Categoría creada: {cat_data['nombre']}")

        try:
            db.session.commit()
            print("Base de datos inicializada correctamente!")
        except Exception as e:
            db.session.rollback()
            print(f"Error al inicializar la base de datos: {str(e)}")

    @app.cli.command()
    def reset_db():
        """Reinicia la base de datos (CUIDADO: elimina todos los datos)"""
        if input("¿Estás seguro de que quieres eliminar todos los datos? (sí/no): ").lower() == 'sí':
            print("Eliminando tablas...")
            db.drop_all()
            print("Creando tablas...")
            db.create_all()
            print("Base de datos reiniciada!")
        else:
            print("Operación cancelada.")

    @app.cli.command()
    def create_admin():
        """Crea un usuario administrador (para futuras implementaciones)"""
        # Placeholder para cuando se implemente autenticación
        print("Funcionalidad de administrador pendiente de implementar")

    # Filtros personalizados para Jinja2
    @app.template_filter('filesizeformat')
    def filesizeformat(value):
        """Convierte bytes a formato legible"""
        if not value:
            return 'Desconocido'

        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if value < 1024.0:
                return f"{value:.1f} {unit}"
            value /= 1024.0
        return f"{value:.1f} PB"

    @app.template_filter('timeago')
    def timeago(value):
        """Muestra tiempo transcurrido de forma legible"""
        if not value:
            return 'Desconocido'

        now = datetime.utcnow()
        diff = now - value

        if diff.days > 0:
            if diff.days == 1:
                return 'hace 1 día'
            elif diff.days < 30:
                return f'hace {diff.days} días'
            elif diff.days < 365:
                months = diff.days // 30
                return f'hace {months} mes{"es" if months > 1 else ""}'
            else:
                years = diff.days // 365
                return f'hace {years} año{"s" if years > 1 else ""}'

        seconds = diff.seconds
        if seconds < 60:
            return 'hace unos segundos'
        elif seconds < 3600:
            minutes = seconds // 60
            return f'hace {minutes} minuto{"s" if minutes > 1 else ""}'
        else:
            hours = seconds // 3600
            return f'hace {hours} hora{"s" if hours > 1 else ""}'

    return app

# Función de configuración para diferentes entornos
class Config:
    """Configuración base"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB

class DevelopmentConfig(Config):
    """Configuración para desarrollo"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
                              'sqlite:///sistema_manuales_dev.db'

class ProductionConfig(Config):
    """Configuración para producción"""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
                              'sqlite:///sistema_manuales.db'

class TestingConfig(Config):
    """Configuración para testing"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

# Diccionario de configuraciones
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

# Asegurar que la aplicación esté expuesta correctamente
if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
else:
    app = create_app()

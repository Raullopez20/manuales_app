from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.utils import secure_filename
import os

db = SQLAlchemy()

class Categoria(db.Model):
    """Modelo para categorías de documentos"""
    __tablename__ = 'categoria'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False, unique=True)
    descripcion = db.Column(db.Text, nullable=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    activa = db.Column(db.Boolean, default=True, nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)  # Nuevo: dueño de la categoría

    # Relación con manuales
    manuales = db.relationship('Manual', backref='categoria', lazy=True)
    usuario = db.relationship('Usuario', backref='categorias', lazy=True)

    def __repr__(self):
        return f'<Categoria {self.nombre}>'

    def to_dict(self):
        """Convierte el objeto a diccionario"""
        return {
            'id': self.id,
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'fecha_creacion': self.fecha_creacion.isoformat(),
            'usuario_id': self.usuario_id,
            'documentos_count': len([m for m in self.manuales if m.activo])  # Contar solo documentos activos
        }

class Usuario(db.Model):
    """Modelo para usuarios"""
    __tablename__ = 'usuario'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=False)  # Contraseña encriptada
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    is_admin = db.Column(db.Boolean, default=False, nullable=False)  # Nuevo campo para distinguir administradores

    # Relación con documentos
    documentos = db.relationship('Manual', backref='usuario', lazy=True)

    def __repr__(self):
        return f'<Usuario {self.username}>'

class Manual(db.Model):
    """Modelo para manuales y documentos"""
    __tablename__ = 'manual'

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    archivo = db.Column(db.String(255), nullable=False)
    tipo_archivo = db.Column(db.String(20), nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    activo = db.Column(db.Boolean, default=True, nullable=False)
    descargas = db.Column(db.Integer, default=0, nullable=False)
    # Clave foránea
    categoria_id = db.Column(db.Integer, db.ForeignKey('categoria.id'), nullable=True)
    subido_por_id = db.Column(db.Integer, nullable=True)
    archivo_original = db.Column(db.String(255), nullable=True)  # Nuevo campo para el nombre original del archivo
    tamaño_archivo = db.Column(db.Integer, nullable=True)  # Nuevo campo para el tamaño del archivo en bytes
    fecha_actualizacion = db.Column(db.DateTime, nullable=True)  # Nuevo campo para la fecha de actualización
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)  # Nueva clave foránea

    def __repr__(self):
        return f'<Manual {self.titulo}>'

    def to_dict(self):
        """Convierte el objeto a diccionario"""
        return {
            'id': self.id,
            'titulo': self.titulo,
            'descripcion': self.descripcion,
            'archivo': self.archivo,
            'tipo_archivo': self.tipo_archivo,
            'fecha_creacion': self.fecha_creacion.isoformat(),
            'categoria_id': self.categoria_id,
            'subido_por_id': self.subido_por_id,
            'archivo_original': self.archivo_original,
            'tamaño_archivo': self.tamaño_archivo,
            'fecha_actualizacion': self.fecha_actualizacion.isoformat() if self.fecha_actualizacion else None,
            'usuario_id': self.usuario_id
        }

    def incrementar_descargas(self):
        """Incrementa el contador de descargas del manual."""
        self.descargas += 1
        self.fecha_actualizacion = datetime.utcnow()

class AuditoriaDescarga(db.Model):
    """Modelo para auditoría de descargas"""
    __tablename__ = 'auditoria_descarga'

    id = db.Column(db.Integer, primary_key=True)
    manual_id = db.Column(db.Integer, db.ForeignKey('manual.id', ondelete='CASCADE'), nullable=False)
    ip_usuario = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(500), nullable=True)
    fecha_descarga = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f'<AuditoriaDescarga {self.id}>'

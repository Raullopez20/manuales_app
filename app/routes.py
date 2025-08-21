from flask import Blueprint, render_template, request, flash, redirect, url_for, send_from_directory, jsonify, abort, current_app, send_file, session
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import mimetypes
from .models import Manual, Categoria, AuditoriaDescarga, db, Usuario
from .forms import UploadForm, SearchForm, CategoryForm, EditDocumentForm, EditCategoryForm
from math import ceil
import glob
import subprocess
import shutil
from .utils import login_required
from time import time
from functools import wraps
from flask import send_file
import zipfile

main = Blueprint('main', __name__)

# Configuración de archivos permitidos
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

def allowed_file(filename):
    """Verifica si el archivo tiene una extensión permitida"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_size(file):
    """Obtiene el tamaño del archivo"""
    file.seek(0, 2)  # Ir al final del archivo
    size = file.tell()
    file.seek(0)  # Volver al inicio
    return size

def save_file(file, upload_folder):
    """Guarda un archivo de forma segura"""
    if file and allowed_file(file.filename):
        # Generar nombre único para evitar conflictos
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = secure_filename(file.filename)
        name, ext = os.path.splitext(filename)
        unique_filename = f"{timestamp}_{name}{ext}"

        filepath = os.path.join(upload_folder, unique_filename)
        file.save(filepath)

        return unique_filename, file.filename, get_file_size(file)
    return None, None, None

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            return redirect(url_for('main.login'))
        from .models import Usuario
        usuario = Usuario.query.get(session['user_id'])
        if not usuario or not usuario.is_admin:
            flash('Acceso solo para administradores.', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

@main.route('/')
def index():
    """Página principal con dashboard"""
    if 'user_id' not in session:
        print('[INDEX] user_id no está en session')
        return redirect(url_for('main.login'))

    try:
        search_form = SearchForm()
        user_id = session.get('user_id')
        username = session.get('username')
        print(f'[INDEX] user_id en session: {user_id}, username: {username}')
        usuario = Usuario.query.get(user_id)
        print(f'[INDEX] usuario encontrado en DB: {usuario}')

        if not usuario:
            session.clear()
            flash('Usuario no encontrado. Inicia sesión nuevamente.', 'error')
            return redirect(url_for('main.login'))

        is_admin = getattr(usuario, 'is_admin', False)

        # Cargar categorías de forma segura
        try:
            if is_admin:
                categorias_activas = Categoria.query.filter_by(activa=True).order_by(Categoria.nombre).all()
            else:
                categorias_activas = Categoria.query.filter_by(activa=True, usuario_id=user_id).order_by(Categoria.nombre).all()
        except Exception as e:
            print(f"Error al cargar categorías: {e}")
            categorias_activas = []

        # Configurar formulario de búsqueda de forma segura
        search_form.categoria_id.choices = [(0, 'Todas las categorías')] + [(c.id, c.nombre) for c in categorias_activas]

        # Obtener documentos de forma segura
        try:
            if is_admin:
                manuales = Manual.query.filter_by(activo=True).order_by(Manual.fecha_creacion.desc()).limit(10).all()
                stats = {
                    'total_documentos': Manual.query.filter_by(activo=True).count(),
                    'total_categorias': Categoria.query.filter_by(activa=True).count()
                }
            else:
                manuales = Manual.query.filter_by(activo=True, usuario_id=user_id).order_by(Manual.fecha_creacion.desc()).limit(10).all()
                stats = {
                    'total_documentos': Manual.query.filter_by(activo=True, usuario_id=user_id).count(),
                    'total_categorias': len(categorias_activas)
                }
        except Exception as e:
            print(f"Error al cargar manuales: {e}")
            manuales = []
            stats = {'total_documentos': 0, 'total_categorias': 0}

        # Obtener categorías para la sección de explorar
        try:
            if is_admin:
                categorias = Categoria.query.filter_by(activa=True).order_by(Categoria.nombre).all()
            else:
                categorias = Categoria.query.filter_by(activa=True, usuario_id=user_id).order_by(Categoria.nombre).all()
        except Exception as e:
            print(f"Error al cargar categorías para explorar: {e}")
            categorias = []

        return render_template('index.html',
                             search_form=search_form,
                             categorias=categorias,
                             stats=stats,
                             manuales=manuales,
                             is_admin=is_admin)

    except Exception as e:
        print(f"Error general en index: {e}")
        # Si hay cualquier error, redirigir al login
        session.clear()
        flash('Ha ocurrido un error. Inicia sesión nuevamente.', 'error')
        return redirect(url_for('main.login'))

@main.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    """Subir múltiples documentos"""
    # Filtrar categorías solo del usuario actual ANTES de crear el formulario
    user_id = session.get('user_id')
    categorias = Categoria.query.filter_by(activa=True, usuario_id=user_id).all()

    # Crear el formulario DESPUÉS de obtener las categorías
    form = UploadForm()
    # Establecer las opciones filtradas
    form.categoria_id.choices = [(c.id, c.nombre) for c in categorias]

    # También filtrar all_categories para el usuario actual
    all_categories = Categoria.query.filter_by(usuario_id=user_id).all()

    if not categorias:
        flash('Debe crear al menos una categoría antes de subir documentos.', 'error')
        return redirect(url_for('main.crear_categoria'))

    if form.validate_on_submit():
        # Validación adicional: verificar que la categoría seleccionada pertenece al usuario
        categoria_seleccionada = Categoria.query.filter_by(
            id=form.categoria_id.data,
            usuario_id=user_id,
            activa=True
        ).first()

        if not categoria_seleccionada:
            flash('La categoría seleccionada no es válida.', 'error')
            return render_template('upload.html', form=form, year=datetime.now().year, all_categories=all_categories)

        archivos = request.files.getlist('archivos')
        if not archivos or all(not archivo.filename for archivo in archivos):
            flash('Debe seleccionar al menos un archivo.', 'error')
            return render_template('upload.html', form=form, year=datetime.now().year, all_categories=all_categories)

        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)

        archivos_subidos = []
        errores = []

        for archivo in archivos:
            if archivo.filename:
                file_size = archivo.seek(0, 2) or archivo.tell()
                archivo.seek(0)
                if file_size > MAX_FILE_SIZE:
                    errores.append(f'{archivo.filename}: Archivo demasiado grande (máximo 50MB)')
                    continue
                if not allowed_file(archivo.filename):
                    errores.append(f'{archivo.filename}: Tipo de archivo no permitido')
                    continue
                unique_filename, original_filename, size = save_file(archivo, upload_folder)
                if unique_filename:
                    manual = Manual(
                        titulo=form.titulo.data,
                        descripcion=form.descripcion.data,
                        archivo=unique_filename,
                        archivo_original=original_filename,
                        tamaño_archivo=size,
                        tipo_archivo=original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else '',
                        categoria_id=form.categoria_id.data,
                        usuario_id=session.get('user_id')  # Asocia el manual al usuario logueado
                    )
                    db.session.add(manual)
                    archivos_subidos.append(original_filename)
                else:
                    errores.append(f'{archivo.filename}: Error al guardar el archivo')
        if archivos_subidos:
            try:
                db.session.commit()
                flash(f'{len(archivos_subidos)} documento(s) subido(s) exitosamente.', 'success')
            except Exception as e:
                db.session.rollback()
                flash('Error al guardar en la base de datos.', 'error')
                current_app.logger.error(f'Error al subir archivos: {str(e)}')
        for error in errores:
            flash(error, 'error')
        return redirect(url_for('main.upload'))

    return render_template('upload.html', form=form, year=datetime.now().year, all_categories=all_categories)

@main.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    """Búsqueda avanzada de documentos con paginación"""
    form = SearchForm()
    # Filtrar categorías solo del usuario actual
    user_id = session.get('user_id')
    usuario = Usuario.query.get(user_id)
    is_admin = usuario and getattr(usuario, 'is_admin', False)

    if is_admin:
        categorias = Categoria.query.filter_by(activa=True).all()
    else:
        categorias = Categoria.query.filter_by(activa=True, usuario_id=user_id).all()

    form.categoria_id.choices = [(0, 'Todas las categorías')] + [(c.id, c.nombre) for c in categorias]

    page = request.args.get('page', 1, type=int)
    per_page = 9  # Número de resultados por página

    # Obtener parámetros tanto de GET como de POST
    if request.method == 'POST' and form.validate_on_submit():
        termino = form.termino.data.strip() if form.termino.data else None
        categoria_id = form.categoria_id.data if form.categoria_id.data != 0 else None
        tipo_archivo = form.tipo_archivo.data if form.tipo_archivo.data != 0 else None
        date_from = request.form.get('date_from')
        date_to = request.form.get('date_to')
    else:
        termino = request.args.get('termino', '').strip() or None
        categoria_id = int(request.args.get('categoria_id', 0)) or None
        if categoria_id == 0:
            categoria_id = None
        tipo_archivo = request.args.get('file_type') or None
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')

    if is_admin:
        query = Manual.query.filter_by(activo=True)
    else:
        query = Manual.query.filter_by(activo=True, usuario_id=session.get('user_id'))

    if termino:
        query = query.filter(
            Manual.titulo.ilike(f'%{termino}%') |
            Manual.descripcion.ilike(f'%{termino}%') |
            Manual.archivo.ilike(f'%{termino}%')
        )
    if categoria_id:
        query = query.filter(Manual.categoria_id == categoria_id)
    if tipo_archivo:
        query = query.filter(Manual.tipo_archivo.in_(tipo_archivo.split(',')))
    if date_from:
        try:
            date_from_dt = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(Manual.fecha_creacion >= date_from_dt)
        except Exception:
            pass
    if date_to:
        try:
            date_to_dt = datetime.strptime(date_to, '%Y-%m-%d')
            query = query.filter(Manual.fecha_creacion <= date_to_dt)
        except Exception:
            pass

    query = query.order_by(Manual.fecha_creacion.desc())
    manuales = query.all()
    total_documentos = len(manuales)
    total_pages = 1
    pagination = None

    return render_template('search.html', 
                         form=form, 
                         manuales=manuales, 
                         categorias=categorias,  # Pasar las categorías filtradas al template
                         year=datetime.now().year, 
                         pagination=pagination, 
                         total_pages=total_pages, 
                         current_page=1, 
                         is_admin=is_admin, 
                         total_documentos=total_documentos)

@main.route('/crear_categoria', methods=['GET', 'POST'])
@login_required
def crear_categoria():
    """Crear nueva categoría"""
    form = CategoryForm()
    usuario = Usuario.query.get(session.get('user_id'))
    is_admin = usuario.is_admin if usuario else False

    if form.validate_on_submit():
        # Verificar si ya existe una categoría con el mismo nombre para este usuario
        categoria_existente = Categoria.query.filter_by(nombre=form.nombre.data, usuario_id=usuario.id).first()

        if categoria_existente:
            flash('Ya existe una categoría con ese nombre para tu usuario.', 'error')
        else:
            categoria = Categoria(
                nombre=form.nombre.data,
                descripcion=form.descripcion.data if form.descripcion.data else None,
                usuario_id=usuario.id
            )
            try:
                db.session.add(categoria)
                db.session.commit()
                flash(f'Categoría "{categoria.nombre}" creada exitosamente.', 'success')
                return redirect(url_for('main.crear_categoria'))
            except Exception as e:
                db.session.rollback()
                flash('Error al crear la categoría.', 'error')
                current_app.logger.error(f'Error al crear categoría: {str(e)}')

    # Mostrar solo las categorías del usuario o todas si es admin
    if is_admin:
        all_categories = Categoria.query.order_by(Categoria.fecha_creacion.desc()).all()
    else:
        all_categories = Categoria.query.filter_by(usuario_id=usuario.id).order_by(Categoria.fecha_creacion.desc()).all()

    # Añadir total de manuales a cada categoría
    for cat in all_categories:
        cat.total_manuales = Manual.query.filter_by(categoria_id=cat.id).count()

    return render_template('crear_categoria.html', form=form, year=datetime.now().year, all_categories=all_categories, is_admin=is_admin)

@main.route('/download/<filename>')
@login_required
def download(filename):
    """Descargar archivo con auditoría"""
    # Buscar el manual por nombre de archivo y usuario
    manual = Manual.query.filter_by(archivo=filename, activo=True, usuario_id=session.get('user_id')).first()

    if not manual:
        abort(404)

    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    filepath = os.path.join(upload_folder, filename)

    if not os.path.exists(filepath):
        flash('El archivo no existe en el servidor.', 'error')
        abort(404)

    try:
        # Registrar descarga en auditoría
        auditoria = AuditoriaDescarga(
            manual_id=manual.id,
            ip_usuario=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')[:500]
        )
        db.session.add(auditoria)

        # Incrementar contador de descargas
        manual.incrementar_descargas()

        db.session.commit()  # Asegurar que los cambios se guarden en la base de datos

        # Verificar si el archivo existe antes de enviarlo
        if not os.path.isfile(filepath):
            flash('El archivo no existe en el servidor.', 'error')
            return redirect(request.referrer or url_for('main.index'))

        # Determinar tipo MIME
        mimetype = mimetypes.guess_type(filepath)[0]

        return send_from_directory(
            upload_folder,
            filename,
            as_attachment=True,
            download_name=manual.archivo_original,
            mimetype=mimetype
        )

    except Exception as e:
        flash(f'Error al descargar el archivo: {str(e)}', 'error')
        return redirect(request.referrer or url_for('main.index'))

@main.route('/api/categorias')
@login_required
def api_categorias():
    """API para obtener categorías (AJAX)"""
    user_id = session.get('user_id')
    usuario = Usuario.query.get(user_id)
    is_admin = usuario and getattr(usuario, 'is_admin', False)

    if is_admin:
        categorias = Categoria.query.filter_by(activa=True).all()
    else:
        categorias = Categoria.query.filter_by(activa=True, usuario_id=user_id).all()

    return jsonify([c.to_dict() for c in categorias])

@main.route('/api/documento/<int:manual_id>')
def api_documento(manual_id):
    """API para obtener información de un documento"""
    manual = Manual.query.filter_by(id=manual_id, activo=True).first()

    if not manual:
        return jsonify({'error': 'Documento no encontrado'}), 404

    return jsonify(manual.to_dict())

@main.route('/api/estadisticas')
def api_estadisticas():
    """API para obtener estadísticas del sistema"""
    stats = {
        'total_documentos': Manual.query.filter_by(activo=True).count(),
        'total_categorias': Categoria.query.filter_by(activa=True).count(),
        'total_descargas': db.session.query(db.func.sum(Manual.descargas)).scalar() or 0,
        'documentos_por_categoria': []
    }

    # Documentos por categoría
    categorias = db.session.query(
        Categoria.nombre,
        db.func.count(Manual.id).label('total')
    ).join(Manual).filter(
        Manual.activo == True,
        Categoria.activa == True
    ).group_by(Categoria.nombre).all()

    stats['documentos_por_categoria'] = [
        {'categoria': cat.nombre, 'total': cat.total}
        for cat in categorias
    ]

    return jsonify(stats)

@main.route('/api/manuales', methods=['GET'])
@login_required
def api_manuales():
    termino = request.args.get('termino', '').strip()
    categoria_id = request.args.get('categoria_id', type=int)
    tipo_archivo = request.args.get('file_type', '').strip()
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')

    user_id = session.get('user_id')
    usuario = Usuario.query.get(user_id)
    is_admin = usuario and getattr(usuario, 'is_admin', False)

    # Filtrar por usuario a menos que sea administrador
    if is_admin:
        query = Manual.query.filter_by(activo=True)
    else:
        query = Manual.query.filter_by(activo=True, usuario_id=user_id)

    if termino:
        query = query.filter(Manual.titulo.ilike(f'%{termino}%'))
    if categoria_id and categoria_id != 0:
        query = query.filter_by(categoria_id=categoria_id)
    if tipo_archivo:
        tipos = tipo_archivo.split(',')
        query = query.filter(Manual.tipo_archivo.in_(tipos))
    if date_from:
        query = query.filter(Manual.fecha_creacion >= date_from)
    if date_to:
        query = query.filter(Manual.fecha_creacion <= date_to)
    manuales = query.order_by(Manual.fecha_creacion.desc()).all()
    return jsonify([m.to_dict() for m in manuales])

@main.route('/api/pack_info/<int:pack_id>')
def api_pack_info(pack_id):
    pack = Pack.query.get_or_404(pack_id)
    return jsonify(pack.to_dict())

@main.route('/eliminar_categoria/<int:categoria_id>', methods=['POST'])
def eliminar_categoria(categoria_id):
    usuario = Usuario.query.get(session.get('user_id'))
    categoria = Categoria.query.get_or_404(categoria_id)
    # Permitir borrar si es admin o dueño de la categoría
    if not (usuario and (usuario.is_admin or getattr(categoria, 'usuario_id', None) == usuario.id)):
        flash('No tienes permisos para eliminar esta categoría.', 'error')
        return redirect(request.referrer or url_for('main.crear_categoria'))
    # Borrar todos los manuales asociados a la categoría
    manuales = Manual.query.filter_by(categoria_id=categoria.id).all()
    for manual in manuales:
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        archivo_path = os.path.join(upload_folder, manual.archivo)
        if os.path.exists(archivo_path):
            try:
                os.remove(archivo_path)
            except Exception:
                pass
        db.session.delete(manual)
    db.session.delete(categoria)
    try:
        db.session.commit()
        flash('Categoría y documentos eliminados correctamente.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error al eliminar la categoría.', 'error')
    return redirect(url_for('main.crear_categoria'))

@main.route('/eliminar_manual/<int:manual_id>', methods=['POST'])
def eliminar_manual(manual_id):
    usuario = Usuario.query.get(session.get('user_id'))
    manual = Manual.query.filter_by(id=manual_id).first_or_404()
    # Permitir borrar si es admin o dueño
    if not (usuario and (usuario.is_admin or manual.usuario_id == usuario.id)):
        flash('No tienes permisos para eliminar este manual.', 'error')
        return redirect(request.referrer or url_for('main.search'))
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    archivo_path = os.path.join(upload_folder, manual.archivo)
    if os.path.exists(archivo_path):
        try:
            os.remove(archivo_path)
        except Exception:
            pass
    db.session.delete(manual)
    try:
        db.session.commit()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Manual eliminado correctamente.'})
        flash('Manual eliminado correctamente.', 'success')
    except Exception as e:
        db.session.rollback()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Error al eliminar el manual.'}), 500
        flash('Error al eliminar el manual.', 'error')
    return redirect(request.referrer or url_for('main.search'))

@main.route('/historial')
@admin_required
def historial():
    manuales = Manual.query.filter_by(activo=True).order_by(Manual.fecha_creacion.desc()).all()
    # Recuento de usuarios que más han subido
    from sqlalchemy import func
    usuarios_ranking = (
        db.session.query(Usuario.username, func.count(Manual.id).label('total'))
        .join(Manual, Manual.usuario_id == Usuario.id)
        .filter(Manual.activo == True)
        .group_by(Usuario.id)
        .order_by(func.count(Manual.id).desc())
        .all()
    )
    return render_template('historial.html', manuales=manuales, year=datetime.now().year, usuarios_ranking=usuarios_ranking)

@main.route('/generar_backup', methods=['POST'])
@admin_required
def generar_backup():
    """Genera un backup manual de la base de datos y archivos subidos en un solo archivo ZIP"""
    import zipfile
    import sys
    import json
    BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'backups')
    UPLOADS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'uploads')
    DB_NAME = 'manuales'
    DB_USER = 'ejemplo'
    DB_PASSWORD = 'ejemplo'
    DB_HOST = 'ejemplo'
    CONFIG_FILES = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config.py'), os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'web.config')]
    DB_FILES = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'sistema_manuales.db'), os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'instance', 'manuales_local.db')]
    os.makedirs(BACKUP_DIR, exist_ok=True)
    fecha = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    backup_db_file = os.path.join(BACKUP_DIR, f'db_backup_{fecha}.sql')
    backup_zip_file = os.path.join(BACKUP_DIR, f'backup_completo_{fecha}.zip')
    try:
        from backup import export_mysql_db
        backup_result = export_mysql_db(DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, backup_db_file)
        if not backup_result or not os.path.exists(backup_db_file):
            flash(f'Error: El archivo de backup de la base de datos no se creó correctamente.', 'error')
            return redirect(url_for('main.historial'))
        with zipfile.ZipFile(backup_zip_file, 'w', zipfile.ZIP_DEFLATED) as backup_zip:
            # Bases de datos locales
            for db_file in DB_FILES:
                if os.path.exists(db_file):
                    backup_zip.write(db_file, arcname=os.path.join('db', os.path.basename(db_file)))
            # Archivos de configuración
            for config_file in CONFIG_FILES:
                if os.path.exists(config_file):
                    backup_zip.write(config_file, arcname=os.path.join('config', os.path.basename(config_file)))
            # Manuales por usuario
            from app.models import Usuario, Manual
            usuarios = Usuario.query.all()
            for usuario in usuarios:
                user_folder = os.path.join('manuales', usuario.username)
                manuales = Manual.query.filter_by(usuario_id=usuario.id).all()
                for manual in manuales:
                    file_path = os.path.join(UPLOADS_DIR, manual.archivo)
                    if os.path.exists(file_path):
                        arcname = os.path.join(user_folder, manual.archivo)
                        backup_zip.write(file_path, arcname)
                # Carpeta vacía si no tiene manuales
                if not manuales:
                    carpeta_usuario = os.path.join('manuales', usuario.username) + '/'
                    zinfo = zipfile.ZipInfo(carpeta_usuario)
                    backup_zip.writestr(zinfo, '')
            # Todos los archivos de uploads
            if os.path.exists(UPLOADS_DIR):
                for foldername, subfolders, filenames in os.walk(UPLOADS_DIR):
                    for filename in filenames:
                        filepath = os.path.join(foldername, filename)
                        arcname = os.path.join('uploads', os.path.relpath(filepath, start=UPLOADS_DIR))
                        backup_zip.write(filepath, arcname=arcname)
            # Metadatos
            metadata = {
                'fecha': fecha,
                'usuario': session.get('username', 'desconocido'),
                'version': '1.1',
                'archivos': {
                    'db': DB_FILES,
                    'uploads': UPLOADS_DIR,
                    'config': CONFIG_FILES
                }
            }
            backup_zip.writestr('metadata.json', json.dumps(metadata, indent=4))
            # info.txt
            info_lines = []
            info_lines.append(f"Backup generado correctamente el {fecha}")
            info_lines.append(f"Usuario que generó el backup: {session.get('username', 'desconocido')}")
            info_lines.append("")
            # Auditoría de archivos en uploads
            total_uploads = 0
            total_uploads_size = 0
            uploads_status = []
            if os.path.exists(UPLOADS_DIR):
                for foldername, subfolders, filenames in os.walk(UPLOADS_DIR):
                    for filename in filenames:
                        filepath = os.path.join(foldername, filename)
                        total_uploads += 1
                        try:
                            size = os.path.getsize(filepath)
                            total_uploads_size += size
                            uploads_status.append(f"[OK] {filename} ({size} bytes)")
                        except Exception as e:
                            uploads_status.append(f"[ERROR] {filename}: {e}")
            info_lines.append(f"Archivos en uploads: {total_uploads}")
            info_lines.append(f"Tamaño total uploads: {total_uploads_size} bytes ({round(total_uploads_size/1024/1024,2)} MB)")
            info_lines.append("")
            info_lines.append("Estado de archivos en uploads:")
            info_lines.extend(uploads_status)
            info_lines.append("")
            # Usuarios y manuales
            try:
                usuarios = Usuario.query.all()
                manuales = Manual.query.all()
                usuarios_dict = {}
                categorias = set()
                for m in manuales:
                    usuario = Usuario.query.get(m.usuario_id)
                    username = usuario.username if usuario else 'Desconocido'
                    usuarios_dict.setdefault(username, []).append(f"{m.titulo} ({m.archivo})")
                    if m.categoria_id:
                        categorias.add(m.categoria_id)
                info_lines.append(f"Total de usuarios: {len(usuarios_dict)}")
                info_lines.append(f"Total de manuales: {len(manuales)}")
                info_lines.append("")
                for username, docs in usuarios_dict.items():
                    info_lines.append(f"Usuario: {username} - {len(docs)} manual(es)")
                    for doc in docs:
                        info_lines.append(f"    - {doc}")
                    info_lines.append("")
                if categorias:
                    categorias_str = ', '.join(str(cid) for cid in categorias)
                else:
                    categorias_str = 'Ninguna'
                info_lines.append(f"Categorías usadas en manuales: {categorias_str}")
            except Exception as e:
                info_lines.append(f"Error al obtener información de usuarios y manuales: {e}")
            info_lines.append("Archivos de configuración incluidos:")
            for config_file in CONFIG_FILES:
                info_lines.append(f"    - {config_file}")
            info_lines.append("")
            info_lines.append("Bases de datos locales incluidas:")
            for db_file in DB_FILES:
                info_lines.append(f"    - {db_file}")
            info_lines.append("")
            info_lines.append("Carpeta uploads incluida completa.")
            info_lines.append("")
            info_lines.append("Backup finalizado correctamente.")
            backup_zip.writestr('info.txt', '\n'.join(info_lines))
            # SQL al ZIP
            if backup_result:
                backup_zip.write(backup_db_file, arcname=os.path.join('db', os.path.basename(backup_db_file)))
        os.remove(backup_db_file)
        flash(f'Backup generado correctamente: {backup_zip_file}', 'success')
    except Exception as e:
        flash(f'Error al generar el backup: {str(e)}', 'error')
    return redirect(url_for('main.historial'))

@main.route('/descargar_ultimo_backup')
@admin_required
def descargar_ultimo_backup():
    """Permite descargar el último backup completo (.zip)"""
    BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'backups')
    lista = sorted(glob.glob(os.path.join(BACKUP_DIR, 'backup_completo_*.zip')), reverse=True)
    if not lista:
        flash('No hay backups completos disponibles.', 'error')
        return redirect(url_for('main.historial'))
    ultimo = lista[0]
    return send_file(ultimo, as_attachment=True)

@main.route('/listar_backups')
@admin_required
def listar_backups():
    """Muestra el historial de backups disponibles, incluyendo .sql y .zip"""
    BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'backups')
    archivos = glob.glob(os.path.join(BACKUP_DIR, '*'))
    backups = []
    for archivo in archivos:
        nombre = os.path.basename(archivo)
        if nombre.startswith('db_backup_') and nombre.endswith('.sql'):
            tipo = 'Base de datos (.sql)'
            fecha = nombre.replace('db_backup_', '').replace('.sql', '')
        elif nombre.startswith('backup_completo_') and nombre.endswith('.zip'):
            tipo = 'Backup completo (.zip)'
            fecha = nombre.replace('backup_completo_', '').replace('.zip', '')
        elif nombre.startswith('uploads_backup_'):
            tipo = 'Archivos subidos (carpeta)'
            fecha = nombre.replace('uploads_backup_', '')
        else:
            continue
        backups.append({'nombre': nombre, 'fecha': fecha, 'tipo': tipo})
    backups = sorted(backups, key=lambda x: x['nombre'], reverse=True)
    return render_template('listar_backups.html', backups=backups)

@main.route('/descargar_backup/<nombre>')
@admin_required
def descargar_backup(nombre):
    """Descarga un backup específico"""
    BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'backups')
    archivo = os.path.join(BACKUP_DIR, nombre)
    if not os.path.exists(archivo):
        flash('El backup no existe.', 'error')
        return redirect(url_for('main.listar_backups'))
    if os.path.isfile(archivo):
        return send_file(archivo, as_attachment=True)
    else:
        flash('Solo se pueden descargar archivos .sql. Para carpetas, accede al servidor.', 'info')
        return redirect(url_for('main.listar_backups'))

@main.route('/eliminar_backup/<nombre>', methods=['POST'])
@admin_required
def eliminar_backup(nombre):
    """Elimina un backup específico"""
    BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'backups')
    archivo = os.path.join(BACKUP_DIR, nombre)
    try:
        if os.path.isfile(archivo):
            os.remove(archivo)
        elif os.path.isdir(archivo):
            import shutil
            shutil.rmtree(archivo)
        flash('Backup eliminado correctamente.', 'success')
    except Exception as e:
        flash(f'Error al eliminar el backup: {e}', 'error')
    return redirect(url_for('main.listar_backups'))

@main.route('/importar_backup', methods=['POST'])
@login_required
def importar_backup():
    if 'backup_file' not in request.files:
        flash('No se ha seleccionado ningún archivo.', 'danger')
        return redirect(url_for('main.listar_backups'))
    file = request.files['backup_file']
    if file.filename == '':
        flash('No se ha seleccionado ningún archivo.', 'danger')
        return redirect(url_for('main.listar_backups'))
    if not file.filename.endswith('.zip'):
        flash('El archivo debe ser un backup .zip.', 'danger')
        return redirect(url_for('main.listar_backups'))
    backup_path = os.path.join('backups', 'restore_temp.zip')
    file.save(backup_path)
    try:
        with zipfile.ZipFile(backup_path, 'r') as zip_ref:
            zip_ref.extractall('restore_temp')
        # Restaurar bases de datos
        db_folder = os.path.join('restore_temp', 'db')
        if os.path.exists(db_folder):
            for db_file in os.listdir(db_folder):
                src = os.path.join(db_folder, db_file)
                dst = db_file if db_file.endswith('.db') else os.path.join('instance', db_file)
                shutil.copy2(src, dst)
        # Restaurar archivos subidos
        uploads_folder = os.path.join('restore_temp', 'uploads')
        if os.path.exists(uploads_folder):
            dst_folder = 'uploads'
            if os.path.exists(dst_folder):
                shutil.rmtree(dst_folder)
            shutil.copytree(uploads_folder, dst_folder)
        # Restaurar configuraciones
        config_folder = os.path.join('restore_temp', 'config')
        if os.path.exists(config_folder):
            for config_file in os.listdir(config_folder):
                src = os.path.join(config_folder, config_file)
                shutil.copy2(src, config_file)
        flash('Backup restaurado correctamente.', 'success')
    except Exception as e:
        flash(f'Error al restaurar el backup: {e}', 'danger')
    finally:
        if os.path.exists('restore_temp'):
            shutil.rmtree('restore_temp')
        if os.path.exists(backup_path):
            os.remove(backup_path)
    return redirect(url_for('main.listar_backups'))

@main.route('/restaurar_backup', methods=['POST'])
@admin_required
def restaurar_backup():
    import zipfile
    import shutil
    import subprocess
    import json
    from app.models import Usuario, Manual, db
    if 'backup_file' not in request.files:
        flash('No se ha seleccionado ningún archivo.', 'danger')
        return redirect(url_for('main.listar_backups'))
    file = request.files['backup_file']
    if file.filename == '':
        flash('No se ha seleccionado ningún archivo.', 'danger')
        return redirect(url_for('main.listar_backups'))
    if not file.filename.endswith('.zip'):
        flash('El archivo debe ser un backup .zip.', 'danger')
        return redirect(url_for('main.listar_backups'))
    temp_dir = os.path.join('backups', 'restore_temp')
    os.makedirs(temp_dir, exist_ok=True)
    backup_path = os.path.join(temp_dir, 'backup.zip')
    file.save(backup_path)
    info_txt = ''
    try:
        with zipfile.ZipFile(backup_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
            # Leer info.txt si existe
            info_txt_path = os.path.join(temp_dir, 'info.txt')
            if os.path.exists(info_txt_path):
                with open(info_txt_path, 'r', encoding='utf-8') as f:
                    info_txt = f.read()
        # Restaurar carpeta uploads completa
        uploads_zip_dir = os.path.join(temp_dir, 'uploads')
        uploads_target_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'static', 'uploads')
        if os.path.exists(uploads_target_dir):
            shutil.rmtree(uploads_target_dir)
        if os.path.exists(uploads_zip_dir):
            shutil.copytree(uploads_zip_dir, uploads_target_dir)
        # Restaurar archivos de configuración si existen
        config_zip_dir = os.path.join(temp_dir, 'config')
        config_target_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
        if os.path.exists(config_zip_dir):
            for config_file in os.listdir(config_zip_dir):
                shutil.copy2(os.path.join(config_zip_dir, config_file), os.path.join(config_target_dir, config_file))
        # Restaurar bases de datos locales si existen
        db_zip_dir = os.path.join(temp_dir, 'db')
        db_target_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
        if os.path.exists(db_zip_dir):
            for db_file in os.listdir(db_zip_dir):
                shutil.copy2(os.path.join(db_zip_dir, db_file), os.path.join(db_target_dir, db_file))
        # Restaurar base de datos desde el .sql
        sql_file = None
        for f in os.listdir(db_zip_dir):
            if f.endswith('.sql'):
                sql_file = os.path.join(db_zip_dir, f)
                break
        if sql_file:
            DB_NAME = 'manuales'
            DB_USER = 'ejepmlo'
            DB_PASSWORD = 'ejemplo'
            DB_HOST = 'ejemplo'
            cmd = f"mysql -h {DB_HOST} -u {DB_USER} -p{DB_PASSWORD} {DB_NAME} < \"{sql_file}\""
            result = subprocess.run(cmd, shell=True)
            if result.returncode != 0:
                flash('Error al restaurar la base de datos.', 'danger')
                return redirect(url_for('main.listar_backups'))
        msg = 'Backup restaurado correctamente.'
        if info_txt:
            msg += f'\n\nResumen del backup restaurado:\n{info_txt}'
        flash(msg, 'success')
    except Exception as e:
        flash(f'Error al restaurar el backup: {e}', 'danger')
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
    return redirect(url_for('main.listar_backups'))

@main.route('/editar_categoria/<int:categoria_id>', methods=['GET', 'POST'])
@login_required
def editar_categoria(categoria_id):
    categoria = Categoria.query.get_or_404(categoria_id)
    usuario = Usuario.query.get(session.get('user_id'))
    is_admin = usuario.is_admin if usuario else False
    if not is_admin and categoria.usuario_id != usuario.id:
        flash('No tienes permiso para editar esta categoría.', 'error')
        return redirect(url_for('main.crear_categoria'))

    form = EditCategoryForm(obj=categoria)
    if form.validate_on_submit():
        categoria.nombre = form.nombre.data
        categoria.descripcion = form.descripcion.data
        try:
            db.session.commit()
            flash('Categoría actualizada correctamente.', 'success')
            return redirect(url_for('main.crear_categoria'))
        except Exception as e:
            db.session.rollback()
            flash('Error al actualizar la categoría.', 'error')
            current_app.logger.error(f'Error al editar categoría: {str(e)}')
    return render_template('editar_categoria.html', form=form, categoria=categoria, is_admin=is_admin)

@main.errorhandler(404)
def not_found_error(error):
    """Manejo de errores 404"""
    return render_template('errors/404.html'), 404

@main.errorhandler(500)
def internal_error(error):
    """Manejo de errores 500"""
    db.session.rollback()
    return render_template('errors/500.html'), 500

@main.errorhandler(413)
def too_large(error):
    """Archivo demasiado grande"""
    flash('El archivo es demasiado grande. Tamaño máximo permitido: 50MB', 'error')
    return redirect(url_for('main.upload'))

# Ruta para servir archivos de uploads con headers apropiados
@main.route('/uploads/<filename>')
def uploaded_file(filename):
    """Sirve archivos desde la carpeta uploads con headers apropiados para vista previa"""
    try:
        filename = secure_filename(filename)
        upload_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'uploads')
        if not os.path.exists(os.path.join(upload_folder, filename)):
            abort(404)
        return send_from_directory(upload_folder, filename)
    except Exception:
        abort(404)

# Ruta específica para vista previa de documentos
@main.route('/preview/<filename>')
def preview_document(filename):
    """Endpoint específico para vista previa de documentos"""
    try:
        filename = secure_filename(filename)
        upload_folder = app.config.get('UPLOAD_FOLDER', 'uploads')
        file_path = os.path.join(upload_folder, filename)

        if not os.path.exists(file_path):
            return jsonify({'error': 'Archivo no encontrado'}), 404

        # Obtener extensión
        extension = filename.lower().split('.')[-1]

        # Para archivos de texto, devolver el contenido
        if extension == 'txt':
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return jsonify({
                    'type': 'text',
                    'content': content,
                    'filename': filename
                })
            except UnicodeDecodeError:
                # Intentar con diferentes encodings
                for encoding in ['latin-1', 'cp1252', 'iso-8859-1']:
                    try:
                        with open(file_path, 'r', encoding=encoding) as f:
                            content = f.read()
                        return jsonify({
                            'type': 'text',
                            'content': content,
                            'filename': filename
                        })
                    except:
                        continue
                return jsonify({'error': 'No se pudo leer el archivo de texto'}), 400

        # Para PDFs y otros documentos, devolver la URL
        file_url = f"/uploads/{filename}"
        return jsonify({
            'type': 'document',
            'url': file_url,
            'filename': filename,
            'extension': extension
        })

    except Exception as e:
        print(f"Error en vista previa: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500

# Ruta para verificar si un archivo existe
@main.route('/api/file_exists/<filename>')
def file_exists(filename):
    """Verifica si un archivo existe"""
    try:
        filename = secure_filename(filename)
        upload_folder = app.config.get('UPLOAD_FOLDER', 'uploads')
        file_path = os.path.join(upload_folder, filename)
        exists = os.path.exists(file_path)

        if exists:
            # Obtener información adicional del archivo
            stat = os.stat(file_path)
            return jsonify({
                'exists': True,
                'size': stat.st_size,
                'modified': stat.st_mtime
            })
        else:
            return jsonify({'exists': False})

    except Exception as e:
        return jsonify({'exists': False, 'error': str(e)})

# Ruta para registrar usuarios
@main.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            flash('Por favor, completa todos los campos.', 'error')
            return redirect(url_for('main.register'))
        existing_user = Usuario.query.filter_by(username=username).first()
        if existing_user:
            flash('El nombre de usuario ya está en uso.', 'error')
            return redirect(url_for('main.register'))
        try:
            hashed_password = generate_password_hash(password, method='sha256')
            new_user = Usuario(username=username, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            flash('Usuario registrado exitosamente. Ahora puedes iniciar sesión.', 'success')
            return redirect(url_for('main.login'))
        except Exception as e:
            print(f'Error al registrar usuario: {str(e)}')  # Log detallado en consola
            flash('Error interno al registrar usuario. Contacta al administrador.', 'error')
            return redirect(url_for('main.register'))
    return render_template('register.html')

# Ruta para iniciar sesión
@main.route('/login', methods=['GET', 'POST'])
def login():
    # Control de intentos fallidos
    if 'login_attempts' not in session:
        session['login_attempts'] = 0
        session['last_attempt'] = 0
    bloqueo = False
    tiempo_restante = 0
    if session['login_attempts'] >= 5:
        tiempo_espera = 60  # 1 minuto
        tiempo_restante = int(tiempo_espera - (time() - session['last_attempt']))
        if tiempo_restante > 0:
            bloqueo = True
        else:
            session['login_attempts'] = 0
            bloqueo = False
    if request.method == 'POST':
        if bloqueo:
            flash(f'Demasiados intentos fallidos. Espera {tiempo_restante} segundos antes de intentar nuevamente.', 'error')
            return render_template('login.html', bloqueo=bloqueo, tiempo_restante=tiempo_restante)
        username = request.form.get('username')
        password = request.form.get('password')
        try:
            user = Usuario.query.filter_by(username=username).first()
            print(f'[LOGIN] Usuario buscado: {username}, encontrado: {user}')
            if not user or not check_password_hash(user.password, password):
                session['login_attempts'] += 1
                session['last_attempt'] = time()
                if session['login_attempts'] >= 5:
                    flash('Demasiados intentos fallidos. Espera 1 minuto antes de intentar nuevamente.', 'error')
                else:
                    flash('Credenciales inválidas. Intenta nuevamente.', 'error')
                return render_template('login.html', bloqueo=bloqueo, tiempo_restante=tiempo_restante)
            # Login exitoso
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_admin'] = getattr(user, 'is_admin', False)
            print(f'[LOGIN] Login exitoso. user_id: {user.id}, username: {user.username}, is_admin: {getattr(user, "is_admin", False)}')
            session['login_attempts'] = 0
            flash(f'Bienvenido, {user.username}!', 'success')
            return redirect(url_for('main.index'))
        except Exception as e:
            print(f'Error al iniciar sesión: {str(e)}')  # Log detallado en consola
            flash('Error interno al intentar iniciar sesión. Intenta más tarde.', 'error')
            return render_template('login.html', bloqueo=bloqueo, tiempo_restante=tiempo_restante)
    return render_template('login.html', bloqueo=bloqueo, tiempo_restante=tiempo_restante)

# Ruta para cerrar sesión
@main.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada correctamente.', 'success')
    return redirect(url_for('main.login'))

@main.route('/editar_documento/<int:documento_id>', methods=['GET', 'POST'])
@login_required
def editar_documento(documento_id):
    manual = Manual.query.get_or_404(documento_id)
    user_id = session.get('user_id')
    usuario = Usuario.query.get(user_id)
    is_admin = usuario and getattr(usuario, 'is_admin', False)

    # Filtrar categorías solo del usuario actual
    if is_admin:
        categorias = Categoria.query.all()
    else:
        categorias = Categoria.query.filter_by(usuario_id=user_id).all()

    form = EditDocumentForm()
    form.categoria_id.choices = [(c.id, c.nombre) for c in categorias]

    if request.method == 'GET':
        form.titulo.data = manual.titulo
        form.descripcion.data = manual.descripcion
        form.categoria_id.data = manual.categoria_id

    if request.method == 'POST' and request.args.get('delete_file') == '1':
        # Eliminar solo el archivo actual
        if manual.archivo:
            try:
                os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], manual.archivo))
            except Exception:
                pass
            # En vez de poner None, poner un string vacío para evitar el error de columna NOT NULL
            manual.archivo = ''
            db.session.commit()
            flash('Archivo eliminado correctamente. Ahora puedes subir uno nuevo.', 'success')
        else:
            flash('No hay archivo para eliminar.', 'warning')
        return redirect(url_for('main.editar_documento', documento_id=documento_id))

    if form.validate_on_submit():
        manual.titulo = form.titulo.data
        manual.descripcion = form.descripcion.data
        manual.categoria_id = form.categoria_id.data
        archivo = form.archivo.data
        if archivo:
            if manual.archivo:
                flash('Primero debes borrar el archivo actual antes de subir uno nuevo. Haz clic en "Borrar archivo" y luego sube el nuevo.', 'error')
                return redirect(url_for('main.editar_documento', documento_id=documento_id))
            filename, original_filename, size = save_file(archivo, current_app.config['UPLOAD_FOLDER'])
            manual.archivo = filename
        db.session.commit()
        flash('Documento actualizado correctamente.', 'success')
        return redirect(url_for('main.search'))

    return render_template('editar_documento.html', form=form, manual=manual)

import os
import datetime
import zipfile
import json
import mysql.connector

def export_mysql_db(host, user, password, db_name, output_file):
    try:
        print(f"Conectando a la base de datos {db_name} en {host}...")
        conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=db_name
        )
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"Tablas encontradas: {tables}")
        with open(output_file, 'w', encoding='utf-8') as f:
            if not tables:
                f.write("-- No se encontraron tablas en la base de datos.\n")
            for table in tables:
                try:
                    print(f"Exportando estructura de la tabla: {table}")
                    cursor.execute(f"SHOW CREATE TABLE `{table}`")
                    create_stmt = cursor.fetchone()[1]
                    f.write(f"DROP TABLE IF EXISTS `{table}`;\n{create_stmt};\n\n")
                    print(f"Exportando datos de la tabla: {table}")
                    cursor.execute(f"SELECT * FROM `{table}`")
                    rows = cursor.fetchall()
                    columns = [desc[0] for desc in cursor.description]
                    print(f"Filas encontradas en {table}: {len(rows)}")
                    for row in rows:
                        values = []
                        for value in row:
                            if value is None:
                                values.append('NULL')
                            elif isinstance(value, str):
                                escaped_value = value.replace("\\", "\\\\").replace("'", "\\'")
                                values.append(f"'{escaped_value}'")
                            else:
                                values.append(str(value))
                        f.write(f"INSERT INTO `{table}` ({', '.join(columns)}) VALUES ({', '.join(values)});\n")
                    f.write("\n")
                except Exception as table_error:
                    print(f"Error exportando la tabla {table}: {table_error}")
                    f.write(f"-- Error exportando la tabla {table}: {table_error}\n")
        cursor.close()
        conn.close()
        print(f"Backup SQL generado correctamente: {output_file}")
        return True
    except Exception as e:
        print(f"Error al exportar la base de datos: {e}")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"-- Error al exportar la base de datos: {e}\n")
        return False

# Configuración
BACKUP_DIR = 'backups'
UPLOADS_DIR = 'uploads'
DB_NAME = 'manuales'
DB_USER = 'ejemplo'
DB_PASSWORD = 'ejemplo'
DB_HOST = 'ejepmlo'
CONFIG_FILES = ['config.py', 'web.config']
DB_FILES = ['sistema_manuales.db', os.path.join('instance', 'manuales_local.db')]

# Usar rutas absolutas para todo
BACKUP_DIR = os.path.abspath(BACKUP_DIR)
UPLOADS_DIR = os.path.abspath('uploads')
DB_FILES = [os.path.abspath(f) for f in DB_FILES]
CONFIG_FILES = [os.path.abspath(f) for f in CONFIG_FILES]

# Verificar si el directorio de backups existe
if not os.path.exists(BACKUP_DIR):
    try:
        os.makedirs(BACKUP_DIR)
        print(f"Directorio de backups creado: {BACKUP_DIR}")
    except Exception as e:
        print(f"Error al crear el directorio de backups: {e}")
        exit(1)

# Fecha para el nombre del backup
fecha = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
backup_zip_file = os.path.join(BACKUP_DIR, f'backup_completo_{fecha}.zip')

# Exportar el SQL antes de crear el ZIP
backup_db_file = os.path.join(BACKUP_DIR, f'db_backup_{fecha}.sql')
backup_result = export_mysql_db(DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, backup_db_file)

# Crear el backup
with zipfile.ZipFile(backup_zip_file, 'w', zipfile.ZIP_DEFLATED) as backup_zip:
    # Agregar bases de datos locales
    for db_file in DB_FILES:
        if os.path.exists(db_file):
            backup_zip.write(db_file, arcname=os.path.join('db', os.path.basename(db_file)))
    # Agregar archivos de configuración
    for config_file in CONFIG_FILES:
        if os.path.exists(config_file):
            backup_zip.write(config_file, arcname=os.path.join('config', os.path.basename(config_file)))
    # Agregar manuales por usuario
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT m.archivo, u.username FROM manual m JOIN usuario u ON m.usuario_id = u.id")
        manuales = cursor.fetchall()
        usuarios = set([manual['username'] for manual in manuales])
        for manual in manuales:
            archivo = manual['archivo']
            username = manual['username']
            archivo_path = os.path.join(UPLOADS_DIR, archivo)
            if os.path.exists(archivo_path):
                arcname = os.path.join('manuales', username, archivo)
                backup_zip.write(archivo_path, arcname=arcname)
        # Crear carpetas vacías por usuario si no tienen manuales
        for username in usuarios:
            carpeta_usuario = os.path.join('manuales', username) + '/'
            zinfo = zipfile.ZipInfo(carpeta_usuario)
            backup_zip.writestr(zinfo, '')
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error al agregar archivos por usuario: {e}")
    # Agregar todos los archivos de la carpeta uploads
    if os.path.exists(UPLOADS_DIR):
        for foldername, subfolders, filenames in os.walk(UPLOADS_DIR):
            for filename in filenames:
                filepath = os.path.join(foldername, filename)
                arcname = os.path.join('uploads', os.path.relpath(filepath, start=UPLOADS_DIR))
                backup_zip.write(filepath, arcname=arcname)
    # Agregar metadatos
    metadata = {
        'fecha': fecha,
        'usuario': os.getenv('USERNAME', 'desconocido'),
        'version': '1.1',
        'archivos': {
            'db': DB_FILES,
            'uploads': UPLOADS_DIR,
            'config': CONFIG_FILES
        }
    }
    backup_zip.writestr('metadata.json', json.dumps(metadata, indent=4))
    # Crear info.txt con resumen detallado y auditoría
    info_lines = []
    info_lines.append(f"Backup generado correctamente el {fecha}")
    info_lines.append(f"Usuario que generó el backup: {os.getenv('USERNAME', 'desconocido')}")
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
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT u.username, m.archivo, m.titulo, m.categoria_id FROM manual m JOIN usuario u ON m.usuario_id = u.id ORDER BY u.username")
        manuales = cursor.fetchall()
        usuarios = {}
        categorias = set()
        for m in manuales:
            usuarios.setdefault(m['username'], []).append(f"{m['titulo']} ({m['archivo']})")
            if m['categoria_id']:
                categorias.add(m['categoria_id'])
        info_lines.append(f"Total de usuarios: {len(usuarios)}")
        info_lines.append(f"Total de manuales: {len(manuales)}")
        info_lines.append("")
        for username, docs in usuarios.items():
            info_lines.append(f"Usuario: {username} - {len(docs)} manual(es)")
            for doc in docs:
                info_lines.append(f"    - {doc}")
            info_lines.append("")
        # Corregido el cierre de paréntesis y comillas
        if categorias:
            categorias_str = ', '.join(str(cid) for cid in categorias)
        else:
            categorias_str = 'Ninguna'
        info_lines.append(f"Categorías usadas en manuales: {categorias_str}")
        cursor.close()
        conn.close()
    except Exception as e:
        info_lines.append(f"Error al obtener información de usuarios y manuales: {e}")
    # Archivos incluidos
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
    # Agregar el SQL al ZIP
    if backup_result:
        backup_zip.write(backup_db_file, arcname=os.path.join('db', os.path.basename(backup_db_file)))

print("Backup completado correctamente.")

# Mostrar el contenido del archivo SQL generado para depuración
try:
    with open(backup_db_file, 'r', encoding='utf-8') as f:
        print("\n--- Contenido del backup SQL generado ---")
        print(f.read())
        print("--- Fin del contenido ---\n")
except Exception as e:
    print(f"No se pudo leer el archivo SQL generado: {e}")

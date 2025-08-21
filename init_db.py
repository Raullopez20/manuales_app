#!/usr/bin/env python3
"""
Script para inicializar la base de datos con datos por defecto
"""
from app import create_app, db
from app.models import Usuario, Categoria
from werkzeug.security import generate_password_hash

def init_database():
    """Inicializa la base de datos con datos por defecto"""
    app = create_app()

    with app.app_context():
        try:
            # Crear todas las tablas
            db.create_all()
            print("✓ Tablas de base de datos creadas correctamente")

            # Verificar si ya existe un usuario admin
            admin_user = Usuario.query.filter_by(username='admin').first()
            if not admin_user:
                # Crear usuario administrador por defecto
                admin_password = generate_password_hash('admin123', method='sha256')
                admin_user = Usuario(
                    username='admin',
                    password=admin_password,
                    is_admin=True
                )
                db.session.add(admin_user)
                print("✓ Usuario administrador creado (admin/admin123)")
            else:
                print("✓ Usuario administrador ya existe")

            # Verificar si ya existe un usuario regular
            regular_user = Usuario.query.filter_by(username='usuario').first()
            if not regular_user:
                # Crear usuario regular por defecto
                user_password = generate_password_hash('usuario123', method='sha256')
                regular_user = Usuario(
                    username='usuario',
                    password=user_password,
                    is_admin=False
                )
                db.session.add(regular_user)
                print("✓ Usuario regular creado (usuario/usuario123)")
            else:
                print("✓ Usuario regular ya existe")

            # Commit usuarios primero
            db.session.commit()

            # Crear categorías por defecto para el admin
            categorias_defecto = [
                {'nombre': 'Manuales Técnicos', 'descripcion': 'Documentación técnica y de sistemas'},
                {'nombre': 'Guías de Usuario', 'descripcion': 'Manuales para usuarios finales'},
                {'nombre': 'Procedimientos', 'descripcion': 'Procedimientos operativos y administrativos'},
                {'nombre': 'Políticas', 'descripcion': 'Políticas corporativas y de seguridad'}
            ]

            for cat_data in categorias_defecto:
                categoria_existente = Categoria.query.filter_by(
                    nombre=cat_data['nombre'],
                    usuario_id=admin_user.id
                ).first()

                if not categoria_existente:
                    categoria = Categoria(
                        nombre=cat_data['nombre'],
                        descripcion=cat_data['descripcion'],
                        usuario_id=admin_user.id
                    )
                    db.session.add(categoria)
                    print(f"✓ Categoría '{cat_data['nombre']}' creada")
                else:
                    print(f"✓ Categoría '{cat_data['nombre']}' ya existe")

            # Commit final
            db.session.commit()
            print("\n🎉 Base de datos inicializada correctamente!")
            print("\n📋 Credenciales por defecto:")
            print("   👤 Administrador: admin / admin123")
            print("   👤 Usuario regular: usuario / usuario123")

        except Exception as e:
            print(f"❌ Error al inicializar la base de datos: {e}")
            db.session.rollback()
            return False

    return True

if __name__ == '__main__':
    print("🚀 Inicializando base de datos...")
    success = init_database()
    if success:
        print("\n✅ Proceso completado exitosamente")
    else:
        print("\n❌ Proceso falló")

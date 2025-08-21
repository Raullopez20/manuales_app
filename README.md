# Sistema de Manuales Empresariales

![Vista de la barra de navegación](static/img/navbar-docs.png)

Sistema web profesional para la gestión centralizada de documentación y manuales corporativos. Desarrollado con Flask y diseñado con una paleta de colores empresarial moderna.

## 🚀 Características Principales

- **Gestión de Documentos**: Subida y organización de múltiples tipos de archivos (PDF, Word, Excel, PowerPoint)
- **Búsqueda Avanzada**: Búsqueda por contenido, categorías y filtros avanzados
- **Categorización**: Sistema de categorías personalizables para organizar documentos
- **Diseño Profesional**: Interfaz moderna con paleta de colores empresarial
- **Responsive**: Totalmente adaptable a dispositivos móviles y tablets
- **Auditoría**: Seguimiento de descargas y actividad de usuarios

## 🛠️ Tecnologías Utilizadas

- **Backend**: Flask 2.3.3, SQLAlchemy, Flask-WTF
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap 5
- **Base de Datos**: SQLite (desarrollo) / PostgreSQL (producción)
- **Iconos**: Font Awesome, Bootstrap Icons
- **Animaciones**: AOS (Animate On Scroll)

## 📋 Requisitos del Sistema

- Python 3.8+
- pip (gestor de paquetes de Python)
- Navegador web moderno

## 🔧 Instalación y Configuración

### 1. Clonar el repositorio
```bash
git clone https://github.com/tu-usuario/sistema-manuales.git
cd sistema-manuales
```

### 2. Crear entorno virtual
```bash
python -m venv venv

# En Windows
venv\Scripts\activate

# En Linux/Mac
source venv/bin/activate
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno
Crear archivo `.env` en la raíz del proyecto:
```bash
SECRET_KEY=tu-clave-secreta-muy-segura
FLASK_ENV=development
DATABASE_URL=sqlite:///sistema_manuales.db
UPLOAD_FOLDER=uploads
```

### 5. Inicializar la base de datos
```bash
flask init-db
```

### 6. Ejecutar la aplicación
```bash
python app.py
```

La aplicación estará disponible en `http://127.0.0.1:5000`

## 📁 Estructura del Proyecto

```
sistema-manuales/
├── app.py                 # Aplicación principal
├── models.py             # Modelos de base de datos
├── routes.py             # Rutas de la aplicación
├── forms.py              # Formularios Flask-WTF
├── requirements.txt      # Dependencias
├── README.md            # Este archivo
├── .env                 # Variables de entorno
├── templates/           # Templates HTML
│   ├── base.html        # Template base
│   ├── index.html       # Dashboard principal
│   ├── upload.html      # Subida de archivos
│   ├── search.html      # Búsqueda avanzada
│   ├── crear_categoria.html  # Crear categorías
│   └── errors/          # Páginas de error
│       ├── 404.html
│       ├── 500.html
│       └── 413.html
├── static/              # Archivos estáticos
│   ├── css/
│   │   └── base.css     # Estilos profesionales
│   └── js/              # JavaScript personalizado
└── uploads/             # Archivos subidos (se crea automáticamente)
```

## 🎨 Paleta de Colores Profesional

El sistema utiliza una paleta de colores empresarial cuidadosamente seleccionada:

- **Primario**: `#2563eb` (Azul corporativo)
- **Secundario**: `#64748b` (Gris azulado)
- **Acento**: `#059669` (Verde corporativo)
- **Advertencia**: `#d97706` (Naranja corporativo)
- **Error**: `#dc2626` (Rojo corporativo)
- **Grises**: De `#f8fafc` a `#0f172a` (Escala profesional)

## 📱 Funcionalidades Implementadas

### Dashboard Principal
- Vista general del sistema con estadísticas
- Acciones rápidas para subir y buscar documentos
- Lista de documentos recientes
- Estado del sistema en tiempo real

### Gestión de Documentos
- Subida múltiple de archivos con drag & drop
- Vista previa de archivos seleccionados
- Validación de tipos y tamaños de archivo
- Categorización automática

### Búsqueda Avanzada
- Búsqueda por título, contenido y categoría
- Filtros por tipo de archivo, fecha y usuario
- Resultados con vista previa y paginación

### Categorización de Documentos
- Crear, editar y eliminar categorías
- Asignar documentos a una o varias categorías
- Visualización por categorías

### Auditoría y Seguridad
- Registro de descargas y actividad de usuarios
- Control de acceso por roles (administrador, usuario)
- Gestión de usuarios y permisos

### Errores y Manejo de Archivos
- Páginas personalizadas para errores 404, 413 y 500
- Validación y manejo seguro de archivos subidos

### Responsive y Experiencia de Usuario
- Interfaz adaptable a móviles y tablets
- Animaciones y transiciones suaves
- Iconografía profesional

---

¿Tienes dudas o necesitas soporte? Contacta al equipo de desarrollo.

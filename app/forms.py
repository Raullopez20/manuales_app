from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, TextAreaField, SelectField, SubmitField, MultipleFileField
from wtforms.validators import DataRequired, Length, Optional, ValidationError
from wtforms.widgets import FileInput

class MultipleFileAllowed(object):
    """
    Validador personalizado para múltiples archivos
    """
    def __init__(self, upload_set, message=None):
        self.upload_set = upload_set
        self.message = message

    def __call__(self, form, field):
        if not field.data:
            return

        for file in field.data:
            if file and hasattr(file, 'filename') and file.filename:
                if not self.upload_set.file_allowed(file, file.filename):
                    message = self.message or f'Archivo {file.filename} no permitido. Solo se permiten: {", ".join(self.upload_set.extensions)}'
                    raise ValidationError(message)

class UploadForm(FlaskForm):
    archivos = MultipleFileField(
        'Archivos',
        validators=[
            FileAllowed(['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt'], 'Solo se permiten documentos.')
        ],
        render_kw={
            'accept': '.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt',
            'multiple': True
        }
    )

    titulo = StringField(
        'Título del documento',
        validators=[
            DataRequired(message='El título es obligatorio'),
            Length(min=5, max=200, message='El título debe tener entre 5 y 200 caracteres')
        ],
        render_kw={'placeholder': 'Ej: Manual de Usuario - Sistema CRM v2.0'}
    )

    descripcion = TextAreaField(
        'Descripción',
        validators=[
            DataRequired(message='La descripción es obligatoria'),
            Length(min=10, max=500, message='La descripción debe tener entre 10 y 500 caracteres')
        ],
        render_kw={
            'placeholder': 'Describe brevemente el contenido del documento',
            'rows': 4
        }
    )

    categoria_id = SelectField(
        'Categoría',
        coerce=int,
        validators=[DataRequired(message='Debe seleccionar una categoría')],
        choices=[]
    )

    submit = SubmitField('Subir Documentos')

class SearchForm(FlaskForm):
    """Formulario de búsqueda avanzada"""
    termino = StringField(
        'Buscar',
        validators=[Optional()],
        render_kw={'placeholder': 'Buscar en títulos, contenido y descripciones...'}
    )

    categoria_id = SelectField(
        'Categoría',
        coerce=int,
        validators=[Optional()],
        choices=[]
    )

    tipo_archivo = SelectField(
        'Tipo de archivo',
        choices=[
            ('', 'Todos los tipos'),
            ('pdf', 'PDF'),
            ('doc,docx', 'Word'),
            ('xls,xlsx', 'Excel'),
            ('ppt,pptx', 'PowerPoint'),
            ('txt', 'Texto')
        ],
        validators=[Optional()]
    )

    submit = SubmitField('Buscar')

class CategoryForm(FlaskForm):
    """Formulario para crear categorías"""
    nombre = StringField(
        'Nombre de la categoría',
        validators=[
            DataRequired(message='El nombre es obligatorio'),
            Length(min=3, max=100, message='El nombre debe tener entre 3 y 100 caracteres')
        ],
        render_kw={'placeholder': 'Ej: Manuales de Usuario, Procedimientos, etc.'}
    )

    descripcion = TextAreaField(
        'Descripción (opcional)',
        validators=[
            Optional(),
            Length(max=300, message='La descripción no puede exceder 300 caracteres')
        ],
        render_kw={
            'placeholder': 'Breve descripción de la categoría',
            'rows': 3
        }
    )

    submit = SubmitField('Crear Categoría')

class EditDocumentForm(FlaskForm):
    titulo = StringField(
        'Título del documento',
        validators=[
            DataRequired(message='El título es obligatorio'),
            Length(min=5, max=200, message='El título debe tener entre 5 y 200 caracteres')
        ]
    )
    descripcion = TextAreaField(
        'Descripción',
        validators=[Optional(), Length(max=500)]
    )
    categoria_id = SelectField('Categoría', coerce=int, validators=[DataRequired()])
    archivo = FileField(
        'Archivo',
        validators=[
            FileAllowed(['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt'], 'Solo se permiten documentos.'),
            Optional()
        ]
    )
    submit = SubmitField('Actualizar documento')

class EditCategoryForm(FlaskForm):
    nombre = StringField('Nombre', validators=[DataRequired(), Length(max=100)])
    descripcion = TextAreaField('Descripción', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Guardar cambios')

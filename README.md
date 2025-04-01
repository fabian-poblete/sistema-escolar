 # Sistema de Atrasos Escolares

Sistema para gestionar atrasos de estudiantes en instituciones educativas.

## Características

- Registro de estudiantes con información básica
- Registro de atrasos con justificación
- Interfaz intuitiva y fácil de usar
- Reportes de atrasos por estudiante
- Sistema de notificaciones por email

## Requisitos

- Python 3.8 o superior
- pip (gestor de paquetes de Python)

## Instalación

1. Clonar el repositorio
2. Crear un entorno virtual:
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

3. Instalar dependencias:
```bash
pip install -r requirements.txt
```

4. Realizar migraciones:
```bash
python manage.py migrate
```

5. Crear superusuario:
```bash
python manage.py createsuperuser
```

6. Ejecutar el servidor:
```bash
python manage.py runserver
```

## Uso

1. Acceder a http://localhost:8000/admin para gestionar estudiantes y atrasos
2. Acceder a http://localhost:8000 para usar la interfaz principal
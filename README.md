# NEXUS Esports Manager

Plataforma web de gestión competitiva de esports construida con **Django 6.1**, **Bootstrap 5** y **Django REST Framework**. Administra organizaciones, equipos, jugadores, staff, partidos y sesiones de entrenamiento bajo un dashboard oscuro "NEXUS".

## Requisitos

- Python 3.12 o superior
- Git
- (Opcional) GitHub Desktop

## Puesta en marcha (desarrollo local)

### 1. Crear y activar el entorno virtual

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Instalar dependencias

```powershell
pip install -r requirements.txt
```

### 3. Aplicar migraciones

```powershell
python manage.py migrate
```

### 4. Crear un superusuario (acceso al panel y a todas las funciones)

```powershell
python manage.py createsuperuser
```

> Nota: en tu base de datos local ya existe la cuenta de prueba `admin` / `Nexus2026` (solo en `db.sqlite3`, que NO se sube a Git).

### 5. Arrancar el servidor

```powershell
python manage.py runserver
```

Abre http://127.0.0.1:8000/ e inicia sesión. También puedes entrar a http://127.0.0.1:8000/admin/ (panel de Django).

## Verificación rápida

```powershell
python manage.py check          # revisa configuración y URLs del sistema
python manage.py makemigrations # detecta cambios pendientes en modelos
```

## Estructura del proyecto

```
proyecto backend/
├── config/            # settings, urls raíz, wsgi/asgi
├── core/              # dashboard, estadísticas, ajustes, permisos, mixins
├── accounts/          # usuario personalizado y autenticación
├── organizations/     # organizaciones, juegos, roles y equipos
├── players/           # jugadores y asignaciones a equipos
├── staff/             # integrantes del staff y asignaciones
├── matches/           # partidos, mapas y estadísticas (jugador/equipo)
├── training/          # sesiones de entrenamiento y asistencia
├── templates/         # plantillas HTML (tema NEXUS)
├── templates_beta/    # maquetas originales de diseño (referencia)
├── static/            # estilos NEXUS (styles.css)
└── manage.py
```

## Rutas principales

| URL            | Vista                     |
| -------------- | ------------------------- |
| `/`            | Dashboard general         |
| `/equipos/`    | Directorio de equipos     |
| `/jugadores/`  | Directorio de jugadores   |
| `/partidos/`   | Calendario de partidos    |
| `/entrenamientos/` | Sesiones de entrenamiento |
| `/estadisticas/` | Centro de análisis       |
| `/configuracion/` | Ajustes                  |
| `/api/`        | API REST (DRF)            |

## Git y GitHub

La base de datos (`db.sqlite3`), el entorno virtual (`.venv/`) y los cachés de Python (`__pycache__/`) están excluidos del repositorio mediante `.gitignore`.

Flujo de trabajo:

```powershell
git status                  # ver cambios
git add -A                  # añadir todos
git commit -m "mensaje"     # crear commit
git push origin main        # subir a GitHub
```

O usa **GitHub Desktop**: `File → Add local repository` y selecciona la carpeta del proyecto.

## Consideraciones

- `DEBUG = True` por defecto y `SECRET_KEY` con valor local: NO desplegar tal cual en producción. Configura `DJANGO_SECRET_KEY` como variable de entorno, `DEBUG = False` y `ALLOWED_HOSTS` antes de publicar.
- Los modelos están en inglés; las plantillas utilizan contexto renombrado (`equipos`, `jugadores`, `partidos`, `entrenamientos`, `equipo`, `jugador`).
- Diseño dark "NEXUS" en `static/css/styles.css`; las maquetas originales viven en `templates_beta/`.
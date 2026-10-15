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

### 4. Cargar datos iniciales (Fixtures)

Para poblar la base de datos con los datos de prueba y usuarios iniciales en el orden correcto de dependencias:

```powershell
python manage.py loaddata organizations.json users.json players.json staff.json tournaments.json tournament_participants.json matches.json training.json
```

> **Credenciales incluidas:**
> - Superusuario / Admin: `admin` / `KuoLUWFJGL1VYDYh`

*(Opcional) También puedes crear un superusuario adicional con:*
```powershell
python manage.py createsuperuser
```

### 4b. Ampliar con equipos de primer nivel (Valorant + LoL)

Para llevar Valorant y League of Legends a 16 equipos cada uno (incluyendo cuerpo técnico):

```powershell
python manage.py seed_val_lol
```

### 5. Arrancar el servidor

```powershell
python manage.py runserver
```

Abre http://127.0.0.1:8000/ e inicia sesión. También puedes entrar a http://127.0.0.1:8000/admin/ (panel de Administración de Django).

## Verificación rápida

```powershell
python manage.py check          # revisa configuración y URLs del sistema
python manage.py makemigrations # detecta cambios pendientes en modelos
```

## Estructura del proyecto

```
eSportsNexus/
├── config/              # settings, urls raíz, wsgi/asgi
├── core/              # dashboard, ajustes, permisos, mixins
├── accounts/          # usuario personalizado y autenticación
├── organizations/     # organizaciones, juegos, roles y equipos
├── players/           # jugadores y asignaciones a equipos
├── staff/             # integrantes del staff y asignaciones
├── matches/           # partidos, torneos, mapas y estadísticas (jugador/equipo)
├── training/          # sesiones de entrenamiento y asistencia
├── templates/         # plantillas HTML (tema NEXUS)
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
| `/torneos/`    | Catálogo de torneos       |
| `/torneos/<id>/` | Detalle del torneo (participantes, grupos y llaves) |
| `/torneos/<id>/participantes/` | Gestión de participantes (staff) |
| `/entrenamientos/` | Sesiones de entrenamiento |
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
- Diseño dark "NEXUS" en `static/css/styles.css`.
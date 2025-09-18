# PRUEBA TÉCNICA CAROLINA RODRÍGUEZ
# Pokémon Async League — Backend (Docker)
Backend del proyecto Pokémon Async League, preparado para ejecutarse de forma reproducible con Docker y Docker Compose.
Incluye apps Django para el dominio del proyecto (por ejemplo, battles) y la configuración del sitio (pokeleague). El repositorio ya trae archivos clave como Dockerfile, docker-compose.yml, .env, manage.py, db.sqlite3 y un README base, además de un archivo celerybeat-schedule (para tareas programadas si se habilita Celery). 

Nota: Este README describe el levantamiento, flujo de desarrollo y la funcionalidad esperada a partir de lo que publica el repo (Docker + Django y la app battles). Ajusta las secciones marcadas como “Opcional / TBD” si el proyecto evoluciona o se añaden servicios (por ejemplo, una cola para Celery).

## Stack y arquitectura
- # Lenguaje:
    Python (proyecto Django) — el repo contiene manage.py y apps Django (pokeleague, battles). 
- # Contenedores: 
    Docker + Docker Compose para orquestar el servicio del backend. (El README original ya indica docker compose up --build.) 
- # Base de datos de desarrollo: 
    db.sqlite3 incluida para uso local/out-of-the-box. 
- # Dependencias: 
    Definidas en requirements.txt (instaladas automáticamente en la imagen Docker). 
- # Arquitectura (alto nivel):
    - pokeleague/: configuración del proyecto Django (ajustes, URL raíz, etc.).
    - battles/: lógica de dominio para batallas (modelos, vistas, urls, tests).
    - Base de datos: SQLite para desarrollo; puedes cambiar a Postgres/MySQL en producción ajustando variables de entorno y docker-compose.yml.
    - Celery / Beat: existe celerybeat-schedule; para procesamiento asíncrono, se añadirán servicios de cola y beat.

## Requisitos
- Docker versión 4.46.0 o superior
- Docker Compose (incluido en Docker Desktop moderno)

## Configuración de entorno
El proyecto incluye un archivo .env en la raíz del repo. Revísalo y ajusta las variables según tu entorno (por ejemplo: DEBUG, ALLOWED_HOSTS, credenciales de DB si cambias a Postgres, etc.).

## Arranque
Construye y levanta los contenedores con:
```bash
docker compose up --build
```
El servicio quedará disponible en http://localhost:8000 (según la configuración del docker-compose.yml).

## Ejecutar migraciones (si aplica)
```bash
docker compose exec backend python manage.py migrate
```

## Ejecutar tests
Para correr las pruebas de la aplicación (ejemplo: módulo battles):
```bash
docker compose exec backend python manage.py test battles
```

## Estructura de carpetas
.
├── battles/                 # App Django del dominio de batallas
├── pokeleague/              # Configuración del proyecto Django
├── manage.py                # Entry point de Django
├── docker-compose.yml       # Orquestación de servicios
├── Dockerfile               # Imagen del backend
├── requirements.txt         # Dependencias de Python
├── .env                     # Variables de entorno (desarrollo)
├── db.sqlite3               # BD local de desarrollo
├── celerybeat-schedule      # Programación de tareas (si se usa Celery Beat)
└── README.md                # Este documento

## Endpoints y navegación
Panel de administración:
http://localhost:8000/admin/ (si habilitado y con superusuario).

Rutas del proyecto y apps:
Revisa pokeleague/urls.py (rutas raíz) y battles/urls.py (rutas de la app).

Comandos útiles para inspección:
# Ver URL patterns en consola (requiere paquete como django-extensions)
```bash
docker compose exec backend python manage.py show_urls
```

## Tareas asíncronas
# Worker
docker compose exec backend celery -A pokeleague worker -l info

# Beat (programador)
docker compose exec backend celery -A pokeleague beat -l info --schedule=/code/celerybeat-schedule

## Guía de troubleshooting
⦁	El contenedor backend no arranca
    -	Verifica que SECRET_KEY y DJANGO_SETTINGS_MODULE estén bien en .env.
    -	Revisa logs: docker compose logs -f backend.

⦁	Error de migraciones
    -	Ejecuta docker compose exec backend python manage.py migrate.
    -   Si cambiaste de SQLite a Postgres, revisa DATABASE_URL o la configuración equivalente.

⦁	No puedo acceder a http://localhost:8000
	-   Confirma que el puerto esté mapeado en docker-compose.yml.
	-   En Windows WSL2, revisa firewalls/puentes de red.

⦁	Admin 404
    -   Comprueba que django.contrib.admin esté habilitado y que exista path('admin/', admin.site.urls) en URLs.
    -   Crea un superusuario si no lo has hecho.
    
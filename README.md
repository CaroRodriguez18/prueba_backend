# PRUEBA TÉCNICA CAROLINA RODRÍGUEZ
# Pokémon Async League — Backend (Docker)
Este proyecto corresponde al backend de la aplicación Pokémon Async League, diseñado para ser ejecutado en un entorno Docker.

## Requisitos
- Docker versión 4.46.0 o superior
- Docker Compose

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


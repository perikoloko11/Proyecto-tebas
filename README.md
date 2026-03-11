# ⚽ LaLiga App — Alineaciones Liga Española

Aplicación web para consultar plantillas y alineaciones de los 10 equipos de LaLiga.
Todo corre en un **único contenedor Docker** con MySQL + Flask + Nginx.

---

## 🚀 Arranque rápido

```bash
cd laliga-single
docker compose up --build
```

Abre **http://localhost** cuando veas en los logs:
```
==> Arrancando Flask y Nginx con supervisord...
```

---

## 🔑 Credenciales

| Rol | Usuario | Contraseña |
|---|---|---|
| Admin | `admin` | `Admin1234!` |
| Usuario | `usuario` | `User1234!` |

---

## 🛠 Stack

| Capa | Tecnología |
|---|---|
| Backend | Python 3.12 + Flask 3.0.3 + SQLAlchemy + JWT |
| Frontend | HTML5 + CSS3 + JavaScript vanilla |
| Base de datos | MySQL 8.0 |
| Servidor web | Nginx 1.27 |
| Infraestructura | Docker + Supervisord |

---

## 🔌 API — Endpoints

**Base URL:** `http://localhost/api`

| Método | Endpoint | Auth | Descripción |
|---|---|---|---|
| `GET` | `/health` | No | Estado de la API |
| `POST` | `/auth/login` | No | Login — devuelve JWT |
| `GET` | `/auth/me` | JWT | Usuario autenticado |
| `GET` | `/teams` | No | Lista equipos |
| `GET` | `/teams/:id` | No | Detalle con jugadores |
| `POST` | `/teams` | Admin | Crear equipo |
| `PUT` | `/teams/:id` | Admin | Editar equipo |
| `DELETE` | `/teams/:id` | Admin | Eliminar equipo |
| `POST` | `/players` | Admin | Crear jugador |
| `PUT` | `/players/:id` | Admin | Editar jugador |
| `DELETE` | `/players/:id` | Admin | Eliminar jugador |

**Header para rutas protegidas:**
```
Authorization: Bearer <token>
```

---

## 🛡 Seguridad — OWASP Top 10

| Control OWASP | Medida aplicada |
|---|---|
| **A01 — Broken Access Control** | Asegura que solo los administradores puedan hacer cambios.. |
| **A02 — Cryptographic Failures** | Protege las contraseñas almacenadas en la base de datos.. |
| **A03 — Injection** |  Evita que atacantes manipulen tu base de datos con texto malicioso.. |
| **A05 — Security Misconfiguration** | Cierra puertas innecesarias en tu servidor. |
| **A07 — Auth Failures** | Controla las sesiones y no da pistas a los atacantes. |
| **A08 — Data Integrity** | Garantiza que tu código usa dependencias fiables y sin alteraciones. |
| **A09 — Logging & Monitoring** | Deja rastro de todo lo que ocurre en tu aplicación. |

---

## 🧪 Pruebas Postman

Importa `LaLiga_5pruebas.postman_collection.json` en Postman y ejecuta en orden:

| # | Prueba | Método | Endpoint |
|---|---|---|---|
| 1 | Health Check | `GET` | `/api/health` |
| 2 | Login Admin | `POST` | `/api/auth/login` |
| 3 | Listar Equipos | `GET` | `/api/teams` |
| 4 | Crear Equipo | `POST` | `/api/teams` |
| 5 | Eliminar Equipo | `DELETE` | `/api/teams/:id` |

> El token y el `team_id` se guardan automáticamente entre pruebas.

---

## 🔧 Comandos útiles

```bash
# Arrancar en segundo plano
docker compose up -d --build

# Ver logs
docker compose logs -f

# Reset completo (borra datos MySQL)
docker compose down -v && docker compose up --build

# Conectar a MySQL
docker exec -it laliga-app mysql -u laliga -plaligapass laliga
```

---

## ❗ Problemas comunes

| Problema | Solución |
|---|---|
| Página no carga | Espera el mensaje `Arrancando Flask y Nginx` en los logs |
| Login no funciona | Espera `SEED >> Usuarios creados` o haz `docker compose down -v` |
| Puerto 80 ocupado | Cambia a `"8080:80"` en `docker-compose.yml` y accede a `:8080` |
| MySQL tarda mucho | Normal en el primer arranque (30-60 s). Espera y recarga |

---

## 📦 Versiones

| Versión | Cambio principal |
|---|---|
| v1 | Multi-contenedor. Bug: tipo `YEAR` en MySQL no acepta años < 1901 |
| v2 | Fix `YEAR` → `SMALLINT`. Hashes de contraseña generados por el backend |
| v3 | Reescritura completa. El backend crea tablas y datos con `db.create_all()` |
| v4 | Fix CSS: la vista no cambiaba tras el login (`display: block !important`) |
| v5 | `start_period` MySQL aumentado a 60s para máquinas lentas |
| **single** | **Versión actual.** Todo en un único contenedor con Supervisord |

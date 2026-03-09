================================================================================
  LaLiga App — Alineaciones Liga Española
  README v1.0 | Marzo 2026
================================================================================

DESCRIPCION
-----------
Aplicacion web para consultar plantillas y alineaciones de los 10 equipos
de LaLiga. Incluye autenticacion JWT con dos roles (admin y usuario),
panel de administracion para gestionar equipos y jugadores, y visualizacion
de alineaciones en campo.

Todo el proyecto corre en un UNICO CONTENEDOR Docker que incluye:
  - MySQL 8.0         -> base de datos
  - Flask (Python)    -> API REST en puerto 5001 (interno)
  - Nginx             -> servidor web y proxy en puerto 80 (publico)


--------------------------------------------------------------------------------
ESTRUCTURA DE ARCHIVOS
--------------------------------------------------------------------------------

laliga-single/
  Dockerfile          -> imagen unica con MySQL + Flask + Nginx + supervisord
  docker-compose.yml  -> levanta el contenedor unico
  app.py              -> API REST en Flask (toda la logica del backend)
  requirements.txt    -> dependencias Python
  index.html          -> frontend SPA (HTML + CSS + JavaScript)
  nginx.conf          -> configuracion Nginx (proxy /api/ -> Flask)
  supervisord.conf    -> gestiona los procesos Flask y Nginx
  start.sh            -> script de arranque: inicia MySQL primero, luego supervisord
  my.cnf              -> configuracion MySQL


--------------------------------------------------------------------------------
REQUISITOS
--------------------------------------------------------------------------------

  - Docker Desktop instalado y en ejecucion
  - Puerto 80 libre en tu maquina


--------------------------------------------------------------------------------
INSTALACION Y ARRANQUE
--------------------------------------------------------------------------------

1. Descarga y descomprime el ZIP del proyecto

2. Abre una terminal (PowerShell en Windows) y entra en la carpeta:

      cd laliga-single

3. Construye y arranca el contenedor:

      docker compose up --build

4. Espera hasta ver este mensaje en los logs:

      ==> Arrancando Flask y Nginx con supervisord...

5. Abre el navegador en:

      http://localhost


PRIMER ARRANQUE
El primer arranque tarda entre 30 y 60 segundos porque MySQL necesita
inicializar los ficheros de datos. Los arranques siguientes son mas rapidos.

ORDEN DE ARRANQUE DENTRO DEL CONTENEDOR (start.sh)
  1. MySQL arranca
  2. El script espera hasta que MySQL responde al ping (hasta 30 intentos)
  3. Se crea la base de datos "laliga" y el usuario con permisos
  4. Supervisord lanza Flask y Nginx
  5. Flask conecta a MySQL, crea las tablas y carga los datos iniciales


--------------------------------------------------------------------------------
CREDENCIALES
--------------------------------------------------------------------------------

  Rol         Usuario     Contrasena
  ---------   ---------   ----------
  Admin       admin       Admin1234!
  Usuario     usuario     User1234!

El admin puede crear, editar y eliminar equipos y jugadores.
El usuario solo puede consultar la informacion.


--------------------------------------------------------------------------------
DATOS INICIALES
--------------------------------------------------------------------------------

La aplicacion carga automaticamente 10 equipos con 11 jugadores cada uno:

  1.  Athletic Club          San Mames              Bilbao       (1898)
  2.  Atletico Madrid        Civitas Metropolitano  Madrid       (1903)
  3.  FC Barcelona           Spotify Camp Nou       Barcelona    (1899)
  4.  Girona FC              Estadio Montilivi      Girona       (1930)
  5.  Real Betis             Benito Villamarin      Sevilla      (1907)
  6.  Real Madrid            Santiago Bernabeu      Madrid       (1902)
  7.  Real Sociedad          Reale Arena            San Sebastian(1909)
  8.  Sevilla FC             Ramon Sanchez-Pizjuan  Sevilla      (1890)
  9.  Valencia CF            Mestalla               Valencia     (1919)
  10. Villarreal CF          Estadio de la Ceramica Villarreal   (1923)


--------------------------------------------------------------------------------
API REST — ENDPOINTS
--------------------------------------------------------------------------------

BASE URL: http://localhost/api

  METODO   ENDPOINT               AUTH      DESCRIPCION
  ------   --------------------   -------   ------------------------------------
  GET      /health                No        Estado de la API
  POST     /auth/login            No        Login, devuelve JWT
  GET      /auth/me               JWT       Datos del usuario autenticado
  GET      /teams                 No        Lista todos los equipos
  GET      /teams/:id             No        Detalle de equipo con jugadores
  POST     /teams                 Admin     Crear nuevo equipo
  PUT      /teams/:id             Admin     Editar equipo
  DELETE   /teams/:id             Admin     Eliminar equipo y sus jugadores
  POST     /players               Admin     Anadir jugador a un equipo
  PUT      /players/:id           Admin     Editar jugador
  DELETE   /players/:id           Admin     Eliminar jugador

AUTORIZACION
Para las rutas que requieren JWT, incluye el header:
  Authorization: Bearer <token>

El token se obtiene haciendo POST a /auth/login y caduca en 1 hora.

CODIGOS DE RESPUESTA
  200  OK                  Operacion correcta
  201  Created             Recurso creado
  400  Bad Request         Faltan campos o formato invalido
  401  Unauthorized        Sin token o credenciales incorrectas
  403  Forbidden           Sin permisos de administrador
  404  Not Found           Recurso no encontrado
  409  Conflict            Nombre de equipo duplicado
  422  Unprocessable       Token JWT malformado
  500  Internal Error      Error de servidor (ver logs)

EJEMPLO DE LOGIN
  curl -X POST http://localhost/api/auth/login \
       -H "Content-Type: application/json" \
       -d '{"username":"admin","password":"Admin1234!"}'

EJEMPLO DE CREAR EQUIPO
  curl -X POST http://localhost/api/teams \
       -H "Content-Type: application/json" \
       -H "Authorization: Bearer <token>" \
       -d '{"name":"RCD Espanyol","city":"Barcelona","founded":1900}'


--------------------------------------------------------------------------------
PRUEBAS CON POSTMAN
--------------------------------------------------------------------------------

Se incluye el archivo:
  LaLiga_5pruebas.postman_collection.json

Para importarlo en Postman:
  1. Abre Postman
  2. Haz clic en "Import"
  3. Selecciona el archivo JSON
  4. Ejecuta las pruebas en orden del 1 al 5

Las 5 pruebas incluidas:

  1. Health Check       GET  /api/health          Verifica que la API responde
  2. Login Admin        POST /api/auth/login       Guarda el token automaticamente
  3. Listar Equipos     GET  /api/teams            Comprueba los 10 equipos
  4. Crear Equipo       POST /api/teams            Crea equipo, guarda el ID
  5. Eliminar Equipo    DELETE /api/teams/:id      Borra el equipo del paso 4

El token y el team_id se guardan automaticamente entre pruebas gracias
a los scripts de "Tests" incluidos en la coleccion.


--------------------------------------------------------------------------------
COMANDOS UTILES
--------------------------------------------------------------------------------

Arrancar la aplicacion:
  docker compose up --build

Arrancar en segundo plano:
  docker compose up -d --build

Ver logs en tiempo real:
  docker compose logs -f

Ver solo logs del proceso Flask:
  docker exec laliga-app tail -f /var/log/supervisor/flask.out.log

Ver solo logs de Nginx:
  docker exec laliga-app tail -f /var/log/supervisor/nginx.out.log

Parar el contenedor:
  docker compose down

Parar y borrar datos de MySQL (reset completo):
  docker compose down -v

Conectar a MySQL desde dentro del contenedor:
  docker exec -it laliga-app mysql -u laliga -plaligapass laliga

Ver los equipos directamente en MySQL:
  docker exec -it laliga-app mysql -u laliga -plaligapass laliga \
    -e "SELECT id, name, city FROM teams;"

Ver el estado del contenedor:
  docker ps


--------------------------------------------------------------------------------
TECNOLOGIAS UTILIZADAS
--------------------------------------------------------------------------------

  Backend
    Python 3.12
    Flask 3.0.3
    Flask-SQLAlchemy 3.1.1
    Flask-JWT-Extended 4.6.0
    Flask-CORS 4.0.1
    PyMySQL 1.1.1
    Werkzeug 3.0.4

  Frontend
    HTML5, CSS3, JavaScript vanilla
    Google Fonts (Barlow, Barlow Condensed)

  Base de Datos
    MySQL 8.0

  Infraestructura
    Docker (contenedor unico)
    Nginx 1.27
    Supervisord (gestor de procesos)


--------------------------------------------------------------------------------
SOLUCION DE PROBLEMAS
--------------------------------------------------------------------------------

La pagina no carga en http://localhost
  -> Comprueba que el contenedor esta corriendo: docker ps
  -> Espera a ver el mensaje "Arrancando Flask y Nginx" en los logs
  -> Asegurate de que el puerto 80 no lo usa otro programa

No puedo iniciar sesion con admin / Admin1234!
  -> Espera a ver "SEED >> Usuarios creados" en los logs de Flask
  -> Si no aparece, ejecuta: docker compose down -v && docker compose up --build

Los equipos no aparecen
  -> Busca "SEED >> 10 equipos y 110 jugadores insertados" en los logs
  -> Si hay error, reinicia con: docker compose down -v && docker compose up --build

Error "port 80 already in use"
  -> Otro servicio esta usando el puerto 80
  -> Cambia el puerto en docker-compose.yml: "8080:80"
  -> Accede entonces en http://localhost:8080

Ver todos los logs del contenedor:
  docker compose logs -f


--------------------------------------------------------------------------------
NOTAS DE SEGURIDAD
--------------------------------------------------------------------------------

Esta aplicacion esta configurada para desarrollo y demostracion local.
Para un entorno de produccion se recomienda:

  - Cambiar las contrasenas por defecto (laligapass, rootpass)
  - Usar variables de entorno externas para SECRET_KEY y JWT_SECRET_KEY
  - Sustituir Flask development server por Gunicorn o uWSGI
  - Configurar HTTPS con certificado SSL en Nginx
  - No exponer el puerto de MySQL al exterior


================================================================================
  Fin del README
================================================================================

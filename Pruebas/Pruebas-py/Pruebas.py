import pytest
import os
import sys

# --- MEJORA DE RUTA ---
# Esto permite que el test encuentre 'app.py' aunque esté en carpetas distintas
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db, User, Team

# --- CONFIGURACIÓN DE LAS PRUEBAS (FIXTURES) ---
@pytest.fixture
def client():
    """Configura un cliente de pruebas con base de datos limpia"""
    app.config['TESTING'] = True
    # Usamos SQLite en memoria: Rápido y no ensucia tu PC
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['JWT_SECRET_KEY'] = 'test-secret'

    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            # Creamos un usuario admin para las pruebas de integración
            admin = User(username='admin', role='admin')
            admin.set_password('Admin1234!')
            db.session.add(admin)
            db.session.commit()
        yield client
        # Al terminar los tests, borramos todo
        with app.app_context():
            db.drop_all()

# --- PRUEBAS UNITARIAS (Lógica interna) ---

def test_password_hashing():
    """Prueba que el hash de contraseñas funciona correctamente"""
    u = User(username='tester')
    u.set_password('Laliga2025!')
    assert u.check_password('Laliga2025!') is True
    assert u.check_password('incorrecta') is False

def test_team_creation_logic():
    """Prueba que el modelo Team guarda los datos asignados"""
    t = Team(name="Betis", city="Sevilla", stadium="Benito Villamarín")
    assert t.name == "Betis"
    assert t.stadium == "Benito Villamarín"

# --- PRUEBAS DE INTEGRACIÓN (Rutas de la API) ---

def test_api_health(client):
    """Verifica que el endpoint de salud responde correctamente"""
    response = client.get('/api/health')
    assert response.status_code == 200
    assert response.json['status'] == 'ok'

def test_full_flow_admin(client):
    """
    PRUEBA DE INTEGRACIÓN COMPLETA:
    1. Login Admin
    2. Crear Equipo
    3. Listar Equipos
    """
    # 1. Login
    login_data = {"username": "admin", "password": "Admin1234!"}
    res_login = client.post('/api/auth/login', json=login_data)
    assert res_login.status_code == 200
    token = res_login.json['token']
    headers = {'Authorization': f'Bearer {token}'}

    # 2. Crear Equipo
    new_team = {"name": "Villarreal", "city": "Villarreal", "stadium": "Cerámica"}
    res_post = client.post('/api/teams', json=new_team, headers=headers)
    assert res_post.status_code == 201
    assert res_post.json['name'] == "Villarreal"

    # 3. Listar y verificar
    res_get = client.get('/api/teams', headers=headers)
    assert any(team['name'] == "Villarreal" for team in res_get.json)

def test_unauthorized_access(client):
    """Verifica que no se puede crear un equipo sin estar logueado"""
    res = client.post('/api/teams', json={"name": "Hack"})
    assert res.status_code == 401 # Unauthorized
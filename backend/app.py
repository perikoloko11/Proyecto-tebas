from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os, re, time, logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
log = logging.getLogger(__name__)

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = (
    f"mysql+pymysql://"
    f"{os.environ.get('DB_USER','laliga')}:{os.environ.get('DB_PASS','laligapass')}"
    f"@{os.environ.get('DB_HOST','db')}:{os.environ.get('DB_PORT','3306')}"
    f"/{os.environ.get('DB_NAME','laliga')}?charset=utf8mb4"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'pool_pre_ping': True, 'pool_recycle': 280}
app.config['SECRET_KEY']     = os.environ.get('SECRET_KEY',     'dev-secret-abc123')
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'dev-jwt-xyz789')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 3600

CORS(app, resources={r'/api/*': {'origins': '*'}})

db  = SQLAlchemy(app)
jwt = JWTManager(app)

# ── MODELOS ─────────────────────────────────────────────────────────────────────
class User(db.Model):
    __tablename__ = 'users'
    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role          = db.Column(db.Enum('admin', 'user'), nullable=False, default='user')

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)

class Team(db.Model):
    __tablename__ = 'teams'
    id              = db.Column(db.Integer, primary_key=True)
    name            = db.Column(db.String(100), unique=True, nullable=False)
    city            = db.Column(db.String(100))
    stadium         = db.Column(db.String(150))
    founded         = db.Column(db.SmallInteger)
    logo_emoji      = db.Column(db.String(10),  default='⚽')
    primary_color   = db.Column(db.String(7),   default='#e63946')
    secondary_color = db.Column(db.String(7),   default='#ffffff')
    players         = db.relationship('Player', backref='team', lazy=True, cascade='all, delete-orphan')

class Player(db.Model):
    __tablename__ = 'players'
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(120), nullable=False)
    position    = db.Column(db.Enum('Portero','Defensa','Centrocampista','Delantero'), nullable=False)
    number      = db.Column(db.SmallInteger)
    nationality = db.Column(db.String(80))
    age         = db.Column(db.SmallInteger)
    team_id     = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)

# ── HELPERS ──────────────────────────────────────────────────────────────────────
def clean(s, n=120):
    if not isinstance(s, str): return ''
    return re.sub(r'[<>"\']', '', s.strip())[:n]

def admin_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        u = User.query.filter_by(username=get_jwt_identity()).first()
        if not u or u.role != 'admin':
            return jsonify({'error': 'Se requiere rol administrador'}), 403
        return fn(*args, **kwargs)
    return wrapper

def team_dict(t, players=False):
    d = {'id':t.id,'name':t.name,'city':t.city,'stadium':t.stadium,
         'founded':t.founded,'logo_emoji':t.logo_emoji,
         'primary_color':t.primary_color,'secondary_color':t.secondary_color,
         'player_count':len(t.players)}
    if players:
        d['players'] = [player_dict(p) for p in sorted(t.players, key=lambda x: x.number or 99)]
    return d

def player_dict(p):
    return {'id':p.id,'name':p.name,'position':p.position,
            'number':p.number,'nationality':p.nationality,'age':p.age,'team_id':p.team_id}

# ── RUTAS ────────────────────────────────────────────────────────────────────────
@app.route('/api/health')
def health():
    return jsonify({'status': 'ok'})

@app.route('/api/auth/login', methods=['POST'])
def login():
    d = request.get_json(silent=True) or {}
    username = clean(d.get('username',''), 80)
    password = d.get('password','')
    if not username or not password:
        return jsonify({'error': 'Usuario y contraseña requeridos'}), 400
    u = User.query.filter_by(username=username).first()
    if not u or not u.check_password(password):
        return jsonify({'error': 'Credenciales incorrectas'}), 401
    return jsonify({'token': create_access_token(identity=u.username),
                    'role': u.role, 'username': u.username})

@app.route('/api/auth/me')
@jwt_required()
def me():
    u = User.query.filter_by(username=get_jwt_identity()).first()
    if not u: return jsonify({'error': 'No encontrado'}), 404
    return jsonify({'username': u.username, 'role': u.role})

@app.route('/api/teams')
def get_teams():
    return jsonify([team_dict(t) for t in Team.query.order_by(Team.name).all()])

@app.route('/api/teams/<int:tid>')
def get_team(tid):
    return jsonify(team_dict(Team.query.get_or_404(tid), players=True))

@app.route('/api/teams', methods=['POST'])
@admin_required
def create_team():
    d = request.get_json(silent=True) or {}
    name = clean(d.get('name',''))
    if not name: return jsonify({'error': 'Nombre requerido'}), 400
    if Team.query.filter_by(name=name).first(): return jsonify({'error': 'Ya existe'}), 409
    t = Team(name=name, city=clean(d.get('city','')), stadium=clean(d.get('stadium','')),
             founded=d.get('founded'), logo_emoji=(d.get('logo_emoji') or '⚽')[:5],
             primary_color=(d.get('primary_color') or '#e63946')[:7],
             secondary_color=(d.get('secondary_color') or '#ffffff')[:7])
    db.session.add(t); db.session.commit()
    return jsonify(team_dict(t)), 201

@app.route('/api/teams/<int:tid>', methods=['PUT'])
@admin_required
def update_team(tid):
    t = Team.query.get_or_404(tid)
    d = request.get_json(silent=True) or {}
    if 'name' in d:            t.name            = clean(d['name'])
    if 'city' in d:            t.city            = clean(d['city'])
    if 'stadium' in d:         t.stadium         = clean(d['stadium'])
    if 'founded' in d:         t.founded         = d['founded']
    if 'logo_emoji' in d:      t.logo_emoji      = (d['logo_emoji'] or '⚽')[:5]
    if 'primary_color' in d:   t.primary_color   = (d['primary_color'] or '#e63946')[:7]
    if 'secondary_color' in d: t.secondary_color = (d['secondary_color'] or '#ffffff')[:7]
    db.session.commit()
    return jsonify(team_dict(t))

@app.route('/api/teams/<int:tid>', methods=['DELETE'])
@admin_required
def delete_team(tid):
    t = Team.query.get_or_404(tid)
    db.session.delete(t); db.session.commit()
    return jsonify({'message': 'Equipo eliminado'})

@app.route('/api/players', methods=['POST'])
@admin_required
def create_player():
    d = request.get_json(silent=True) or {}
    if not d.get('name') or not d.get('team_id') or not d.get('position'):
        return jsonify({'error': 'name, team_id y position son requeridos'}), 400
    if not Team.query.get(d['team_id']): return jsonify({'error': 'Equipo no encontrado'}), 404
    p = Player(name=clean(d['name']), position=d['position'],
               number=d.get('number'), nationality=clean(d.get('nationality','')),
               age=d.get('age'), team_id=d['team_id'])
    db.session.add(p); db.session.commit()
    return jsonify(player_dict(p)), 201

@app.route('/api/players/<int:pid>', methods=['PUT'])
@admin_required
def update_player(pid):
    p = Player.query.get_or_404(pid)
    d = request.get_json(silent=True) or {}
    if 'name' in d:        p.name        = clean(d['name'])
    if 'position' in d:    p.position    = d['position']
    if 'number' in d:      p.number      = d['number']
    if 'nationality' in d: p.nationality = clean(d['nationality'])
    if 'age' in d:         p.age         = d['age']
    db.session.commit()
    return jsonify(player_dict(p))

@app.route('/api/players/<int:pid>', methods=['DELETE'])
@admin_required
def delete_player(pid):
    p = Player.query.get_or_404(pid)
    db.session.delete(p); db.session.commit()
    return jsonify({'message': 'Jugador eliminado'})

# ── DATOS INICIALES ───────────────────────────────────────────────────────────────
TEAMS_SEED = [
    {'name':'Real Madrid','city':'Madrid','stadium':'Santiago Bernabeu','founded':1902,'logo_emoji':'👑','primary_color':'#FEBE10','secondary_color':'#FFFFFF','players':[
        {'name':'Thibaut Courtois','position':'Portero','number':1,'nationality':'Belga','age':32},
        {'name':'Dani Carvajal','position':'Defensa','number':2,'nationality':'Espanol','age':32},
        {'name':'Eder Militao','position':'Defensa','number':3,'nationality':'Brasileno','age':26},
        {'name':'David Alaba','position':'Defensa','number':4,'nationality':'Austriaco','age':32},
        {'name':'Ferland Mendy','position':'Defensa','number':23,'nationality':'Frances','age':29},
        {'name':'Aurelien Tchouameni','position':'Centrocampista','number':18,'nationality':'Frances','age':24},
        {'name':'Toni Kroos','position':'Centrocampista','number':8,'nationality':'Aleman','age':34},
        {'name':'Luka Modric','position':'Centrocampista','number':10,'nationality':'Croata','age':38},
        {'name':'Vinicius Jr','position':'Delantero','number':7,'nationality':'Brasileno','age':23},
        {'name':'Rodrygo','position':'Delantero','number':11,'nationality':'Brasileno','age':23},
        {'name':'Kylian Mbappe','position':'Delantero','number':9,'nationality':'Frances','age':25},
    ]},
    {'name':'FC Barcelona','city':'Barcelona','stadium':'Spotify Camp Nou','founded':1899,'logo_emoji':'🔵','primary_color':'#A50044','secondary_color':'#004D98','players':[
        {'name':'Marc-Andre ter Stegen','position':'Portero','number':1,'nationality':'Aleman','age':32},
        {'name':'Jules Kounde','position':'Defensa','number':23,'nationality':'Frances','age':25},
        {'name':'Ronald Araujo','position':'Defensa','number':4,'nationality':'Uruguayo','age':25},
        {'name':'Pau Cubarsi','position':'Defensa','number':33,'nationality':'Espanol','age':17},
        {'name':'Alejandro Balde','position':'Defensa','number':3,'nationality':'Espanol','age':20},
        {'name':'Pedri','position':'Centrocampista','number':8,'nationality':'Espanol','age':21},
        {'name':'Frenkie de Jong','position':'Centrocampista','number':21,'nationality':'Nerlandes','age':26},
        {'name':'Gavi','position':'Centrocampista','number':6,'nationality':'Espanol','age':19},
        {'name':'Lamine Yamal','position':'Delantero','number':27,'nationality':'Espanol','age':16},
        {'name':'Robert Lewandowski','position':'Delantero','number':9,'nationality':'Polaco','age':35},
        {'name':'Raphinha','position':'Delantero','number':11,'nationality':'Brasileno','age':27},
    ]},
    {'name':'Atletico Madrid','city':'Madrid','stadium':'Civitas Metropolitano','founded':1903,'logo_emoji':'🔴','primary_color':'#CE3524','secondary_color':'#FFFFFF','players':[
        {'name':'Jan Oblak','position':'Portero','number':13,'nationality':'Esloveno','age':31},
        {'name':'Nahuel Molina','position':'Defensa','number':16,'nationality':'Argentino','age':26},
        {'name':'Jose M. Gimenez','position':'Defensa','number':2,'nationality':'Uruguayo','age':29},
        {'name':'Axel Witsel','position':'Defensa','number':20,'nationality':'Belga','age':35},
        {'name':'Reinildo','position':'Defensa','number':6,'nationality':'Mozambiqueno','age':30},
        {'name':'Rodrigo De Paul','position':'Centrocampista','number':5,'nationality':'Argentino','age':30},
        {'name':'Koke','position':'Centrocampista','number':8,'nationality':'Espanol','age':32},
        {'name':'Pablo Barrios','position':'Centrocampista','number':29,'nationality':'Espanol','age':21},
        {'name':'Samuel Lino','position':'Delantero','number':17,'nationality':'Portugues','age':24},
        {'name':'Antoine Griezmann','position':'Delantero','number':7,'nationality':'Frances','age':33},
        {'name':'Alvaro Morata','position':'Delantero','number':9,'nationality':'Espanol','age':31},
    ]},
    {'name':'Sevilla FC','city':'Sevilla','stadium':'Ramon Sanchez-Pizjuan','founded':1890,'logo_emoji':'⚪','primary_color':'#D40000','secondary_color':'#FFFFFF','players':[
        {'name':'Orjan Nyland','position':'Portero','number':13,'nationality':'Noruego','age':33},
        {'name':'Jesus Navas','position':'Defensa','number':16,'nationality':'Espanol','age':38},
        {'name':'Loic Bade','position':'Defensa','number':23,'nationality':'Frances','age':24},
        {'name':'Sergio Ramos','position':'Defensa','number':4,'nationality':'Espanol','age':38},
        {'name':'Marcos Acuna','position':'Defensa','number':19,'nationality':'Argentino','age':32},
        {'name':'Joan Jordan','position':'Centrocampista','number':8,'nationality':'Espanol','age':30},
        {'name':'Lucas Ocampos','position':'Centrocampista','number':5,'nationality':'Argentino','age':30},
        {'name':'Oliver Torres','position':'Centrocampista','number':21,'nationality':'Espanol','age':29},
        {'name':'Suso','position':'Delantero','number':7,'nationality':'Espanol','age':30},
        {'name':'En-Nesyri','position':'Delantero','number':15,'nationality':'Marroqui','age':27},
        {'name':'Lukebekio','position':'Delantero','number':11,'nationality':'Belga','age':26},
    ]},
    {'name':'Real Betis','city':'Sevilla','stadium':'Benito Villamarin','founded':1907,'logo_emoji':'💚','primary_color':'#00A850','secondary_color':'#FFFFFF','players':[
        {'name':'Rui Silva','position':'Portero','number':13,'nationality':'Portugues','age':30},
        {'name':'Hector Bellerin','position':'Defensa','number':22,'nationality':'Espanol','age':29},
        {'name':'German Pezzella','position':'Defensa','number':5,'nationality':'Argentino','age':33},
        {'name':'Marc Bartra','position':'Defensa','number':15,'nationality':'Espanol','age':33},
        {'name':'Ricardo Rodriguez','position':'Defensa','number':3,'nationality':'Suizo','age':31},
        {'name':'Guido Rodriguez','position':'Centrocampista','number':17,'nationality':'Argentino','age':30},
        {'name':'Isco','position':'Centrocampista','number':10,'nationality':'Espanol','age':32},
        {'name':'Sergio Canales','position':'Centrocampista','number':8,'nationality':'Espanol','age':33},
        {'name':'Antony','position':'Delantero','number':7,'nationality':'Brasileno','age':24},
        {'name':'Ayoze Perez','position':'Delantero','number':19,'nationality':'Espanol','age':30},
        {'name':'Vitor Roque','position':'Delantero','number':9,'nationality':'Brasileno','age':19},
    ]},
    {'name':'Valencia CF','city':'Valencia','stadium':'Mestalla','founded':1919,'logo_emoji':'🦇','primary_color':'#FF7A00','secondary_color':'#000000','players':[
        {'name':'Giorgi Mamardashvili','position':'Portero','number':1,'nationality':'Georgiano','age':23},
        {'name':'Thierry Correia','position':'Defensa','number':2,'nationality':'Portugues','age':24},
        {'name':'Cristhian Mosquera','position':'Defensa','number':5,'nationality':'Espanol','age':21},
        {'name':'Cesar Tarrega','position':'Defensa','number':4,'nationality':'Espanol','age':22},
        {'name':'Jose Gaya','position':'Defensa','number':14,'nationality':'Espanol','age':29},
        {'name':'Pepelu','position':'Centrocampista','number':8,'nationality':'Espanol','age':24},
        {'name':'Javi Guerra','position':'Centrocampista','number':16,'nationality':'Espanol','age':22},
        {'name':'Andre Almeida','position':'Centrocampista','number':18,'nationality':'Portugues','age':25},
        {'name':'Dani Gomez','position':'Delantero','number':11,'nationality':'Espanol','age':26},
        {'name':'Hugo Duro','position':'Delantero','number':9,'nationality':'Espanol','age':24},
        {'name':'Rafa Mir','position':'Delantero','number':19,'nationality':'Espanol','age':26},
    ]},
    {'name':'Villarreal CF','city':'Villarreal','stadium':'Estadio de la Ceramica','founded':1923,'logo_emoji':'🟡','primary_color':'#FFE000','secondary_color':'#005F87','players':[
        {'name':'Filip Jorgensen','position':'Portero','number':1,'nationality':'Danes','age':22},
        {'name':'Juan Foyth','position':'Defensa','number':2,'nationality':'Argentino','age':26},
        {'name':'Pau Torres','position':'Defensa','number':5,'nationality':'Espanol','age':27},
        {'name':'Raul Albiol','position':'Defensa','number':3,'nationality':'Espanol','age':38},
        {'name':'Alberto Moreno','position':'Defensa','number':18,'nationality':'Espanol','age':32},
        {'name':'Dani Parejo','position':'Centrocampista','number':10,'nationality':'Espanol','age':35},
        {'name':'Etienne Capoue','position':'Centrocampista','number':8,'nationality':'Frances','age':36},
        {'name':'Alex Baena','position':'Centrocampista','number':19,'nationality':'Espanol','age':22},
        {'name':'Yeremi Pino','position':'Delantero','number':11,'nationality':'Espanol','age':21},
        {'name':'Gerard Moreno','position':'Delantero','number':7,'nationality':'Espanol','age':32},
        {'name':'Samu Chukwueze','position':'Delantero','number':17,'nationality':'Nigeriano','age':25},
    ]},
    {'name':'Athletic Club','city':'Bilbao','stadium':'San Mames','founded':1898,'logo_emoji':'🦁','primary_color':'#EE2523','secondary_color':'#FFFFFF','players':[
        {'name':'Unai Simon','position':'Portero','number':1,'nationality':'Espanol','age':27},
        {'name':'Oscar de Marcos','position':'Defensa','number':2,'nationality':'Espanol','age':35},
        {'name':'Dani Vivian','position':'Defensa','number':5,'nationality':'Espanol','age':24},
        {'name':'Yeray Alvarez','position':'Defensa','number':3,'nationality':'Espanol','age':28},
        {'name':'Yuri Berchiche','position':'Defensa','number':18,'nationality':'Espanol','age':33},
        {'name':'Oihan Sancet','position':'Centrocampista','number':8,'nationality':'Espanol','age':22},
        {'name':'Mikel Vesga','position':'Centrocampista','number':14,'nationality':'Espanol','age':31},
        {'name':'Iker Muniain','position':'Centrocampista','number':10,'nationality':'Espanol','age':31},
        {'name':'Inaki Williams','position':'Delantero','number':11,'nationality':'Espanol','age':29},
        {'name':'Gorka Guruzeta','position':'Delantero','number':9,'nationality':'Espanol','age':27},
        {'name':'Nico Williams','position':'Delantero','number':17,'nationality':'Espanol','age':22},
    ]},
    {'name':'Real Sociedad','city':'San Sebastian','stadium':'Reale Arena','founded':1909,'logo_emoji':'🔷','primary_color':'#003DA5','secondary_color':'#FFFFFF','players':[
        {'name':'Alex Remiro','position':'Portero','number':1,'nationality':'Espanol','age':28},
        {'name':'Hamari Traore','position':'Defensa','number':2,'nationality':'Malies','age':32},
        {'name':'Robin Le Normand','position':'Defensa','number':5,'nationality':'Espanol','age':27},
        {'name':'Aritz Elustondo','position':'Defensa','number':3,'nationality':'Espanol','age':33},
        {'name':'Aihen Munoz','position':'Defensa','number':18,'nationality':'Espanol','age':26},
        {'name':'Martin Zubimendi','position':'Centrocampista','number':4,'nationality':'Espanol','age':25},
        {'name':'Mikel Merino','position':'Centrocampista','number':8,'nationality':'Espanol','age':28},
        {'name':'Brais Mendez','position':'Centrocampista','number':19,'nationality':'Espanol','age':27},
        {'name':'Takefusa Kubo','position':'Delantero','number':11,'nationality':'Japones','age':23},
        {'name':'Mikel Oyarzabal','position':'Delantero','number':10,'nationality':'Espanol','age':27},
        {'name':'Sheraldo Becker','position':'Delantero','number':17,'nationality':'Surinames','age':29},
    ]},
    {'name':'Girona FC','city':'Girona','stadium':'Estadio Montilivi','founded':1930,'logo_emoji':'🏟','primary_color':'#CF0E2B','secondary_color':'#FFFFFF','players':[
        {'name':'Paulo Gazzaniga','position':'Portero','number':1,'nationality':'Argentino','age':32},
        {'name':'Yan Couto','position':'Defensa','number':2,'nationality':'Brasileno','age':22},
        {'name':'David Lopez','position':'Defensa','number':5,'nationality':'Espanol','age':33},
        {'name':'Eric Garcia','position':'Defensa','number':3,'nationality':'Espanol','age':23},
        {'name':'Miguel Gutierrez','position':'Defensa','number':28,'nationality':'Espanol','age':22},
        {'name':'Aleix Garcia','position':'Centrocampista','number':4,'nationality':'Espanol','age':26},
        {'name':'Viktor Tsygankov','position':'Centrocampista','number':11,'nationality':'Ucraniano','age':26},
        {'name':'Oriol Romeu','position':'Centrocampista','number':8,'nationality':'Espanol','age':32},
        {'name':'Savinho','position':'Delantero','number':17,'nationality':'Brasileno','age':20},
        {'name':'Artem Dovbyk','position':'Delantero','number':9,'nationality':'Ucraniano','age':27},
        {'name':'Portu','position':'Delantero','number':14,'nationality':'Espanol','age':31},
    ]},
]

def seed():
    try:
        # Usuarios
        if User.query.count() == 0:
            a = User(username='admin',   role='admin'); a.set_password('Admin1234!')
            u = User(username='usuario', role='user');  u.set_password('User1234!')
            db.session.add_all([a, u])
            db.session.commit()
            log.info('SEED >> Usuarios creados: admin / usuario')
        else:
            log.info('SEED >> Usuarios ya existen')

        # Equipos y jugadores
        if Team.query.count() == 0:
            for td in TEAMS_SEED:
                players_info = td.pop('players')
                t = Team(**td)
                db.session.add(t)
                db.session.flush()
                for pd in players_info:
                    db.session.add(Player(team_id=t.id, **pd))
                td['players'] = players_info  # restaurar por si acaso
            db.session.commit()
            log.info('SEED >> 10 equipos y 110 jugadores insertados')
        else:
            log.info('SEED >> Equipos ya existen')

    except Exception as e:
        db.session.rollback()
        log.error(f'SEED ERROR: {e}')
        raise

# ── ARRANQUE ─────────────────────────────────────────────────────────────────────
def wait_for_db(retries=20, delay=3):
    for i in range(retries):
        try:
            with app.app_context():
                db.engine.connect().close()
            log.info('DB >> MySQL conectado OK')
            return True
        except Exception as e:
            log.warning(f'DB >> Esperando MySQL ({i+1}/{retries}): {e}')
            time.sleep(delay)
    log.error('DB >> No se pudo conectar a MySQL')
    return False

if __name__ == '__main__':
    if wait_for_db():
        with app.app_context():
            db.create_all()   # crea tablas si no existen
            seed()            # inserta datos si no existen
    app.run(host='0.0.0.0', port=5001, debug=False)

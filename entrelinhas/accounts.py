"""Optional local accounts. Sessions never expose password hashes to the UI."""
import hashlib
import hmac
import re
import secrets
import sqlite3
import time
import uuid
from contextlib import contextmanager
from http.cookies import SimpleCookie
from pathlib import Path

from analyzer import MaterialError

SESSION_AGE = 7 * 24 * 3600

class Accounts:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,name TEXT NOT NULL,email TEXT UNIQUE NOT NULL,salt TEXT NOT NULL,password_hash TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY,user_id TEXT NOT NULL,expires REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS attempts(key TEXT PRIMARY KEY,count INTEGER NOT NULL,started REAL NOT NULL);
            ''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def digest(password, salt):
        return hashlib.scrypt(password.encode('utf-8'), salt=bytes.fromhex(salt), n=32768, r=8, p=3, maxmem=64*1024*1024).hex()

    @staticmethod
    def email(value):
        if not isinstance(value, str) or len(value) > 254 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', value.strip()):
            raise MaterialError('Informe um e-mail válido.')
        return value.strip().lower()

    @staticmethod
    def password(value):
        if not isinstance(value, str) or not 8 <= len(value) <= 128:
            raise MaterialError('Use uma senha de 8 a 128 caracteres.')
        return value

    def throttle(self, key):
        now = time.time()
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM attempts WHERE key=?', (key,)).fetchone()
            if row and now-row['started'] < 600 and row['count'] >= 12:
                raise MaterialError('Muitas tentativas. Aguarde alguns minutos e tente novamente.')
            count = row['count']+1 if row and now-row['started'] < 600 else 1
            start = row['started'] if row and now-row['started'] < 600 else now
            db.execute('INSERT OR REPLACE INTO attempts VALUES(?,?,?)', (key, count, start))

    def register(self, body, address):
        self.throttle('register:'+address)
        email = self.email(body.get('email'))
        password = self.password(body.get('password'))
        name = body.get('name', '')
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 60:
            raise MaterialError('Informe seu nome, com até 60 caracteres.')
        user = {'id': uuid.uuid4().hex, 'name': name.strip(), 'email': email}
        salt = secrets.token_hex(16)
        digest = self.digest(password, salt)
        try:
            with self.connect() as db:
                db.execute('INSERT INTO users VALUES(?,?,?,?,?)', (user['id'], user['name'], email, salt, digest))
        except sqlite3.IntegrityError:
            raise MaterialError('Não foi possível criar a conta com esse e-mail. Se já tiver conta, entre.')
        return user, self.session(user['id'])

    def login(self, body, address):
        email = self.email(body.get('email'))
        self.throttle('login-address:'+address)
        self.throttle('login:'+hashlib.sha256(email.encode()).hexdigest())
        password = body.get('password')
        if not isinstance(password, str) or len(password) > 128:
            raise MaterialError('E-mail ou senha incorretos.')
        with self.connect() as db:
            row = db.execute('SELECT * FROM users WHERE email=?', (email,)).fetchone()
        candidate = self.digest(password, row['salt'] if row else '00'*16)
        if not row or not hmac.compare_digest(candidate, row['password_hash']):
            raise MaterialError('E-mail ou senha incorretos.')
        with self.connect() as db:
            db.execute('DELETE FROM attempts WHERE key=?', ('login:'+hashlib.sha256(email.encode()).hexdigest(),))
        user = {key: row[key] for key in ('id', 'name', 'email')}
        return user, self.session(user['id'])

    def session(self, user_id):
        token = secrets.token_urlsafe(32)
        with self.connect() as db:
            db.execute('DELETE FROM sessions WHERE expires<?', (time.time(),))
            db.execute('INSERT INTO sessions VALUES(?,?,?)', (hashlib.sha256(token.encode()).hexdigest(), user_id, time.time()+SESSION_AGE))
        return token

    @staticmethod
    def token(cookie):
        parsed = SimpleCookie()
        try:
            parsed.load(cookie or '')
            return parsed['entrelinhas_session'].value if 'entrelinhas_session' in parsed else ''
        except Exception:
            return ''

    def user(self, cookie):
        token = self.token(cookie)
        if not token or len(token) > 100:
            return None
        with self.connect() as db:
            row = db.execute('SELECT users.id,name,email FROM sessions JOIN users ON users.id=sessions.user_id WHERE token_hash=? AND expires>?', (hashlib.sha256(token.encode()).hexdigest(), time.time())).fetchone()
        return dict(row) if row else None

    def logout(self, cookie):
        with self.connect() as db:
            db.execute('DELETE FROM sessions WHERE token_hash=?', (hashlib.sha256(self.token(cookie).encode()).hexdigest(),))

    @staticmethod
    def cookie(token):
        return 'entrelinhas_session='+token+'; Path=/; HttpOnly; SameSite=Strict; Max-Age='+str(SESSION_AGE if token else 0)

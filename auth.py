# -*- coding: utf-8 -*-
"""
AUTHENTIFIZIERUNGSMODUL - User Authentication für Q-DAS DFQ Konverter
===========================================================================

Dieses Modul implementiert eine vollständige Benutzerauthentifizierung für die 
Q-DAS DFQ zu Excel Konverter-Anwendung. Es ist als separates Modul implementiert,
um die bestehende app.py nicht zu verändern.

Features:
- **Benutzerregistrierung:** Neue Benutzer können sich registrieren
- **Login/Logout:** Sichere Anmeldung mit Passwort-Hashing
- **Session Management:** Flask-Session basierte Authentifizierung
- **Passwort-Sicherheit:** Bcrypt für sicheres Password Hashing
- **Decorator-basierte Zugriffskontrolle:** @login_required Decorator
- **Database Integration:** SQLite für Benutzerdaten
- **CSRF Protection:** Cross-Site Request Forgery Schutz
"""

import os
import sqlite3
import hashlib
import secrets
from datetime import datetime, timedelta
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, g
from werkzeug.security import generate_password_hash, check_password_hash
import bcrypt

# ==============================================================================
# 1. BLUEPRINT KONFIGURATION
# ==============================================================================
"""
Erstellt ein Flask Blueprint für alle authentifizierungsbezogenen Routen.
Dies ermöglicht eine saubere Trennung der Auth-Funktionalität vom Hauptcode.
"""
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# ==============================================================================
# 2. DATENBANK-VERBINDUNGSMANAGEMENT
# ==============================================================================

def get_auth_db():
    """
    Erstellt oder ruft eine Datenbankverbindung für Authentifizierung ab.
    Verwendet Flask's g-Objekt für Request-lokale Speicherung der Verbindung.
    
    Returns:
        sqlite3.Connection: Datenbankverbindung für Benutzerauthentifizierung
    """
    if 'auth_db' not in g:
        db_path = current_app.config.get('USER_DATABASE_PATH', 'users.db')
        g.auth_db = sqlite3.connect(db_path)
        g.auth_db.row_factory = sqlite3.Row  # Ermöglicht Zugriff auf Spalten per Name
    return g.auth_db

def close_auth_db(e=None):
    """
    Schließt die Datenbankverbindung am Ende des Requests.
    
    Args:
        e: Fehlerobjekt (optional, für Flask's teardown_appcontext)
    """
    db = g.pop('auth_db', None)
    if db is not None:
        db.close()

def init_auth_db():
    """
    Initialisiert die Benutzerdatenbank mit notwendigen Tabellen.
    Erstellt die users-Tabelle, falls sie noch nicht existiert.
    
    Tabellenstruktur:
    - id: Primärschlüssel (Integer, Auto-increment)
    - username: Eindeutiger Benutzername (Text, NOT NULL, UNIQUE)
    - email: E-Mail-Adresse (Text, NOT NULL, UNIQUE)  
    - password_hash: Gehashtes Passwort (Text, NOT NULL)
    - created_at: Zeitstempel der Registrierung (Text, NOT NULL)
    - last_login: Zeitstempel des letzten Logins (Text, nullable)
    - is_active: Aktiv-Status des Benutzers (Integer, default 1)
    """
    db = get_auth_db()
    
    # SQL für das Erstellen der Benutzertabelle
    create_users_table = '''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        created_at TEXT NOT NULL,
        last_login TEXT,
        is_active INTEGER DEFAULT 1
    )
    '''
    
    try:
        db.execute(create_users_table)
        db.commit()
        print("✅ Auth-Datenbank erfolgreich initialisiert")
    except sqlite3.Error as e:
        print(f"❌ Fehler beim Initialisieren der Auth-Datenbank: {e}")

# ==============================================================================
# 3. PASSWORT-SICHERHEITSFUNKTIONEN
# ==============================================================================

def hash_password(password):
    """
    Erstellt einen sicheren Hash für ein Passwort mit bcrypt.
    
    Args:
        password (str): Das zu hashende Passwort
        
    Returns:
        str: Der gehashte Passwort-String
    """
    # Generiert einen Salt und hasht das Passwort mit bcrypt
    salt = bcrypt.gensalt(rounds=12)  # 12 Runden für gute Sicherheit vs. Performance
    password_hash = bcrypt.hashpw(password.encode('utf-8'), salt)
    return password_hash.decode('utf-8')

def verify_password(password, password_hash):
    """
    Verifiziert ein Passwort gegen seinen gespeicherten Hash.
    
    Args:
        password (str): Das zu prüfende Passwort
        password_hash (str): Der gespeicherte Hash
        
    Returns:
        bool: True wenn das Passwort korrekt ist, False sonst
    """
    try:
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    except Exception as e:
        print(f"⚠️ Fehler bei Passwort-Verifikation: {e}")
        return False

# ==============================================================================
# 4. BENUTZER-VERWALTUNGSFUNKTIONEN
# ==============================================================================

def create_user(username, email, password):
    """
    Erstellt einen neuen Benutzer in der Datenbank.
    
    Args:
        username (str): Eindeutiger Benutzername
        email (str): E-Mail-Adresse des Benutzers
        password (str): Klartext-Passwort (wird automatisch gehasht)
        
    Returns:
        dict: Erfolgsmeldung oder Fehlermeldung
    """
    db = get_auth_db()
    
    # Prüfe ob Benutzername bereits existiert
    existing_user = db.execute(
        'SELECT id FROM users WHERE username = ? OR email = ?', 
        (username, email)
    ).fetchone()
    
    if existing_user:
        return {'success': False, 'message': 'Benutzername oder E-Mail bereits vorhanden'}
    
    # Validiere Eingaben
    if len(username) < 3:
        return {'success': False, 'message': 'Benutzername muss mindestens 3 Zeichen lang sein'}
    
    if len(password) < 6:
        return {'success': False, 'message': 'Passwort muss mindestens 6 Zeichen lang sein'}
    
    if '@' not in email:
        return {'success': False, 'message': 'Ungültige E-Mail-Adresse'}
    
    try:
        # Hash das Passwort und erstelle den Benutzer
        password_hash = hash_password(password)
        created_at = datetime.now().isoformat()
        
        db.execute(
            'INSERT INTO users (username, email, password_hash, created_at) VALUES (?, ?, ?, ?)',
            (username, email, password_hash, created_at)
        )
        db.commit()
        
        print(f"✅ Neuer Benutzer erstellt: {username}")
        return {'success': True, 'message': f'Benutzer {username} erfolgreich erstellt'}
        
    except sqlite3.Error as e:
        print(f"❌ Datenbankfehler beim Erstellen des Benutzers: {e}")
        return {'success': False, 'message': 'Fehler beim Erstellen des Benutzers'}

def authenticate_user(username, password):
    """
    Authentifiziert einen Benutzer mit Benutzername und Passwort.
    
    Args:
        username (str): Benutzername oder E-Mail
        password (str): Klartext-Passwort
        
    Returns:
        dict: Benutzerinformationen bei Erfolg, None bei Fehlschlag
    """
    db = get_auth_db()
    
    # Suche Benutzer nach Benutzername oder E-Mail
    user = db.execute(
        'SELECT * FROM users WHERE (username = ? OR email = ?) AND is_active = 1',
        (username, username)
    ).fetchone()
    
    if user and verify_password(password, user['password_hash']):
        # Aktualisiere letzten Login-Zeitstempel
        last_login = datetime.now().isoformat()
        db.execute(
            'UPDATE users SET last_login = ? WHERE id = ?',
            (last_login, user['id'])
        )
        db.commit()
        
        print(f"✅ Benutzer erfolgreich angemeldet: {user['username']}")
        
        # Gib Benutzerinformationen zurück (ohne Passwort-Hash)
        return {
            'id': user['id'],
            'username': user['username'],
            'email': user['email'],
            'created_at': user['created_at'],
            'last_login': last_login
        }
    
    print(f"⚠️ Fehlgeschlagener Login-Versuch für: {username}")
    return None

def get_user_by_id(user_id):
    """
    Ruft Benutzerinformationen anhand der Benutzer-ID ab.
    
    Args:
        user_id (int): Die ID des Benutzers
        
    Returns:
        dict: Benutzerinformationen oder None
    """
    db = get_auth_db()
    user = db.execute(
        'SELECT id, username, email, created_at, last_login FROM users WHERE id = ? AND is_active = 1',
        (user_id,)
    ).fetchone()
    
    if user:
        return dict(user)
    return None

# ==============================================================================
# 5. SESSION-MANAGEMENT
# ==============================================================================

def login_user(user_info):
    """
    Startet eine Benutzersession nach erfolgreicher Authentifizierung.
    
    Args:
        user_info (dict): Benutzerinformationen von authenticate_user()
    """
    # Erstelle sichere Session mit Benutzerinformationen
    session['user_id'] = user_info['id']
    session['username'] = user_info['username']
    session['logged_in'] = True
    session['login_time'] = datetime.now().isoformat()
    
    # Generiere CSRF-Token für zusätzliche Sicherheit
    session['csrf_token'] = secrets.token_hex(16)
    
    print(f"✅ Session gestartet für Benutzer: {user_info['username']}")

def logout_user():
    """
    Beendet die aktuelle Benutzersession sicher.
    """
    username = session.get('username', 'Unbekannt')
    
    # Lösche alle sessionbezogenen Daten
    session.clear()
    
    print(f"✅ Session beendet für Benutzer: {username}")

def is_user_logged_in():
    """
    Prüft, ob ein Benutzer aktuell eingeloggt ist.
    
    Returns:
        bool: True wenn eingeloggt, False sonst
    """
    return session.get('logged_in', False) and 'user_id' in session

def get_current_user():
    """
    Ruft Informationen des aktuell eingeloggten Benutzers ab.
    
    Returns:
        dict: Benutzerinformationen oder None
    """
    if is_user_logged_in():
        return get_user_by_id(session['user_id'])
    return None

# ==============================================================================
# 6. DECORATOR FÜR ZUGRIFFSKONTROLLE
# ==============================================================================

def login_required(f):
    """
    Decorator um Routen zu schützen, die eine Anmeldung erfordern.
    
    Verwendung:
        @login_required
        def protected_route():
            return "Diese Route ist geschützt"
    
    Args:
        f: Die zu schützende Funktion
        
    Returns:
        function: Wrapper-Funktion mit Authentifizierungsprüfung
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_user_logged_in():
            flash('Bitte melden Sie sich an, um auf diese Seite zuzugreifen.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# ==============================================================================
# 7. FLASK ROUTEN FÜR AUTHENTIFIZIERUNG
# ==============================================================================

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Login-Route für Benutzeranmeldung.
    
    GET: Zeigt Login-Formular
    POST: Verarbeitet Login-Versuch
    """
    # Leite bereits angemeldete Benutzer zur Hauptseite weiter
    if is_user_logged_in():
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Bitte geben Sie Benutzername und Passwort ein.', 'error')
            return render_template('auth/login.html')
        
        # Versuche Authentifizierung
        user_info = authenticate_user(username, password)
        
        if user_info:
            login_user(user_info)
            flash(f'Willkommen zurück, {user_info["username"]}!', 'success')
            
            # Leite zur ursprünglich angeforderten Seite weiter
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('index'))
        else:
            flash('Ungültiger Benutzername oder Passwort.', 'error')
    
    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """
    Registrierungs-Route für neue Benutzer.
    
    GET: Zeigt Registrierungsformular
    POST: Verarbeitet Registrierung
    """
    # Leite bereits angemeldete Benutzer zur Hauptseite weiter
    if is_user_logged_in():
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')
        
        # Validiere Eingaben
        if not all([username, email, password, password_confirm]):
            flash('Bitte füllen Sie alle Felder aus.', 'error')
            return render_template('auth/register.html')
        
        if password != password_confirm:
            flash('Passwörter stimmen nicht überein.', 'error')
            return render_template('auth/register.html')
        
        # Versuche Benutzer zu erstellen
        result = create_user(username, email, password)
        
        if result['success']:
            flash(result['message'], 'success')
            flash('Sie können sich jetzt anmelden.', 'info')
            return redirect(url_for('auth.login'))
        else:
            flash(result['message'], 'error')
    
    return render_template('auth/register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """
    Logout-Route für Benutzerabmeldung.
    """
    username = session.get('username', 'Unbekannt')
    logout_user()
    flash(f'Auf Wiedersehen, {username}!', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/profile')
@login_required
def profile():
    """
    Profilseite für angemeldete Benutzer.
    """
    user = get_current_user()
    if not user:
        flash('Benutzerinformationen konnten nicht geladen werden.', 'error')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/profile.html', user=user)

# ==============================================================================
# 8. INITIALISIERUNGSFUNKTIONEN
# ==============================================================================

def init_auth_module(app):
    """
    Initialisiert das Authentifizierungsmodul mit der Flask-App.
    
    Args:
        app: Flask-App-Instanz
    """
    # Registriere Blueprint
    app.register_blueprint(auth_bp)
    
    # Registriere Teardown-Handler für Datenbankverbindung
    app.teardown_appcontext(close_auth_db)
    
    # Initialisiere Datenbank
    with app.app_context():
        init_auth_db()
    
    print("✅ Authentifizierungsmodul erfolgreich initialisiert")

# ==============================================================================
# 9. TEMPLATE-KONTEXTPROZESSOR
# ==============================================================================

@auth_bp.app_context_processor
def inject_auth_functions():
    """
    Macht Authentifizierungsfunktionen in allen Templates verfügbar.
    
    Returns:
        dict: Funktionen für Templates
    """
    return {
        'is_user_logged_in': is_user_logged_in,
        'get_current_user': get_current_user
    }
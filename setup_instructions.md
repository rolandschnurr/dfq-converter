# Q-DAS DFQ Converter - User Authentication Setup

## 📋 Übersicht

Ich habe dein Q-DAS DFQ Converter Python-Programm um eine vollständige User Authentication erweitert. Hier ist, was hinzugefügt wurde:

## 🆕 Neue Features

### 🔐 User Authentication
- **Sichere Benutzeranmeldung** mit Flask-Login
- **Passwort-Hashing** mit PBKDF2-SHA256
- **Session Management** mit CSRF-Schutz
- **User Registration** für neue Benutzer
- **Protected Routes** - nur angemeldete Benutzer können Dateien konvertieren

### 🚀 Render.com Ready
- **Optimiert für Render Deployment**
- **Environment Variables** Konfiguration
- **Automatische SSL/HTTPS** Unterstützung
- **Persistent Database** Option

## 📁 Neue Dateien

### 1. **auth.py** - Authentication Module
- User Model mit Flask-Login
- SQLite Database Manager
- Sichere Passwort-Funktionen
- Session-Konfiguration

### 2. **Erweiterte app.py**
- Integrierte Authentication Routes (`/login`, `/register`, `/logout`)
- Geschützte Upload-Route
- User-spezifische Datei-Isolation
- Error Handling

### 3. **Templates**
- `templates/auth/login.html` - Login-Seite
- `templates/auth/register.html` - Registrierung
- Erweiterte `templates/index.html` mit User-Info

### 4. **Konfiguration**
- `requirements.txt` - Erweiterte Dependencies
- `render.yaml` - Render Deployment Config
- `.env.template` - Environment Variables Template
- `DEPLOYMENT.md` - Detaillierte Deployment-Anleitung

## 🔧 Installation & Setup

### 1. Lokale Entwicklung

```bash
# 1. Dependencies installieren
pip install -r requirements.txt

# 2. Environment Variables setzen
cp .env.template .env
# Bearbeite .env mit deinen Einstellungen

# 3. App starten
python app.py
```

### 2. Erste Anmeldung
- **URL**: `http://localhost:5000/login`
- **Standard Admin**: 
  - Username: `admin`
  - Password: `admin123`
  - **⚠️ Sofort ändern nach erster Anmeldung!**

## 🌐 Render.com Deployment

### Quick Deploy:

1. **Code committen**:
```bash
git add .
git commit -m "Add user authentication"
git push origin main
```

2. **Render.com Service erstellen**:
- Repository verbinden
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn app:app`

3. **Environment Variables setzen**:
```env
FLASK_ENV=production
SECRET_KEY=[Auto-generiert von Render]
USER_DATABASE_PATH=/opt/render/project/src/users.db
WTF_CSRF_ENABLED=true
SESSION_COOKIE_SECURE=true
```

4. **Deploy**: Automatisch bei Git Push

## 🔒 Sicherheit

### Implementierte Sicherheitsmaßnahmen:
- ✅ **Passwort-Hashing** (PBKDF2-SHA256)
- ✅ **CSRF-Schutz** (Flask-WTF)
- ✅ **Sichere Sessions** (HttpOnly, Secure Cookies)
- ✅ **Input Validation** (WTForms)
- ✅ **User Isolation** (User-spezifische Dateien)
- ✅ **HTTPS Enforcement** (in Production)

### Database:
- **SQLite** für einfache Deployment
- **User-Tabelle** mit sichere Schema
- **Soft Delete** für User-Deaktivierung

## 📊 User Management

### Admin-Funktionen:
- User können sich selbst registrieren
- Admins können in der Database User verwalten
- Session-basierte Authentication
- Automatische Logout nach Inaktivität

### User Flow:
1. **Registrierung** → `/register`
2. **Login** → `/login`
3. **Datei-Konvertierung** → `/` (geschützt)
4. **Logout** → `/logout`

## 💾 Daten-Persistenz

### Lokale Entwicklung:
- SQLite Database: `users.db`
- Upload/Download Ordner: `uploads/`, `downloads/`

### Render Production:
- **Ohne Persistent Disk**: Database wird bei jedem Deploy zurückgesetzt
- **Mit Persistent Disk** (~$1/Monat): Database bleibt erhalten

## 🛠️ Anpassungen

### Deine originalen Features bleiben:
- ✅ **Q-DAS Parsing Logic** unverändert
- ✅ **Excel Export** funktioniert wie bisher
- ✅ **Multi-Format Support** (BOSCH, MESSDATE)
- ✅ **Batch Processing** für mehrere Dateien
- ✅ **ZIP Download** bei mehreren Dateien

### Neue Sicherheit:
- 🔒 **Nur angemeldete Benutzer** können Dateien konvertieren
- 🔒 **User-spezifische Downloads** (Isolation)
- 🔒 **Session-basierte Zugriffskontrolle**

## 🆘 Support & Troubleshooting

### Häufige Probleme:

1. **Database Fehler**: Prüfe Datei-Permissions für `users.db`
2. **Session Probleme**: Prüfe `SECRET_KEY` Environment Variable
3. **Upload Fehler**: Prüfe Ordner-Permissions für `uploads/downloads/`

### Logs prüfen:
```bash
# Lokale Entwicklung:
python app.py

# Render Production:
# Dashboard → Service → Logs
```

---

## 🎉 Ready to Deploy!

Deine App ist jetzt bereit für professionellen Einsatz mit:
- ✅ Sichere User Authentication
- ✅ Render.com Deployment Ready
- ✅ Production-grade Security
- ✅ Alle originalen Features erhalten

**Next Steps:**
1. Teste lokal mit `python app.py`
2. Deploye auf Render.com
3. Ändere Admin-Passwort
4. Fertig! 🚀
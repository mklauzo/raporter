# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Raporter is a Flask web application for managing Linux servers and generating system reports via SSH. The UI is in Polish.

## Development Commands

```bash
# Start application (builds and runs containers)
docker-compose up --build

# Rebuild after Python code changes (app/ folder is baked into image, not volume-mounted)
docker-compose up --build -d

# Restart web container (only for raport_servera.sh changes - the only mounted file)
docker-compose restart web

# Stop and remove containers
docker-compose down

# Stop and remove containers including database volume (resets database!)
docker-compose down -v

# View logs
docker-compose logs -f web
```

**Important:** The `app/` folder is copied into the Docker image at build time. Changes to Python files require `docker-compose up --build`, not just `restart`. Only `raport_servera.sh` is volume-mounted and can be updated with a simple restart.

**Default credentials:** adminek / adminek123

## Architecture

### Application Structure

```
app/
├── __init__.py      # Flask app factory, creates default user on startup
├── config.py        # Configuration from environment variables
├── models.py        # SQLAlchemy models: User, Server, Report, Settings
├── routes/
│   ├── auth.py      # Login, logout, settings (password, SSH key)
│   ├── servers.py   # Server CRUD operations
│   └── reports.py   # Report generation and history
└── services/
    ├── crypto.py    # Fernet encryption for SSH keys
    └── ssh_service.py  # Paramiko SSH connections
```

### Key Components

**SSH Service** (`services/ssh_service.py`):
- `SSHService` class is a context manager for SSH connections
- Supports RSA, Ed25519, ECDSA key types
- `generate_report(server)` uploads and executes `raport_servera.sh` on remote server

**Encryption** (`services/crypto.py`):
- SSH private keys are encrypted with Fernet before storing in database
- Key derived from Flask's SECRET_KEY via SHA256

**Models** (`models.py`):
- `Server.last_report` property returns most recent report for dashboard display
- `Settings.get(key)` / `Settings.set(key, value)` for key-value config storage

### Request Flow

1. User logs in → Flask-Login session created
2. Dashboard shows servers with last report status (color-coded badge)
3. "Generate Report" → POST to `/reports/generate/<id>` → SSH connection → execute script → store result → return JSON
4. Report displayed in Bootstrap modal via JavaScript

### Docker Setup

- `web` service: Flask app on port 5000
- `db` service: MariaDB 10.11 with health check
- `raport_servera.sh` mounted read-only into container
- Database initialized from `init_db.sql`

## Important Files

- `raport_servera.sh` - Bash script executed on remote servers, checks: Plesk version, disk usage, load, mail queue, updates, logs, firewall, Fail2Ban, ClamAV (if running)
- `init_db.sql` - Database schema (tables created here, user created by Flask)
- `.env.example` - Required environment variables template

## Report Script Sections

The `raport_servera.sh` generates reports with these sections:
1. Plesk version
2. Disk usage
3. Load & uptime
4. Mail queue (Postfix)
5. Package updates
6. Log analysis (syslog, web errors, MySQL)
7. Security (Firewall, Fail2Ban jails)
8. ClamAV antivirus (only if clamscan is running - shows scan summary, starts new scan in screen/background)

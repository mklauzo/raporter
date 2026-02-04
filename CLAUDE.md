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

### Key Components

- **App factory** (`app/__init__.py`): `create_app()` registers blueprints (`auth`, `servers`, `reports`), initializes extensions, and creates the default user on first run.
- **Routes** (`app/routes/`): Three blueprints — `auth.py` (login/logout/settings), `servers.py` (server CRUD + dashboard), `reports.py` (generation + history).
- **SSH Service** (`app/services/ssh_service.py`): Context manager class. Connects via Paramiko, uploads `raport_servera.sh` to `/tmp/` on remote server, executes it (120s timeout), returns output. Supports RSA, Ed25519, ECDSA keys.
- **Encryption** (`app/services/crypto.py`): Fernet encryption for SSH private keys stored in the `settings` table. Key derived from Flask's `SECRET_KEY` via SHA256.
- **Models** (`app/models.py`): `User`, `Server`, `Report`, `Settings`. Notable: `Server.last_report` property returns most recent report; `Settings.get(key)`/`Settings.set(key, value)` for key-value config.

### Request Flow

1. User logs in → Flask-Login session created
2. Dashboard shows servers with last report status (color-coded badge)
3. "Generate Report" → POST to `/reports/generate/<id>` → SSH connection → execute script → store result → return JSON
4. Report displayed in Bootstrap modal via JavaScript

### Database Schema (MariaDB 10.11)

- **users**: `id`, `username` (unique), `password_hash`, `created_at`
- **servers**: `id`, `name`, `ip_address`, `ssh_user` (default 'root'), `ssh_port` (default 22), `created_at`
- **reports**: `id`, `server_id` (FK → servers), `content` (text), `status` (enum: 'success'|'error'), `created_at`
- **settings**: `id`, `key` (unique), `value`, `updated_at` — used for storing encrypted SSH key

Schema defined in `init_db.sql`; default user created by Flask app on startup.

### Docker Setup

- `web` service: Flask app on port 5000, runs as non-root `appuser`
- `db` service: MariaDB 10.11 with health check, persistent `db_data` volume
- `raport_servera.sh` mounted read-only into container at `/app/raport_servera.sh`
- Database initialized from `init_db.sql`

## Report Script Sections

The `raport_servera.sh` generates reports with these sections:
1. Server metrics (IP, hostname, OS, kernel, hardware vendor/model via hostnamectl)
2. Plesk version
3. Disk usage
4. Load & uptime
5. Mail queue (Postfix)
6. Package updates
7. Log analysis (syslog, web errors, MySQL)
8. Security (Firewall, Fail2Ban jails)
9. ClamAV antivirus (only if clamscan is running - shows scan summary, starts new scan in screen/background)

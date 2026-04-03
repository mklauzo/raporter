import json
import os
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, Response, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import User, Server, Report, Settings
from app.services.crypto import encrypt_data

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('servers.dashboard'))
    return redirect(url_for('auth.login'))


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('servers.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('servers.dashboard'))

        flash('Nieprawidlowa nazwa uzytkownika lub haslo', 'error')

    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Wylogowano pomyslnie', 'success')
    return redirect(url_for('auth.login'))


@auth_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    from app.services.crypto import decrypt_data

    ssh_key_configured = Settings.get('ssh_private_key') is not None
    anthropic_key_configured = Settings.get('anthropic_api_key') is not None
    gemini_key_configured = Settings.get('gemini_api_key') is not None
    ai_provider = Settings.get('ai_provider') or 'anthropic'
    gemini_model = Settings.get('gemini_model') or 'gemini-2.0-flash'
    anthropic_model = Settings.get('anthropic_model') or 'claude-opus-4-6'

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'save_anthropic_key':
            key_value = request.form.get('anthropic_api_key', '').strip()
            if not key_value:
                flash('Podaj klucz Anthropic API', 'error')
            else:
                encrypted = encrypt_data(key_value)
                Settings.set('anthropic_api_key', encrypted)
                flash('Klucz Anthropic API zostal zapisany', 'success')
                anthropic_key_configured = True

        elif action == 'delete_anthropic_key':
            setting = Settings.query.filter_by(key='anthropic_api_key').first()
            if setting:
                db.session.delete(setting)
                db.session.commit()
                flash('Klucz Anthropic API zostal usuniety', 'success')
                anthropic_key_configured = False

        elif action == 'save_gemini_key':
            key_value = request.form.get('gemini_api_key', '').strip()
            if not key_value:
                flash('Podaj klucz Gemini API', 'error')
            else:
                encrypted = encrypt_data(key_value)
                Settings.set('gemini_api_key', encrypted)
                flash('Klucz Gemini API zostal zapisany', 'success')
                gemini_key_configured = True

        elif action == 'delete_gemini_key':
            setting = Settings.query.filter_by(key='gemini_api_key').first()
            if setting:
                db.session.delete(setting)
                db.session.commit()
                flash('Klucz Gemini API zostal usuniety', 'success')
                gemini_key_configured = False

        elif action == 'save_anthropic_model':
            model_name = request.form.get('anthropic_model', '').strip()
            if not model_name:
                flash('Podaj nazwe modelu Anthropic', 'error')
            else:
                Settings.set('anthropic_model', model_name)
                flash(f'Model Anthropic zmieniony na: {model_name}', 'success')
                anthropic_model = model_name

        elif action == 'save_gemini_model':
            model_name = request.form.get('gemini_model', '').strip()
            if not model_name:
                flash('Podaj nazwe modelu Gemini', 'error')
            else:
                Settings.set('gemini_model', model_name)
                flash(f'Model Gemini zmieniony na: {model_name}', 'success')
                gemini_model = model_name

        elif action == 'set_ai_provider':
            provider = request.form.get('ai_provider')
            if provider in ('anthropic', 'gemini'):
                Settings.set('ai_provider', provider)
                flash('Dostawca AI zostal zmieniony', 'success')
                ai_provider = provider

        elif action == 'change_password':
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')

            if not current_user.check_password(current_password):
                flash('Nieprawidlowe obecne haslo', 'error')
            elif new_password != confirm_password:
                flash('Nowe hasla nie sa zgodne', 'error')
            elif len(new_password) < 8:
                flash('Nowe haslo musi miec co najmniej 8 znakow', 'error')
            else:
                current_user.set_password(new_password)
                db.session.commit()
                flash('Haslo zostalo zmienione', 'success')

        elif action == 'upload_ssh_key':
            ssh_key_file = request.files.get('ssh_key')
            if ssh_key_file and ssh_key_file.filename:
                try:
                    key_content = ssh_key_file.read().decode('utf-8')
                    if 'PRIVATE KEY' not in key_content:
                        flash('Plik nie wyglada na klucz prywatny SSH', 'error')
                    else:
                        encrypted_key = encrypt_data(key_content)
                        Settings.set('ssh_private_key', encrypted_key)
                        flash('Klucz SSH zostal zapisany', 'success')
                        ssh_key_configured = True
                except Exception as e:
                    flash(f'Blad podczas wczytywania klucza: {e}', 'error')
            else:
                flash('Nie wybrano pliku', 'error')

        elif action == 'delete_ssh_key':
            setting = Settings.query.filter_by(key='ssh_private_key').first()
            if setting:
                db.session.delete(setting)
                db.session.commit()
                flash('Klucz SSH zostal usuniety', 'success')
                ssh_key_configured = False

    return render_template('settings.html',
                           ssh_key_configured=ssh_key_configured,
                           anthropic_key_configured=anthropic_key_configured,
                           gemini_key_configured=gemini_key_configured,
                           ai_provider=ai_provider,
                           gemini_model=gemini_model,
                           anthropic_model=anthropic_model)


@auth_bp.route('/settings/models/<provider>')
@login_required
def list_ai_models(provider):
    from app.services.crypto import decrypt_data

    if provider == 'gemini':
        encrypted = Settings.get('gemini_api_key')
        if not encrypted:
            return jsonify({'error': 'Brak klucza Gemini API'}), 400
        try:
            api_key = decrypt_data(encrypted)
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            models = sorted([
                m.name.replace('models/', '')
                for m in genai.list_models()
                if 'generateContent' in m.supported_generation_methods
            ])
            return jsonify({'models': models})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    elif provider == 'anthropic':
        from app.services.crypto import decrypt_data
        encrypted = Settings.get('anthropic_api_key')
        api_key = None
        if encrypted:
            try:
                api_key = decrypt_data(encrypted)
            except Exception:
                pass
        if not api_key:
            api_key = os.environ.get('ANTHROPIC_API_KEY')
        if not api_key:
            return jsonify({'error': 'Brak klucza Anthropic API'}), 400
        try:
            import anthropic as ant
            client = ant.Anthropic(api_key=api_key)
            models = sorted([m.id for m in client.models.list().data])
            return jsonify({'models': models})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    return jsonify({'error': 'Nieznany dostawca'}), 400


@auth_bp.route('/settings/export')
@login_required
def export_db():
    def serialize_datetime(dt):
        return dt.isoformat() if dt else None

    data = {
        'exported_at': datetime.utcnow().isoformat(),
        'users': [
            {
                'id': u.id,
                'username': u.username,
                'password_hash': u.password_hash,
                'created_at': serialize_datetime(u.created_at),
            }
            for u in User.query.all()
        ],
        'servers': [
            {
                'id': s.id,
                'name': s.name,
                'ip_address': s.ip_address,
                'ssh_user': s.ssh_user,
                'ssh_port': s.ssh_port,
                'created_at': serialize_datetime(s.created_at),
            }
            for s in Server.query.all()
        ],
        'reports': [
            {
                'id': r.id,
                'server_id': r.server_id,
                'content': r.content,
                'status': r.status,
                'created_at': serialize_datetime(r.created_at),
            }
            for r in Report.query.all()
        ],
        'settings': [
            {
                'id': st.id,
                'key': st.key,
                'value': st.value,
                'updated_at': serialize_datetime(st.updated_at),
            }
            for st in Settings.query.all()
        ],
    }

    filename = f"raporter_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    return Response(
        json.dumps(data, ensure_ascii=False, indent=2),
        mimetype='application/json',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )


@auth_bp.route('/settings/import', methods=['POST'])
@login_required
def import_db():
    file = request.files.get('import_file')
    if not file or not file.filename:
        flash('Nie wybrano pliku', 'error')
        return redirect(url_for('auth.settings'))

    try:
        data = json.loads(file.read().decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        flash('Nieprawidlowy format pliku JSON', 'error')
        return redirect(url_for('auth.settings'))

    required_keys = {'users', 'servers', 'reports', 'settings'}
    if not required_keys.issubset(data.keys()):
        flash('Plik nie zawiera wymaganych danych (users, servers, reports, settings)', 'error')
        return redirect(url_for('auth.settings'))

    def parse_datetime(val):
        if not val:
            return None
        return datetime.fromisoformat(val)

    try:
        Report.query.delete()
        Server.query.delete()
        Settings.query.delete()
        User.query.delete()
        db.session.flush()

        for u in data['users']:
            db.session.execute(
                db.text('INSERT INTO users (id, username, password_hash, created_at) VALUES (:id, :username, :password_hash, :created_at)'),
                {'id': u['id'], 'username': u['username'], 'password_hash': u['password_hash'], 'created_at': parse_datetime(u.get('created_at'))},
            )

        for s in data['servers']:
            db.session.execute(
                db.text('INSERT INTO servers (id, name, ip_address, ssh_user, ssh_port, created_at) VALUES (:id, :name, :ip_address, :ssh_user, :ssh_port, :created_at)'),
                {'id': s['id'], 'name': s['name'], 'ip_address': s['ip_address'], 'ssh_user': s.get('ssh_user', 'root'), 'ssh_port': s.get('ssh_port', 22), 'created_at': parse_datetime(s.get('created_at'))},
            )

        for r in data['reports']:
            db.session.execute(
                db.text('INSERT INTO reports (id, server_id, content, status, created_at) VALUES (:id, :server_id, :content, :status, :created_at)'),
                {'id': r['id'], 'server_id': r['server_id'], 'content': r.get('content'), 'status': r['status'], 'created_at': parse_datetime(r.get('created_at'))},
            )

        for st in data['settings']:
            db.session.execute(
                db.text('INSERT INTO settings (id, `key`, value, updated_at) VALUES (:id, :key, :value, :updated_at)'),
                {'id': st['id'], 'key': st['key'], 'value': st.get('value'), 'updated_at': parse_datetime(st.get('updated_at'))},
            )

        db.session.commit()
        flash('Baza danych zostala zaimportowana pomyslnie', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Blad podczas importu: {e}', 'error')

    return redirect(url_for('auth.settings'))

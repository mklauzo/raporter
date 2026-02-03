from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import User, Settings
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
    ssh_key_configured = Settings.get('ssh_private_key') is not None

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'change_password':
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

    return render_template('settings.html', ssh_key_configured=ssh_key_configured)

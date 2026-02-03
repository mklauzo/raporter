from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app import db
from app.models import Server

servers_bp = Blueprint('servers', __name__)


@servers_bp.route('/dashboard')
@login_required
def dashboard():
    servers = Server.query.order_by(Server.created_at.desc()).all()
    return render_template('dashboard.html', servers=servers)


@servers_bp.route('/servers/add', methods=['GET', 'POST'])
@login_required
def add_server():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        ip_address = request.form.get('ip_address', '').strip()
        ssh_user = request.form.get('ssh_user', 'root').strip()
        ssh_port = request.form.get('ssh_port', '22').strip()

        if not name or not ip_address:
            flash('Nazwa i adres IP sa wymagane', 'error')
            return render_template('server_form.html', server=None)

        try:
            ssh_port = int(ssh_port)
        except ValueError:
            ssh_port = 22

        server = Server(
            name=name,
            ip_address=ip_address,
            ssh_user=ssh_user or 'root',
            ssh_port=ssh_port
        )
        db.session.add(server)
        db.session.commit()

        flash(f'Serwer "{name}" zostal dodany', 'success')
        return redirect(url_for('servers.dashboard'))

    return render_template('server_form.html', server=None)


@servers_bp.route('/servers/<int:server_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_server(server_id):
    server = Server.query.get_or_404(server_id)

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        ip_address = request.form.get('ip_address', '').strip()
        ssh_user = request.form.get('ssh_user', 'root').strip()
        ssh_port = request.form.get('ssh_port', '22').strip()

        if not name or not ip_address:
            flash('Nazwa i adres IP sa wymagane', 'error')
            return render_template('server_form.html', server=server)

        try:
            ssh_port = int(ssh_port)
        except ValueError:
            ssh_port = 22

        server.name = name
        server.ip_address = ip_address
        server.ssh_user = ssh_user or 'root'
        server.ssh_port = ssh_port
        db.session.commit()

        flash(f'Serwer "{name}" zostal zaktualizowany', 'success')
        return redirect(url_for('servers.dashboard'))

    return render_template('server_form.html', server=server)


@servers_bp.route('/servers/<int:server_id>/delete', methods=['POST'])
@login_required
def delete_server(server_id):
    server = Server.query.get_or_404(server_id)
    name = server.name
    db.session.delete(server)
    db.session.commit()
    flash(f'Serwer "{name}" zostal usuniety', 'success')
    return redirect(url_for('servers.dashboard'))

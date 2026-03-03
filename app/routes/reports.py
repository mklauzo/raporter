from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required
from app import db
from app.models import Server, Report
from app.services.ssh_service import generate_report

reports_bp = Blueprint('reports', __name__)


@reports_bp.route('/reports/generate/<int:server_id>', methods=['POST'])
@login_required
def generate(server_id):
    server = Server.query.get_or_404(server_id)

    if not server.is_active:
        return jsonify({'success': False, 'content': 'Serwer jest wylaczony - generowanie raportow jest zablokowane.', 'status': 'error'}), 403

    content, status = generate_report(server)

    report = Report(
        server_id=server.id,
        content=content,
        status=status
    )
    db.session.add(report)
    db.session.commit()

    return jsonify({
        'success': status == 'success',
        'content': content,
        'status': status,
        'report_id': report.id
    })


@reports_bp.route('/reports/history')
@login_required
def history():
    page = request.args.get('page', 1, type=int)
    server_id = request.args.get('server_id', type=int)

    query = Report.query

    if server_id:
        query = query.filter_by(server_id=server_id)

    reports = query.order_by(Report.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )

    servers = Server.query.order_by(Server.name).all()

    return render_template('history.html', reports=reports, servers=servers, selected_server_id=server_id)


@reports_bp.route('/reports/<int:report_id>')
@login_required
def view_report(report_id):
    report = Report.query.get_or_404(report_id)
    return jsonify({
        'id': report.id,
        'server_name': report.server.name,
        'server_ip': report.server.ip_address,
        'content': report.content,
        'status': report.status,
        'created_at': report.created_at.strftime('%Y-%m-%d %H:%M:%S')
    })

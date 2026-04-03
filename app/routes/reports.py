from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required
from app import db
from app.models import Server, Report, Analysis, Settings
from app.services.ssh_service import generate_report, run_diagnostics
from app.services.ai_service import analyze_report

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


@reports_bp.route('/reports/analyze/<int:server_id>', methods=['POST'])
@login_required
def analyze(server_id):
    server = Server.query.get_or_404(server_id)

    if not server.is_active:
        return jsonify({'success': False, 'content': 'Serwer jest wyłączony.'}), 403

    report = Report.query.filter_by(server_id=server_id, status='success').order_by(Report.created_at.desc()).first()
    if not report:
        return jsonify({'success': False, 'content': 'Brak raportu do analizy. Najpierw wygeneruj raport dla tego serwera.'})

    diag_output, diag_ok = run_diagnostics(server)

    combined = report.content
    combined += '\n\n' + ('=' * 60) + '\n'
    combined += '=== DANE DIAGNOSTYCZNE (zebrane przed analizą) ===\n'
    combined += ('=' * 60) + '\n'
    combined += diag_output

    content, success = analyze_report(combined)

    provider = Settings.get('ai_provider') or 'anthropic'
    model_key = 'gemini_model' if provider == 'gemini' else 'anthropic_model'
    default_model = 'gemini-2.0-flash' if provider == 'gemini' else 'claude-opus-4-6'
    model = Settings.get(model_key) or default_model

    analysis = Analysis(
        server_id=server.id,
        content=content,
        ai_provider=provider,
        ai_model=model,
        status='success' if success else 'error'
    )
    db.session.add(analysis)
    db.session.commit()

    return jsonify({'success': success, 'content': content, 'report_date': report.created_at.strftime('%Y-%m-%d %H:%M'), 'analysis_id': analysis.id})


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


@reports_bp.route('/analyses/history')
@login_required
def analysis_history():
    page = request.args.get('page', 1, type=int)
    server_id = request.args.get('server_id', type=int)

    query = Analysis.query
    if server_id:
        query = query.filter_by(server_id=server_id)

    analyses = query.order_by(Analysis.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    servers = Server.query.order_by(Server.name).all()

    return render_template('analysis_history.html', analyses=analyses, servers=servers, selected_server_id=server_id)


@reports_bp.route('/analyses/<int:analysis_id>')
@login_required
def view_analysis(analysis_id):
    analysis = Analysis.query.get_or_404(analysis_id)
    return jsonify({
        'id': analysis.id,
        'server_name': analysis.server.name,
        'server_ip': analysis.server.ip_address,
        'content': analysis.content,
        'ai_provider': analysis.ai_provider,
        'ai_model': analysis.ai_model,
        'status': analysis.status,
        'created_at': analysis.created_at.strftime('%Y-%m-%d %H:%M:%S')
    })

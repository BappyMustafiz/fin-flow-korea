from flask import render_template, request, redirect, url_for, flash, jsonify, session, make_response
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta, date
from sqlalchemy import func, desc, extract
from app import app, db
from models import (Institution, Account, Transaction, Category, Department, 
                   Vendor, MappingRule, Contract, AuditLog, Alert, Consent, User)
import json
import re

# 인증 라우트들
@app.route('/login', methods=['GET', 'POST'])
@app.route('/fresh-login', methods=['GET', 'POST'])
def login():
    """로그인"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = bool(request.form.get('remember'))
        
        if not email or not password:
            flash('이메일과 패스워드를 입력해주세요.', 'error')
            return render_template('auth/login.html')
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            if not user.active:
                flash('비활성화된 계정입니다. 관리자에게 문의하세요.', 'error')
                return render_template('auth/login.html')
            
            login_user(user, remember=remember)
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('dashboard'))
        else:
            flash('이메일 또는 패스워드가 올바르지 않습니다.', 'error')
    
    return render_template('auth/login.html')

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    """로그아웃"""
    try:
        logout_user()
        session.clear()
        flash('로그아웃되었습니다.', 'success')
        return redirect(url_for('login'))
    except Exception as e:
        session.clear()
        return redirect(url_for('login'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """프로필 설정"""
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # 입력 검증
        if not name:
            flash('이름은 필수 입력 항목입니다.', 'error')
            return render_template('profile.html', departments=Department.query.all())
        
        # 이메일 중복 확인 (자신 제외)
        existing_user = User.query.filter(User.email == email, User.id != current_user.id).first()
        if existing_user:
            flash('이미 사용중인 이메일입니다.', 'error')
            return render_template('profile.html', departments=Department.query.all())
        
        # 비밀번호 변경 요청이 있는 경우
        if new_password:
            if not current_password:
                flash('현재 비밀번호를 입력해주세요.', 'error')
                return render_template('profile.html', departments=Department.query.all())
            
            if not current_user.check_password(current_password):
                flash('현재 비밀번호가 올바르지 않습니다.', 'error')
                return render_template('profile.html', departments=Department.query.all())
            
            if new_password != confirm_password:
                flash('새 비밀번호가 일치하지 않습니다.', 'error')
                return render_template('profile.html', departments=Department.query.all())
            
            if new_password is not None and len(new_password) < 6:
                flash('비밀번호는 최소 6자 이상이어야 합니다.', 'error')
                return render_template('profile.html', departments=Department.query.all())
            
            current_user.set_password(new_password)
        
        # 프로필 정보 업데이트
        current_user.name = name
        current_user.email = email
        current_user.updated_at = datetime.utcnow()
        
        db.session.commit()
        flash('프로필이 성공적으로 업데이트되었습니다.', 'success')
        return redirect(url_for('profile'))
    
    departments = Department.query.all()
    return render_template('profile.html', departments=departments)

@app.route('/register', methods=['GET', 'POST'])
def register():
    """회원가입"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        name = request.form.get('name')
        department_id = request.form.get('department_id') or None
        
        # 입력 검증
        if not all([email, password, confirm_password, name]):
            flash('모든 필드를 입력해주세요.', 'error')
            return render_template('auth/register.html', departments=Department.query.all())
        
        if password != confirm_password:
            flash('패스워드가 일치하지 않습니다.', 'error')
            return render_template('auth/register.html', departments=Department.query.all())
        
        if password and len(password) < 6:
            flash('패스워드는 최소 6자 이상이어야 합니다.', 'error')
            return render_template('auth/register.html', departments=Department.query.all())
        
        # 이메일 중복 확인
        if User.query.filter_by(email=email).first():
            flash('이미 등록된 이메일입니다.', 'error')
            return render_template('auth/register.html', departments=Department.query.all())
        
        # 새 사용자 생성
        user = User()
        user.email = email
        user.name = name
        user.department_id = department_id
        user.role = 'user'  # 기본값은 일반 사용자
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        flash('회원가입이 완료되었습니다. 로그인해주세요.', 'success')
        return redirect(url_for('login'))
    
    departments = Department.query.all()
    return render_template('auth/register.html', departments=departments)

@app.route('/')
@login_required
def dashboard():
    """대시보드 - KPI 및 주요 지표 표시"""
    # KPI 계산
    today = datetime.now().date()
    current_month = today.replace(day=1)
    last_month = (current_month - timedelta(days=1)).replace(day=1)
    
    # 이번달 수입/지출
    current_income = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.amount > 0,
        func.date(Transaction.transaction_date) >= current_month
    ).scalar() or 0
    
    current_expense = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.amount < 0,
        func.date(Transaction.transaction_date) >= current_month
    ).scalar() or 0
    
    # 저번달 수입/지출
    last_income = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.amount > 0,
        func.date(Transaction.transaction_date) >= last_month,
        func.date(Transaction.transaction_date) < current_month
    ).scalar() or 0
    
    last_expense = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.amount < 0,
        func.date(Transaction.transaction_date) >= last_month,
        func.date(Transaction.transaction_date) < current_month
    ).scalar() or 0
    
    # 미분류 거래 수
    unclassified_count = Transaction.query.filter_by(classification_status='pending').count()
    
    # 최근 거래 내역 (5건)
    recent_transactions = Transaction.query.order_by(desc(Transaction.transaction_date)).limit(5).all()
    
    # 최근 알림 (5건)
    recent_alerts = Alert.query.filter_by(is_read=False).order_by(desc(Alert.created_at)).limit(5).all()
    
    # 부서별 지출 현황 (이번달)
    dept_expenses_raw = db.session.query(
        Department.name,
        func.sum(Transaction.amount).label('total')
    ).join(Transaction).filter(
        Transaction.amount < 0,
        func.date(Transaction.transaction_date) >= current_month
    ).group_by(Department.name).all()
    
    # Convert to JSON serializable format
    dept_expenses = [{'name': row.name, 'total': float(abs(row.total or 0))} for row in dept_expenses_raw]
    
    return render_template('dashboard.html',
                         current_income=current_income,
                         current_expense=abs(current_expense),
                         last_income=last_income,
                         last_expense=abs(last_expense),
                         unclassified_count=unclassified_count,
                         recent_transactions=recent_transactions,
                         recent_alerts=recent_alerts,
                         dept_expenses=dept_expenses)

@app.route('/connections')
@login_required
def connections():
    """연결 관리 - 금융기관 연결 현황"""
    institutions = Institution.query.all()
    consents = Consent.query.join(Institution).all()
    
    return render_template('connections.html', 
                         institutions=institutions,
                         consents=consents)

@app.route('/connect/<institution_code>')
@login_required
def connect_institution(institution_code):
    """금융기관 연결 (OAuth 시뮬레이션)"""
    institution = Institution.query.filter_by(code=institution_code).first()
    if not institution:
        flash('지원하지 않는 금융기관입니다.', 'error')
        return redirect(url_for('connections'))
    
    # OAuth 동의 시뮬레이션
    consent = Consent()
    consent.institution_id = institution.id
    consent.consent_id = f"consent_{institution_code}_{datetime.now().timestamp()}"
    consent.status = 'active'
    consent.scope = 'account:read transaction:read'
    consent.expires_at = datetime.now() + timedelta(days=180)
    db.session.add(consent)
    db.session.commit()
    
    flash(f'{institution.name} 연결이 완료되었습니다.', 'success')
    return redirect(url_for('connections'))

@app.route('/accounts')
@login_required
def accounts():
    """계정 관리"""
    accounts = Account.query.join(Institution).all()
    departments = Department.query.all()
    institutions = Institution.query.all()
    
    return render_template('accounts.html', 
                         accounts=accounts,
                         departments=departments,
                         institutions=institutions)

@app.route('/account/add', methods=['POST'])
@login_required
def add_account():
    """계좌 추가"""
    try:
        # 새 계좌 생성
        account = Account()
        account.institution_id = request.form.get('institution_id')
        account.account_name = request.form.get('account_name')
        account.account_number = request.form.get('account_number')
        account.account_type = request.form.get('account_type')
        account.balance = float(request.form.get('balance', 0))
        account.currency = request.form.get('currency', 'KRW')
        account.department_id = request.form.get('department_id') or None
        account.is_active = True
        
        db.session.add(account)
        db.session.commit()
        
        flash('계좌가 성공적으로 추가되었습니다.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'계좌 추가 중 오류가 발생했습니다: {str(e)}', 'error')
    
    return redirect(url_for('accounts'))

@app.route('/account/<int:account_id>/edit', methods=['POST'])
@login_required
def edit_account(account_id):
    """계좌 정보 수정"""
    try:
        account = Account.query.get_or_404(account_id)
        
        # 계좌 정보 업데이트
        account.account_name = request.form.get('account_name')
        account.account_number = request.form.get('account_number')
        account.account_type = request.form.get('account_type')
        account.balance = float(request.form.get('balance', account.balance))
        account.department_id = request.form.get('department_id') or None
        
        db.session.commit()
        flash('계좌 정보가 성공적으로 수정되었습니다.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'계좌 수정 중 오류가 발생했습니다: {str(e)}', 'error')
    
    return redirect(url_for('accounts'))

@app.route('/transactions')
@login_required
def transactions():
    """거래 내역 관리"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # 필터 파라미터
    status = request.args.get('status', '')
    department_id = request.args.get('department_id', '')
    category_id = request.args.get('category_id', '')
    account_id = request.args.get('account_id', '')
    search = request.args.get('search', '')
    
    # 기본 쿼리 (활성 거래만)
    query = Transaction.query.filter(Transaction.is_active == True)
    
    # 필터 적용
    if status:
        query = query.filter(Transaction.classification_status == status)
    if department_id:
        query = query.filter(Transaction.department_id == department_id)
    if category_id:
        query = query.filter(Transaction.category_id == category_id)
    if account_id:
        query = query.filter(Transaction.account_id == account_id)
    if search:
        query = query.filter(
            db.or_(
                Transaction.description.contains(search),
                Transaction.counterparty.contains(search)
            )
        )
    
    # 페이지네이션
    transactions_page = query.order_by(desc(Transaction.transaction_date)).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # 필터 옵션을 위한 데이터
    departments = Department.query.all()
    categories = Category.query.all()
    accounts = Account.query.join(Institution).all()
    
    # 현재 선택된 계좌 정보
    selected_account = None
    if account_id:
        selected_account = Account.query.get(account_id)
    
    return render_template('transactions.html',
                         transactions=transactions_page.items,
                         pagination=transactions_page,
                         departments=departments,
                         categories=categories,
                         accounts=accounts,
                         selected_account=selected_account,
                         current_filters={
                             'status': status,
                             'department_id': department_id,
                             'category_id': category_id,
                             'account_id': account_id,
                             'search': search
                         })

@app.route('/transaction/<int:transaction_id>/details', methods=['GET'])
@login_required
def transaction_details(transaction_id):
    """거래 상세 정보 조회 (JSON)"""
    try:
        transaction = Transaction.query.get_or_404(transaction_id)
        
        transaction_data = {
            'id': transaction.id,
            'counterparty': transaction.counterparty,
            'description': transaction.description,
            'amount': float(transaction.amount),
            'transaction_date': transaction.transaction_date.isoformat(),
            'classification_status': transaction.classification_status,
            'account': {
                'institution': {'name': transaction.account.institution.name},
                'account_name': transaction.account.account_name
            }
        }
        
        return jsonify({'success': True, 'transaction': transaction_data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/transaction/<int:transaction_id>/split', methods=['POST'])
@login_required
def split_transaction(transaction_id):
    """거래 분할 처리"""
    try:
        original_transaction = Transaction.query.get_or_404(transaction_id)
        
        # 분할 데이터 받기
        amounts = request.form.getlist('amounts[]')
        descriptions = request.form.getlist('descriptions[]')
        categories = request.form.getlist('categories[]')
        departments = request.form.getlist('departments[]')
        
        # 금액 합계 검증
        total_amount = sum(float(amount) for amount in amounts)
        if abs(total_amount - float(original_transaction.amount)) > 0.01:
            flash('분할된 금액의 합계가 원본 거래 금액과 일치하지 않습니다.', 'error')
            return redirect(url_for('transactions'))
        
        # 원본 거래를 비활성화
        original_transaction.is_active = False
        original_transaction.split_parent_id = None  # 이것이 분할의 부모임을 표시
        
        # 분할된 거래들 생성
        for i, amount in enumerate(amounts):
            split_transaction = Transaction()
            split_transaction.account_id = original_transaction.account_id
            split_transaction.counterparty = original_transaction.counterparty
            split_transaction.description = descriptions[i] if descriptions[i] else f"{original_transaction.description} (분할 {i+1})"
            split_transaction.amount = float(amount)
            split_transaction.transaction_date = original_transaction.transaction_date
            split_transaction.processed_date = original_transaction.processed_date
            split_transaction.transaction_type = original_transaction.transaction_type
            split_transaction.classification_status = 'manual'  # 분할된 거래는 수동분류로 설정
            split_transaction.split_parent_id = original_transaction.id  # 원본 거래 ID 저장
            
            # 카테고리와 부서 설정
            if categories[i]:
                split_transaction.category_id = int(categories[i])
            if departments[i]:
                split_transaction.department_id = int(departments[i])
            
            db.session.add(split_transaction)
        
        db.session.commit()
        flash(f'거래가 {len(amounts)}개로 성공적으로 분할되었습니다.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'거래 분할 중 오류가 발생했습니다: {str(e)}', 'error')
    
    return redirect(url_for('transactions'))

@app.route('/transaction/<int:transaction_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_transaction(transaction_id):
    """거래 내역 편집"""
    transaction = Transaction.query.get_or_404(transaction_id)
    
    if request.method == 'POST':
        try:
            # 기본 정보 업데이트
            if request.form.get('description'):
                transaction.description = request.form.get('description')
            if request.form.get('counterparty'):
                transaction.counterparty = request.form.get('counterparty')
            if request.form.get('amount'):
                amount_str = request.form.get('amount')
                if amount_str:
                    transaction.amount = float(amount_str)
            if request.form.get('transaction_date'):
                from datetime import datetime
                date_str = request.form.get('transaction_date')
                if date_str:
                    transaction.transaction_date = datetime.fromisoformat(date_str)
            
            # 분류 정보 업데이트
            transaction.category_id = request.form.get('category_id') or None
            transaction.department_id = request.form.get('department_id') or None
            transaction.vendor_id = request.form.get('vendor_id') or None
            transaction.classification_status = request.form.get('classification_status', 'manual')
            transaction.memo = request.form.get('memo') or None
            
            # 수정일시 업데이트
            from datetime import datetime
            transaction.updated_at = datetime.utcnow()
            
            db.session.commit()
            flash('거래 내역이 수정되었습니다.', 'success')
            return redirect(url_for('transactions'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'수정 중 오류가 발생했습니다: {str(e)}', 'error')
    
    categories = Category.query.all()
    departments = Department.query.all()
    vendors = Vendor.query.all()
    
    return render_template('edit_transaction.html',
                         transaction=transaction,
                         categories=categories,
                         departments=departments,
                         vendors=vendors)

@app.route('/rules')
@login_required
def rules():
    """분류 규칙 관리"""
    rules = MappingRule.query.order_by(MappingRule.priority.desc()).all()
    categories = Category.query.all()
    departments = Department.query.all()
    vendors = Vendor.query.all()
    
    return render_template('rules.html',
                         rules=rules,
                         categories=categories,
                         departments=departments,
                         vendors=vendors)

@app.route('/rule/add', methods=['POST'])
@login_required
def add_rule():
    """분류 규칙 추가"""
    rule = MappingRule()
    rule.name = request.form['name']
    rule.priority = int(request.form.get('priority', 0))
    rule.condition_type = request.form['condition_type']
    rule.condition_field = request.form['condition_field']
    rule.condition_value = request.form['condition_value']
    rule.target_category_id = request.form.get('target_category_id') or None
    rule.target_department_id = request.form.get('target_department_id') or None
    rule.target_vendor_id = request.form.get('target_vendor_id') or None
    
    db.session.add(rule)
    db.session.commit()
    
    flash('분류 규칙이 추가되었습니다.', 'success')
    return redirect(url_for('rules'))

@app.route('/rule/<int:rule_id>/apply')
@login_required
def apply_rule(rule_id):
    """규칙 적용 실행"""
    rule = MappingRule.query.get_or_404(rule_id)
    
    # 미분류 거래에 규칙 적용
    query = Transaction.query.filter_by(classification_status='pending')
    
    if rule.condition_type == 'contains':
        if rule.condition_field == 'description':
            query = query.filter(Transaction.description.contains(rule.condition_value))
        elif rule.condition_field == 'counterparty':
            query = query.filter(Transaction.counterparty.contains(rule.condition_value))
    
    transactions = query.all()
    
    for transaction in transactions:
        if rule.target_category_id:
            transaction.category_id = rule.target_category_id
        if rule.target_department_id:
            transaction.department_id = rule.target_department_id
        if rule.target_vendor_id:
            transaction.vendor_id = rule.target_vendor_id
        transaction.classification_status = 'classified'
    
    db.session.commit()
    
    flash(f'{len(transactions)}건의 거래가 분류되었습니다.', 'success')
    return redirect(url_for('rules'))

@app.route('/reports')
@login_required
def reports():
    """보고서"""
    # 현금흐름 차트 데이터 (최근 12개월)
    end_date = date.today()
    start_date = end_date.replace(year=end_date.year - 1)
    
    # 월별 현금흐름
    monthly_flow_raw = db.session.query(
        extract('year', Transaction.transaction_date).label('year'),
        extract('month', Transaction.transaction_date).label('month'),
        func.sum(Transaction.amount).label('total')
    ).filter(
        Transaction.transaction_date >= start_date
    ).group_by(
        extract('year', Transaction.transaction_date),
        extract('month', Transaction.transaction_date)
    ).order_by('year', 'month').all()
    
    # Convert to JSON serializable format
    monthly_flow = [{'year': int(row.year), 'month': int(row.month), 'total': float(row.total or 0)} for row in monthly_flow_raw]
    
    # 부서별 지출 현황 (이번달)
    current_month = end_date.replace(day=1)
    dept_spending_raw = db.session.query(
        Department.name,
        func.sum(Transaction.amount).label('total')
    ).join(Transaction).filter(
        Transaction.amount < 0,
        Transaction.transaction_date >= current_month
    ).group_by(Department.name).all()
    
    # Convert to JSON serializable format
    dept_spending = [{'name': row.name, 'total': float(abs(row.total or 0))} for row in dept_spending_raw]
    
    # 상위 거래처 (이번달)
    top_vendors = db.session.query(
        Vendor.name,
        func.sum(Transaction.amount).label('total'),
        func.count(Transaction.id).label('count')
    ).join(Transaction).filter(
        Transaction.amount < 0,
        Transaction.transaction_date >= current_month
    ).group_by(Vendor.name).order_by(desc('total')).limit(10).all()
    
    # 디버깅을 위한 로그
    print(f"Monthly flow data: {monthly_flow}")
    print(f"Dept spending data: {dept_spending}")
    
    return render_template('reports.html',
                         monthly_flow=monthly_flow,
                         dept_spending=dept_spending,
                         top_vendors=top_vendors)

@app.route('/settings')
@login_required
def settings():
    """설정 및 알림 - alerts.html로 리다이렉트"""
    return redirect(url_for('alerts'))

@app.route('/alerts')
@login_required
def alerts():
    """알림 관리"""
    from models import AlertSetting
    alerts = Alert.query.order_by(desc(Alert.created_at)).limit(50).all()
    alert_settings = AlertSetting.query.order_by(desc(AlertSetting.created_at)).all()
    return render_template('alerts.html', alerts=alerts, alert_settings=alert_settings)

@app.route('/audit')
@login_required
def audit():
    """감사 로그"""
    return render_template('audit.html')

@app.route('/init_data')
@login_required
def init_data():
    """샘플 데이터 초기화"""
    init_sample_data()
    flash('샘플 데이터가 생성되었습니다.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/alert/<int:alert_id>/read')
@login_required
def mark_alert_read(alert_id):
    """알림 읽음 처리"""
    alert = Alert.query.get_or_404(alert_id)
    alert.is_read = True
    db.session.commit()
    
    return redirect(url_for('alerts'))

@app.route('/alerts/settings', methods=['POST'])
@login_required
def save_alert_settings():
    """알림 설정 저장"""
    try:
        settings_data = request.get_json()
        
        # 실제 구현에서는 사용자별 설정을 데이터베이스에 저장
        # 현재는 세션에 임시 저장
        session['alert_settings'] = settings_data
        
        return jsonify({'success': True, 'message': '알림 설정이 저장되었습니다.'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/alerts/add', methods=['POST'])
@login_required  
def add_alert_setting():
    """새 알림 설정 추가"""
    try:
        from utils import parse_alert_condition
        from models import AlertSetting
        
        # 폼 데이터 받기
        name = request.form.get('name')
        alert_type = request.form.get('type')
        condition = request.form.get('condition')
        severity = request.form.get('severity')
        channel = request.form.get('channel')
        
        if not name or not condition:
            flash('알림명과 조건은 필수입니다.', 'error')
            return redirect(url_for('alerts'))
        
        # 조건 파싱
        parsed = parse_alert_condition(condition)
        
        # 새 알림 설정 생성
        alert_setting = AlertSetting()
        alert_setting.name = name
        alert_setting.alert_type = alert_type or 'custom'
        alert_setting.condition = condition
        alert_setting.severity = severity or 'info'
        alert_setting.channel = channel or 'system'
        
        if parsed:
            alert_setting.condition_type = parsed['type']
            alert_setting.condition_field = parsed['field']
            alert_setting.condition_value = parsed['value']
        
        db.session.add(alert_setting)
        db.session.commit()
        
        flash(f'알림 설정 "{name}"이 추가되었습니다.', 'success')
        return redirect(url_for('alerts'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'알림 설정 추가 중 오류가 발생했습니다: {str(e)}', 'error')
        return redirect(url_for('alerts'))

@app.route('/alerts/settings/<int:setting_id>/toggle', methods=['POST'])
@login_required
def toggle_alert_setting(setting_id):
    """알림 설정 활성화/비활성화"""
    try:
        from models import AlertSetting
        setting = AlertSetting.query.get_or_404(setting_id)
        setting.is_active = not setting.is_active
        db.session.commit()
        
        status = '활성화' if setting.is_active else '비활성화'
        return jsonify({'success': True, 'message': f'알림 설정이 {status}되었습니다.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/alerts/settings/<int:setting_id>/delete', methods=['POST'])
@login_required
def delete_alert_setting(setting_id):
    """알림 설정 삭제"""
    try:
        from models import AlertSetting
        setting = AlertSetting.query.get_or_404(setting_id)
        setting_name = setting.name
        db.session.delete(setting)
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'알림 설정 "{setting_name}"이 삭제되었습니다.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/alerts/settings/edit', methods=['POST'])
@login_required
def edit_alert_setting():
    """알림 설정 수정"""
    try:
        from models import AlertSetting
        
        setting_id = request.form.get('setting_id')
        name = request.form.get('name')
        condition_type = request.form.get('condition_type')
        condition_value = request.form.get('condition_value')
        condition = request.form.get('condition')
        severity = request.form.get('severity', 'info')
        channel = request.form.get('channel', 'app')
        
        if not all([setting_id, name, condition]):
            flash('필수 정보가 누락되었습니다.', 'error')
            return redirect(url_for('alerts'))
        
        setting = AlertSetting.query.get_or_404(setting_id)
        
        # 조건이 비어있으면 자동 생성
        if not condition and condition_type and condition_value:
            from utils import generate_condition_from_type
            condition = generate_condition_from_type(condition_type, condition_value)
        
        setting.name = name
        setting.condition = condition
        setting.severity = severity
        setting.channel = channel
        
        db.session.commit()
        
        flash(f'알림 설정 "{name}"이 수정되었습니다.', 'success')
        return redirect(url_for('alerts'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'알림 설정 수정 중 오류가 발생했습니다: {str(e)}', 'error')
        return redirect(url_for('alerts'))

@app.route('/contracts')
@login_required
def contracts():
    """계약 관리"""
    from models import Contract, Vendor, Department
    contracts = Contract.query.order_by(desc(Contract.created_at)).all()
    vendors = Vendor.query.all()
    departments = Department.query.all()
    return render_template('contracts.html', contracts=contracts, vendors=vendors, departments=departments)

@app.route('/contracts/add', methods=['POST'])
@login_required
def add_contract():
    """계약 추가"""
    try:
        from models import Contract
        
        name = request.form.get('name')
        vendor_id = request.form.get('vendor_id')
        department_id = request.form.get('department_id')
        contract_amount = request.form.get('contract_amount')
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        description = request.form.get('description', '')
        
        if not all([name, vendor_id, department_id, contract_amount, start_date_str, end_date_str]):
            flash('필수 정보가 누락되었습니다.', 'error')
            return redirect(url_for('contracts'))
        
        # 날짜 변환
        from datetime import datetime
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        contract = Contract(
            name=name,
            vendor_id=int(vendor_id),
            department_id=int(department_id),
            contract_amount=float(contract_amount),
            start_date=start_date,
            end_date=end_date,
            description=description
        )
        
        db.session.add(contract)
        db.session.commit()
        
        flash(f'계약 "{name}"이 추가되었습니다.', 'success')
        return redirect(url_for('contracts'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'계약 추가 중 오류가 발생했습니다: {str(e)}', 'error')
        return redirect(url_for('contracts'))

@app.route('/contracts/<int:contract_id>/edit', methods=['POST'])
@login_required
def edit_contract(contract_id):
    """계약 수정"""
    try:
        from models import Contract
        
        contract = Contract.query.get_or_404(contract_id)
        
        contract.name = request.form.get('name', contract.name)
        contract.vendor_id = int(request.form.get('vendor_id', contract.vendor_id))
        contract.department_id = int(request.form.get('department_id', contract.department_id))
        contract.contract_amount = float(request.form.get('contract_amount', contract.contract_amount))
        
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        
        if start_date_str:
            from datetime import datetime
            contract.start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        
        if end_date_str:
            from datetime import datetime
            contract.end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        contract.description = request.form.get('description', contract.description)
        contract.status = request.form.get('status', contract.status)
        
        db.session.commit()
        
        flash(f'계약 "{contract.name}"이 수정되었습니다.', 'success')
        return redirect(url_for('contracts'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'계약 수정 중 오류가 발생했습니다: {str(e)}', 'error')
        return redirect(url_for('contracts'))

@app.route('/budgets')
@login_required
def budgets():
    """예산 관리"""
    from models import Department, Category, CategoryBudget
    from datetime import datetime
    
    departments = Department.query.all()
    categories = Category.query.all()
    
    # 현재 월의 분류별 예산 가져오기
    current_year = datetime.now().year
    current_month = datetime.now().month
    
    category_budgets = CategoryBudget.query.filter_by(
        year=current_year, 
        month=current_month, 
        is_active=True
    ).all()
    
    return render_template('budgets.html', 
                         departments=departments,
                         categories=categories,
                         category_budgets=category_budgets,
                         current_year=current_year,
                         current_month=current_month)

@app.route('/budgets/update', methods=['POST'])
@login_required
def update_budgets():
    """예산 업데이트"""
    try:
        from models import Department
        
        for dept_id, budget_str in request.form.items():
            if dept_id.startswith('budget_'):
                department_id = int(dept_id.replace('budget_', ''))
                budget_amount = float(budget_str) if budget_str else 0
                
                department = Department.query.get(department_id)
                if department:
                    department.budget = budget_amount
        
        db.session.commit()
        flash('예산이 성공적으로 업데이트되었습니다.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'예산 업데이트 중 오류가 발생했습니다: {str(e)}', 'error')
    
    return redirect(url_for('budgets'))

@app.route('/budgets/category/add', methods=['POST'])
@login_required
def add_category_budget():
    """분류별 예산 추가"""
    try:
        from models import CategoryBudget
        from datetime import datetime
        
        category_id = int(request.form.get('category_id'))
        budget_amount = float(request.form.get('budget_amount', 0))
        year = int(request.form.get('year', datetime.now().year))
        month = int(request.form.get('month', datetime.now().month))
        description = request.form.get('description', '').strip()
        
        # 중복 체크
        existing = CategoryBudget.query.filter_by(
            category_id=category_id,
            year=year,
            month=month,
            is_active=True
        ).first()
        
        if existing:
            flash('해당 분류의 예산이 이미 설정되어 있습니다.', 'error')
            return redirect(url_for('budgets'))
        
        category_budget = CategoryBudget(
            category_id=category_id,
            budget_amount=budget_amount,
            year=year,
            month=month,
            description=description
        )
        
        db.session.add(category_budget)
        db.session.commit()
        
        flash('분류별 예산이 추가되었습니다.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'분류별 예산 추가 중 오류가 발생했습니다: {str(e)}', 'error')
    
    return redirect(url_for('budgets'))

@app.route('/budgets/category/<int:budget_id>/edit', methods=['POST'])
@login_required
def edit_category_budget(budget_id):
    """분류별 예산 수정"""
    try:
        from models import CategoryBudget
        
        category_budget = CategoryBudget.query.get_or_404(budget_id)
        
        category_budget.budget_amount = float(request.form.get('budget_amount', 0))
        category_budget.description = request.form.get('description', '').strip()
        
        db.session.commit()
        
        flash('분류별 예산이 수정되었습니다.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'분류별 예산 수정 중 오류가 발생했습니다: {str(e)}', 'error')
    
    return redirect(url_for('budgets'))

@app.route('/budgets/category/<int:budget_id>/delete', methods=['POST'])
@login_required
def delete_category_budget(budget_id):
    """분류별 예산 삭제"""
    try:
        from models import CategoryBudget
        
        category_budget = CategoryBudget.query.get_or_404(budget_id)
        category_budget.is_active = False  # Soft delete
        
        db.session.commit()
        
        flash('분류별 예산이 삭제되었습니다.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'분류별 예산 삭제 중 오류가 발생했습니다: {str(e)}', 'error')
    
    return redirect(url_for('budgets'))

@app.route('/departments')
@login_required
def departments():
    """부서 관리"""
    from models import Department
    departments = Department.query.all()
    return render_template('departments.html', departments=departments)

@app.route('/departments/add', methods=['POST'])
@login_required
def add_department():
    """부서 추가"""
    try:
        from models import Department
        
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        
        if not name:
            flash('부서명은 필수입니다.', 'error')
            return redirect(url_for('departments'))
        
        # 중복 체크
        existing = Department.query.filter_by(name=name).first()
        if existing:
            flash('이미 존재하는 부서명입니다.', 'error')
            return redirect(url_for('departments'))
        
        department = Department(name=name, description=description)
        db.session.add(department)
        db.session.commit()
        
        flash(f'부서 "{name}"이 추가되었습니다.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'부서 추가 중 오류가 발생했습니다: {str(e)}', 'error')
    
    return redirect(url_for('departments'))

@app.route('/departments/<int:dept_id>/edit', methods=['POST'])
@login_required
def edit_department(dept_id):
    """부서 수정"""
    try:
        from models import Department
        
        department = Department.query.get_or_404(dept_id)
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        
        if not name:
            flash('부서명은 필수입니다.', 'error')
            return redirect(url_for('departments'))
        
        # 중복 체크 (자기 자신 제외)
        existing = Department.query.filter(
            Department.name == name, 
            Department.id != dept_id
        ).first()
        if existing:
            flash('이미 존재하는 부서명입니다.', 'error')
            return redirect(url_for('departments'))
        
        department.name = name
        department.description = description
        db.session.commit()
        
        flash(f'부서 "{name}"이 수정되었습니다.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'부서 수정 중 오류가 발생했습니다: {str(e)}', 'error')
    
    return redirect(url_for('departments'))

@app.route('/departments/<int:dept_id>/delete', methods=['POST'])
@login_required
def delete_department(dept_id):
    """부서 삭제"""
    try:
        from models import Department, User
        
        department = Department.query.get_or_404(dept_id)
        
        # 부서에 속한 사용자가 있는지 확인
        users_count = User.query.filter_by(department_id=dept_id).count()
        if users_count > 0:
            flash(f'부서에 {users_count}명의 사용자가 있어 삭제할 수 없습니다.', 'error')
            return redirect(url_for('departments'))
        
        db.session.delete(department)
        db.session.commit()
        
        flash(f'부서 "{department.name}"이 삭제되었습니다.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'부서 삭제 중 오류가 발생했습니다: {str(e)}', 'error')
    
    return redirect(url_for('departments'))

# API 엔드포인트들

@app.route('/users')
@login_required
def users():
    """사용자 관리 (관리자 전용)"""
    if not current_user.is_admin():
        flash('관리자만 접근할 수 있습니다.', 'error')
        return redirect(url_for('dashboard'))
    
    users = User.query.all()
    departments = Department.query.all()
    return render_template('users.html', users=users, departments=departments)

@app.route('/user/<int:user_id>/toggle', methods=['POST'])
@login_required
def toggle_user_status(user_id):
    """사용자 활성화/비활성화 (관리자 전용)"""
    if not current_user.is_admin():
        flash('관리자만 접근할 수 있습니다.', 'error')
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    
    # 자기 자신은 비활성화할 수 없음
    if user.id == current_user.id:
        flash('자기 자신의 계정은 비활성화할 수 없습니다.', 'error')
        return redirect(url_for('users'))
    
    user.is_active = not user.is_active
    db.session.commit()
    
    status = "활성화" if user.is_active else "비활성화"
    flash(f'{user.name} 사용자가 {status}되었습니다.', 'success')
    return redirect(url_for('users'))

@app.route('/user/<int:user_id>/role', methods=['POST'])
@login_required
def change_user_role(user_id):
    """사용자 권한 변경 (관리자 전용)"""
    if not current_user.is_admin():
        flash('관리자만 접근할 수 있습니다.', 'error')
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    new_role = request.form.get('role')
    
    if new_role not in ['admin', 'user']:
        flash('잘못된 권한입니다.', 'error')
        return redirect(url_for('users'))
    
    # 자기 자신의 관리자 권한은 해제할 수 없음
    if user.id == current_user.id and new_role != 'admin':
        flash('자기 자신의 관리자 권한은 해제할 수 없습니다.', 'error')
        return redirect(url_for('users'))
    
    old_role = user.role
    user.role = new_role
    db.session.commit()
    
    role_name = "관리자" if new_role == 'admin' else "일반 사용자"
    flash(f'{user.name} 사용자의 권한이 {role_name}로 변경되었습니다.', 'success')
    return redirect(url_for('users'))

@app.route('/user/<int:user_id>/department', methods=['POST'])
@login_required
def change_user_department(user_id):
    """사용자 부서 변경 (관리자 전용)"""
    if not current_user.is_admin():
        flash('관리자만 접근할 수 있습니다.', 'error')
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    department_id = request.form.get('department_id') or None
    
    user.department_id = department_id
    db.session.commit()
    
    if department_id:
        department = Department.query.get(department_id)
        if department:
            flash(f'{user.name} 사용자의 부서가 {department.name}로 변경되었습니다.', 'success')
        else:
            flash(f'{user.name} 사용자의 부서가 변경되었습니다.', 'success')
    else:
        flash(f'{user.name} 사용자의 부서가 제거되었습니다.', 'success')
    
    return redirect(url_for('users'))

@app.route('/user/add', methods=['POST'])
@login_required
def add_user():
    """새 사용자 추가 (관리자 전용)"""
    if not current_user.is_admin():
        flash('관리자만 접근할 수 있습니다.', 'error')
        return redirect(url_for('dashboard'))
    
    # 이메일 중복 확인
    email = request.form.get('email')
    if User.query.filter_by(email=email).first():
        flash('이미 존재하는 이메일입니다.', 'error')
        return redirect(url_for('users'))
    
    # 새 사용자 생성
    user = User()
    user.name = request.form.get('name')
    user.email = email
    user.set_password(request.form.get('password'))
    user.role = request.form.get('role', 'user')
    user.department_id = request.form.get('department_id') or None
    
    db.session.add(user)
    db.session.commit()
    
    flash(f'{user.name} 사용자가 추가되었습니다.', 'success')
    return redirect(url_for('users'))

@app.route('/user/<int:user_id>/delete', methods=['POST'])
@login_required
def delete_user(user_id):
    """사용자 삭제 (관리자 전용)"""
    if not current_user.is_admin():
        flash('관리자만 접근할 수 있습니다.', 'error')
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    
    # 자기 자신은 삭제할 수 없음
    if user.id == current_user.id:
        flash('자기 자신의 계정은 삭제할 수 없습니다.', 'error')
        return redirect(url_for('users'))
    
    user_name = user.name
    db.session.delete(user)
    db.session.commit()
    
    flash(f'{user_name} 사용자가 삭제되었습니다.', 'success')
    return redirect(url_for('users'))

@app.route('/api/dashboard/chart-data')
@login_required
def api_dashboard_chart_data():
    """대시보드 차트 데이터 API"""
    # 최근 7일 일별 현금흐름
    end_date = date.today()
    start_date = end_date - timedelta(days=6)
    
    # 간단하게 모든 거래를 가져와서 처리
    transactions = Transaction.query.filter(
        func.date(Transaction.transaction_date) >= start_date
    ).all()
    
    # 날짜별로 데이터 집계
    daily_data = {}
    current_date = start_date
    while current_date <= end_date:
        daily_data[current_date] = {'income': 0, 'expense': 0}
        current_date += timedelta(days=1)
    
    for transaction in transactions:
        trans_date = transaction.transaction_date.date()
        if trans_date in daily_data:
            if transaction.amount > 0:
                daily_data[trans_date]['income'] += float(transaction.amount)
            else:
                daily_data[trans_date]['expense'] += float(abs(transaction.amount))
    
    dates = []
    income_data = []
    expense_data = []
    
    for date_key in sorted(daily_data.keys()):
        dates.append(date_key.strftime('%m/%d'))
        income_data.append(daily_data[date_key]['income'])
        expense_data.append(daily_data[date_key]['expense'])
    
    return jsonify({
        'dates': dates,
        'income': income_data,
        'expense': expense_data
    })

# 초기 데이터 생성용 헬퍼 함수들

def init_sample_data():
    """샘플 데이터 초기화 (개발용)"""
    if Institution.query.count() > 0:
        return
    
    # 금융기관 데이터
    institutions = []
    institution_data = [
        {'code': '001', 'name': 'KB국민은행', 'type': 'bank'},
        {'code': '002', 'name': '신한은행', 'type': 'bank'},
        {'code': '003', 'name': '우리은행', 'type': 'bank'},
        {'code': '101', 'name': '삼성카드', 'type': 'card'},
        {'code': '102', 'name': '현대카드', 'type': 'card'},
    ]
    for data in institution_data:
        inst = Institution()
        inst.code = data['code']
        inst.name = data['name']
        inst.type = data['type']
        institutions.append(inst)
    
    # 부서 데이터
    departments = []
    department_data = [
        {'code': '001', 'name': '경영지원팀', 'budget': 10000000},
        {'code': '002', 'name': '개발팀', 'budget': 15000000},
        {'code': '003', 'name': '마케팅팀', 'budget': 8000000},
        {'code': '004', 'name': '영업팀', 'budget': 12000000},
    ]
    for data in department_data:
        dept = Department()
        dept.code = data['code']
        dept.name = data['name']
        dept.budget = data['budget']
        departments.append(dept)
    
    # 카테고리 데이터
    categories = []
    category_data = [
        {'code': '001', 'name': '사무용품'},
        {'code': '002', 'name': '교통비'},
        {'code': '003', 'name': '식비'},
        {'code': '004', 'name': '임대료'},
        {'code': '005', 'name': '통신비'},
        {'code': '006', 'name': '광고비'},
        {'code': '007', 'name': '회의비'},
    ]
    for data in category_data:
        cat = Category()
        cat.code = data['code']
        cat.name = data['name']
        categories.append(cat)
    
    # 거래처 데이터
    vendors = []
    vendor_data = [
        {'name': '사무용품쇼핑몰', 'business_number': '123-45-67890', 'category_id': 1},
        {'name': '카카오T', 'business_number': '234-56-78901', 'category_id': 2},
        {'name': '배달의민족', 'business_number': '345-67-89012', 'category_id': 3},
        {'name': '부동산관리공사', 'business_number': '456-78-90123', 'category_id': 4},
        {'name': 'SKT', 'business_number': '567-89-01234', 'category_id': 5},
        {'name': '스타벅스', 'business_number': '678-90-12345', 'category_id': 3},
        {'name': '네이버', 'business_number': '789-01-23456', 'category_id': 6},
    ]
    for data in vendor_data:
        vendor = Vendor()
        vendor.name = data['name']
        vendor.business_number = data['business_number']
        vendor.category_id = data['category_id']
        vendors.append(vendor)
    
    db.session.add_all(institutions + departments + categories + vendors)
    db.session.commit()
    
    # 계좌 데이터
    accounts = []
    account_data = [
        {'institution_id': 1, 'account_number': '123-456-789012', 'account_name': '법인통장', 'account_type': 'checking', 'balance': 50000000, 'department_id': 1},
        {'institution_id': 2, 'account_number': '987-654-321098', 'account_name': '개발팀 통장', 'account_type': 'checking', 'balance': 15000000, 'department_id': 2},
        {'institution_id': 4, 'account_number': '1234-5678-9012', 'account_name': '법인카드', 'account_type': 'credit', 'balance': 0, 'department_id': 1},
    ]
    for data in account_data:
        account = Account()
        account.institution_id = data['institution_id']
        account.account_number = data['account_number']
        account.account_name = data['account_name']
        account.account_type = data['account_type']
        account.balance = data['balance']
        account.department_id = data['department_id']
        accounts.append(account)
    
    db.session.add_all(accounts)
    db.session.commit()
    
    # 샘플 거래 데이터
    sample_transactions = []
    for i in range(100):
        transaction = Transaction()
        transaction.account_id = 1
        transaction.transaction_id = f'TXN-{i:06d}'
        transaction.amount = -5500 if i % 3 == 0 else (15000 if i % 5 == 0 else -12000)
        transaction.transaction_type = 'debit'
        transaction.description = f'스타벅스 강남점' if i % 3 == 0 else (f'프로젝트 수수료 입금' if i % 5 == 0 else f'사무용품 구매')
        transaction.counterparty = f'스타벅스' if i % 3 == 0 else (f'클라이언트' if i % 5 == 0 else f'오피스디포')
        transaction.transaction_date = datetime.now() - timedelta(days=i)
        transaction.classification_status = 'pending' if i % 4 == 0 else 'classified'
        transaction.category_id = 3 if i % 3 == 0 else (None if i % 5 == 0 else 1)
        transaction.department_id = 2 if i % 2 == 0 else 1
        transaction.vendor_id = 6 if i % 3 == 0 else (None if i % 5 == 0 else 1)
        sample_transactions.append(transaction)
    
    db.session.add_all(sample_transactions)
    db.session.commit()
    
    # 샘플 알림 데이터
    sample_alerts = []
    alert_data = [
        {'title': '예산 초과 경고', 'message': '개발팀의 이번 달 지출이 예산의 85%에 달했습니다.', 'alert_type': 'budget', 'severity': 'warning'},
        {'title': '계약 만료 임박', 'message': 'SKT 통신 서비스 계약이 30일 후 만료됩니다.', 'alert_type': 'contract', 'severity': 'info'},
        {'title': '이상거래 감지', 'message': '평소보다 큰 금액의 거래가 감지되었습니다. (1,500,000원)', 'alert_type': 'anomaly', 'severity': 'warning'},
    ]
    for data in alert_data:
        alert = Alert()
        alert.title = data['title']
        alert.message = data['message']
        alert.alert_type = data['alert_type']
        alert.severity = data['severity']
        sample_alerts.append(alert)
    
    db.session.add_all(sample_alerts)
    db.session.commit()
    
    # 샘플 분류 규칙
    sample_rules = []
    rule_data = [
        {'name': '스타벅스 자동분류', 'priority': 8, 'condition_type': 'contains', 'condition_field': 'counterparty', 'condition_value': '스타벅스', 'target_category_id': 3, 'target_vendor_id': 6},
        {'name': '사무용품 자동분류', 'priority': 7, 'condition_type': 'contains', 'condition_field': 'description', 'condition_value': '사무용품', 'target_category_id': 1, 'target_department_id': 1, 'target_vendor_id': 1},
    ]
    for data in rule_data:
        rule = MappingRule()
        rule.name = data['name']
        rule.priority = data['priority']
        rule.condition_type = data['condition_type']
        rule.condition_field = data['condition_field']
        rule.condition_value = data['condition_value']
        rule.target_category_id = data.get('target_category_id')
        rule.target_department_id = data.get('target_department_id')
        rule.target_vendor_id = data.get('target_vendor_id')
        sample_rules.append(rule)
    
    db.session.add_all(sample_rules)
    db.session.commit()

def create_tables():
    """앱 시작시 테이블 생성 및 초기 데이터 로드"""
    db.create_all()
    init_sample_data()

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
            if not user.is_active:
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
        if current_user.is_authenticated:
            logout_user()
        
        # 세션 완전 초기화
        session.clear()
        
        # 응답 생성 - 직접 HTML 리다이렉트
        html = '''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <script>
                // 스토리지 완전 클리어
                if(typeof(Storage) !== "undefined") {
                    localStorage.clear();
                    sessionStorage.clear();
                }
                // 강제 리다이렉트
                window.location.replace('/login');
            </script>
        </head>
        <body>
            <p>로그아웃 중...</p>
        </body>
        </html>
        '''
        
        response = make_response(html)
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache' 
        response.headers['Expires'] = '0'
        response.headers['Content-Type'] = 'text/html; charset=utf-8'
        
        return response
        
    except Exception as e:
        # 에러가 나도 강제로 로그인 페이지로
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
            
            if len(new_password) < 6:
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
        
        if len(password) < 6:
            flash('패스워드는 최소 6자 이상이어야 합니다.', 'error')
            return render_template('auth/register.html', departments=Department.query.all())
        
        # 이메일 중복 확인
        if User.query.filter_by(email=email).first():
            flash('이미 등록된 이메일입니다.', 'error')
            return render_template('auth/register.html', departments=Department.query.all())
        
        # 새 사용자 생성
        user = User(
            email=email,
            name=name,
            department_id=department_id,
            role='user'  # 기본값은 일반 사용자
        )
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
    consent = Consent(
        institution_id=institution.id,
        consent_id=f"consent_{institution_code}_{datetime.now().timestamp()}",
        status='active',
        scope='account:read transaction:read',
        expires_at=datetime.now() + timedelta(days=180)
    )
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
    
    return render_template('accounts.html', 
                         accounts=accounts,
                         departments=departments)

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
    search = request.args.get('search', '')
    
    # 기본 쿼리
    query = Transaction.query
    
    # 필터 적용
    if status:
        query = query.filter(Transaction.classification_status == status)
    if department_id:
        query = query.filter(Transaction.department_id == department_id)
    if category_id:
        query = query.filter(Transaction.category_id == category_id)
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
    
    return render_template('transactions.html',
                         transactions=transactions_page.items,
                         pagination=transactions_page,
                         departments=departments,
                         categories=categories,
                         current_filters={
                             'status': status,
                             'department_id': department_id,
                             'category_id': category_id,
                             'search': search
                         })

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
                transaction.amount = float(request.form.get('amount'))
            if request.form.get('transaction_date'):
                from datetime import datetime
                transaction.transaction_date = datetime.fromisoformat(request.form.get('transaction_date'))
            
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
    rule = MappingRule(
        name=request.form['name'],
        priority=int(request.form.get('priority', 0)),
        condition_type=request.form['condition_type'],
        condition_field=request.form['condition_field'],
        condition_value=request.form['condition_value'],
        target_category_id=request.form.get('target_category_id') or None,
        target_department_id=request.form.get('target_department_id') or None,
        target_vendor_id=request.form.get('target_vendor_id') or None
    )
    
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
    start_date = end_date.replace(month=1 if end_date.month == 12 else end_date.month + 1, 
                                  year=end_date.year - 1 if end_date.month == 12 else end_date.year)
    
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
    alerts = Alert.query.order_by(desc(Alert.created_at)).limit(50).all()
    return render_template('alerts.html', alerts=alerts)

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
        flash(f'{user.name} 사용자의 부서가 {department.name}로 변경되었습니다.', 'success')
    else:
        flash(f'{user.name} 사용자의 부서가 제거되었습니다.', 'success')
    
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
    institutions = [
        Institution(code='001', name='KB국민은행', type='bank'),
        Institution(code='002', name='신한은행', type='bank'),
        Institution(code='003', name='우리은행', type='bank'),
        Institution(code='101', name='삼성카드', type='card'),
        Institution(code='102', name='현대카드', type='card'),
    ]
    
    # 부서 데이터
    departments = [
        Department(code='001', name='경영지원팀', budget=10000000),
        Department(code='002', name='개발팀', budget=15000000),
        Department(code='003', name='마케팅팀', budget=8000000),
        Department(code='004', name='영업팀', budget=12000000),
    ]
    
    # 카테고리 데이터
    categories = [
        Category(code='001', name='사무용품'),
        Category(code='002', name='교통비'),
        Category(code='003', name='식비'),
        Category(code='004', name='임대료'),
        Category(code='005', name='통신비'),
        Category(code='006', name='광고비'),
        Category(code='007', name='회의비'),
    ]
    
    # 거래처 데이터
    vendors = [
        Vendor(name='사무용품쇼핑몰', business_number='123-45-67890', category_id=1),
        Vendor(name='카카오T', business_number='234-56-78901', category_id=2),
        Vendor(name='배달의민족', business_number='345-67-89012', category_id=3),
        Vendor(name='부동산관리공사', business_number='456-78-90123', category_id=4),
        Vendor(name='SKT', business_number='567-89-01234', category_id=5),
        Vendor(name='스타벅스', business_number='678-90-12345', category_id=3),
        Vendor(name='네이버', business_number='789-01-23456', category_id=6),
    ]
    
    db.session.add_all(institutions + departments + categories + vendors)
    db.session.commit()
    
    # 계좌 데이터
    accounts = [
        Account(institution_id=1, account_number='123-456-789012', 
                account_name='법인통장', account_type='checking', 
                balance=50000000, department_id=1),
        Account(institution_id=2, account_number='987-654-321098', 
                account_name='개발팀 통장', account_type='checking', 
                balance=15000000, department_id=2),
        Account(institution_id=4, account_number='1234-5678-9012', 
                account_name='법인카드', account_type='credit', 
                balance=0, department_id=1),
    ]
    
    db.session.add_all(accounts)
    db.session.commit()
    
    # 샘플 거래 데이터
    sample_transactions = [
        Transaction(
            account_id=1, 
            transaction_id=f'TXN-{i:06d}',
            amount=-5500 if i % 3 == 0 else (15000 if i % 5 == 0 else -12000),
            transaction_type='debit',
            description=f'스타벅스 강남점' if i % 3 == 0 else (f'프로젝트 수수료 입금' if i % 5 == 0 else f'사무용품 구매'),
            counterparty=f'스타벅스' if i % 3 == 0 else (f'클라이언트' if i % 5 == 0 else f'오피스디포'),
            transaction_date=datetime.now() - timedelta(days=i),
            classification_status='pending' if i % 4 == 0 else 'classified',
            category_id=3 if i % 3 == 0 else (None if i % 5 == 0 else 1),
            department_id=2 if i % 2 == 0 else 1,
            vendor_id=6 if i % 3 == 0 else (None if i % 5 == 0 else 1)
        ) for i in range(100)
    ]
    
    db.session.add_all(sample_transactions)
    db.session.commit()
    
    # 샘플 알림 데이터
    sample_alerts = [
        Alert(
            title='예산 초과 경고',
            message='개발팀의 이번 달 지출이 예산의 85%에 달했습니다.',
            alert_type='budget',
            severity='warning'
        ),
        Alert(
            title='계약 만료 임박',
            message='SKT 통신 서비스 계약이 30일 후 만료됩니다.',
            alert_type='contract',
            severity='info'
        ),
        Alert(
            title='이상거래 감지',
            message='평소보다 큰 금액의 거래가 감지되었습니다. (1,500,000원)',
            alert_type='anomaly',
            severity='warning'
        ),
    ]
    
    db.session.add_all(sample_alerts)
    db.session.commit()
    
    # 샘플 분류 규칙
    sample_rules = [
        MappingRule(
            name='스타벅스 자동분류',
            priority=8,
            condition_type='contains',
            condition_field='counterparty',
            condition_value='스타벅스',
            target_category_id=3,
            target_vendor_id=6
        ),
        MappingRule(
            name='사무용품 자동분류',
            priority=7,
            condition_type='contains',
            condition_field='description',
            condition_value='사무용품',
            target_category_id=1,
            target_department_id=1,
            target_vendor_id=1
        ),
    ]
    
    db.session.add_all(sample_rules)
    db.session.commit()

def create_tables():
    """앱 시작시 테이블 생성 및 초기 데이터 로드"""
    db.create_all()
    init_sample_data()

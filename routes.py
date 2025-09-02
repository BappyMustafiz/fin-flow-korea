from flask import render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime, timedelta, date
from sqlalchemy import func, desc, extract
from app import app, db
from models import (Institution, Account, Transaction, Category, Department, 
                   Vendor, MappingRule, Contract, AuditLog, Alert, Consent)
import json
import re

@app.route('/')
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
def connections():
    """연결 관리 - 금융기관 연결 현황"""
    institutions = Institution.query.all()
    consents = Consent.query.join(Institution).all()
    
    return render_template('connections.html', 
                         institutions=institutions,
                         consents=consents)

@app.route('/connect/<institution_code>')
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
def accounts():
    """계정 관리"""
    accounts = Account.query.join(Institution).all()
    departments = Department.query.all()
    
    return render_template('accounts.html', 
                         accounts=accounts,
                         departments=departments)

@app.route('/transactions')
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
def edit_transaction(transaction_id):
    """거래 내역 편집"""
    transaction = Transaction.query.get_or_404(transaction_id)
    
    if request.method == 'POST':
        transaction.category_id = request.form.get('category_id') or None
        transaction.department_id = request.form.get('department_id') or None
        transaction.vendor_id = request.form.get('vendor_id') or None
        transaction.description = request.form.get('description', transaction.description)
        transaction.classification_status = 'manual'
        
        db.session.commit()
        flash('거래 내역이 수정되었습니다.', 'success')
        return redirect(url_for('transactions'))
    
    categories = Category.query.all()
    departments = Department.query.all()
    vendors = Vendor.query.all()
    
    return render_template('edit_transaction.html',
                         transaction=transaction,
                         categories=categories,
                         departments=departments,
                         vendors=vendors)

@app.route('/rules')
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
def settings():
    """설정 및 알림 - alerts.html로 리다이렉트"""
    return redirect(url_for('alerts'))

@app.route('/alerts')
def alerts():
    """알림 관리"""
    alerts = Alert.query.order_by(desc(Alert.created_at)).limit(50).all()
    return render_template('alerts.html', alerts=alerts)

@app.route('/audit')
def audit():
    """감사 로그"""
    return render_template('audit.html')

@app.route('/init_data')
def init_data():
    """샘플 데이터 초기화"""
    init_sample_data()
    flash('샘플 데이터가 생성되었습니다.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/alert/<int:alert_id>/read')
def mark_alert_read(alert_id):
    """알림 읽음 처리"""
    alert = Alert.query.get_or_404(alert_id)
    alert.is_read = True
    db.session.commit()
    
    return redirect(url_for('alerts'))

# API 엔드포인트들

@app.route('/api/dashboard/chart-data')
def api_dashboard_chart_data():
    """대시보드 차트 데이터 API"""
    # 최근 7일 일별 현금흐름
    end_date = date.today()
    start_date = end_date - timedelta(days=6)
    
    daily_flow = db.session.query(
        func.date(Transaction.transaction_date).label('date'),
        func.sum(func.case((Transaction.amount > 0, Transaction.amount), else_=0)).label('income'),
        func.sum(func.case((Transaction.amount < 0, func.abs(Transaction.amount)), else_=0)).label('expense')
    ).filter(
        func.date(Transaction.transaction_date) >= start_date
    ).group_by(func.date(Transaction.transaction_date)).order_by('date').all()
    
    dates = []
    income_data = []
    expense_data = []
    
    for flow in daily_flow:
        dates.append(flow.date.strftime('%m/%d'))
        income_data.append(float(flow.income))
        expense_data.append(float(flow.expense))
    
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

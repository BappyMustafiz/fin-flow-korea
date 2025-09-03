from datetime import datetime
from app import db
from sqlalchemy import func
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    """사용자 정보"""
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), default='user')  # admin, user
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'))
    active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    department = db.relationship('Department', backref='users')
    
    def set_password(self, password):
        """패스워드 해시 설정"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """패스워드 확인"""
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        """관리자 권한 확인"""
        return self.role == 'admin'
    
    def get_id(self):
        """Flask-Login용 ID 반환"""
        return str(self.id)
    
    @property
    def is_active(self):
        """Flask-Login용 활성 상태 확인"""
        return self.active

class Institution(db.Model):
    """금융기관 정보"""
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), unique=True, nullable=False)  # 기관코드
    name = db.Column(db.String(100), nullable=False)  # 기관명
    type = db.Column(db.String(20), nullable=False)  # bank, card, payment
    logo_url = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    accounts = db.relationship('Account', backref='institution', lazy=True)
    consents = db.relationship('Consent', backref='institution', lazy=True)

class Consent(db.Model):
    """오픈뱅킹 동의 정보"""
    id = db.Column(db.Integer, primary_key=True)
    institution_id = db.Column(db.Integer, db.ForeignKey('institution.id'), nullable=False)
    consent_id = db.Column(db.String(100), unique=True, nullable=False)
    status = db.Column(db.String(20), default='active')  # active, expired, revoked
    scope = db.Column(db.Text)  # 동의 범위
    expires_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Department(db.Model):
    """부서 정보"""
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('department.id'))
    budget = db.Column(db.Numeric(15, 2))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Self-referential relationship
    children = db.relationship('Department', backref=db.backref('parent', remote_side=[id]))

class Account(db.Model):
    """계좌 정보"""
    id = db.Column(db.Integer, primary_key=True)
    institution_id = db.Column(db.Integer, db.ForeignKey('institution.id'), nullable=False)
    account_number = db.Column(db.String(50), nullable=False)
    account_name = db.Column(db.String(100), nullable=False)
    account_type = db.Column(db.String(20), nullable=False)  # checking, savings, credit, etc.
    balance = db.Column(db.Numeric(15, 2), default=0)
    currency = db.Column(db.String(3), default='KRW')
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    transactions = db.relationship('Transaction', backref='account', lazy=True)
    department = db.relationship('Department', backref='accounts')

class Category(db.Model):
    """거래 분류 카테고리"""
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Self-referential relationship
    children = db.relationship('Category', backref=db.backref('parent', remote_side=[id]))

class Vendor(db.Model):
    """공급업체/거래처 정보"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    business_number = db.Column(db.String(20))  # 사업자번호
    contact_info = db.Column(db.Text)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    category = db.relationship('Category', backref='vendors')

class Transaction(db.Model):
    """거래 내역"""
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    transaction_id = db.Column(db.String(100), unique=True, nullable=False)  # 외부 거래 ID
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    currency = db.Column(db.String(3), default='KRW')
    transaction_type = db.Column(db.String(20), nullable=False)  # debit, credit
    description = db.Column(db.Text)
    counterparty = db.Column(db.String(200))  # 거래 상대방
    transaction_date = db.Column(db.DateTime, nullable=False)
    processed_date = db.Column(db.DateTime)
    
    # Classification fields
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'))
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendor.id'))
    classification_status = db.Column(db.String(20), default='pending')  # pending, classified, manual
    
    # Split transaction fields
    is_active = db.Column(db.Boolean, default=True)  # 분할 후 원본은 비활성화
    split_parent_id = db.Column(db.Integer, db.ForeignKey('transaction.id'))  # 분할된 거래의 원본 ID
    
    # Metadata
    raw_data = db.Column(db.Text)  # 원본 데이터 JSON
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    category = db.relationship('Category', backref='transactions')
    department = db.relationship('Department', backref='transactions')
    vendor = db.relationship('Vendor', backref='transactions')

class MappingRule(db.Model):
    """거래 자동 분류 규칙"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    priority = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    
    # Condition fields
    condition_type = db.Column(db.String(20), nullable=False)  # contains, equals, regex, amount_range
    condition_field = db.Column(db.String(50), nullable=False)  # description, counterparty, amount
    condition_value = db.Column(db.Text, nullable=False)
    
    # Action fields
    target_category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    target_department_id = db.Column(db.Integer, db.ForeignKey('department.id'))
    target_vendor_id = db.Column(db.Integer, db.ForeignKey('vendor.id'))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    target_category = db.relationship('Category', backref='mapping_rules')
    target_department = db.relationship('Department', backref='mapping_rules')
    target_vendor = db.relationship('Vendor', backref='mapping_rules')

class Contract(db.Model):
    """계약 정보"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendor.id'))
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'))
    contract_amount = db.Column(db.Numeric(15, 2))
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='active')  # active, expired, terminated
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    vendor = db.relationship('Vendor', backref='contracts')
    department = db.relationship('Department', backref='contracts')

class AuditLog(db.Model):
    """감사 로그"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(100))  # 사용자 ID
    action = db.Column(db.String(100), nullable=False)
    table_name = db.Column(db.String(50))
    record_id = db.Column(db.Integer)
    old_values = db.Column(db.Text)  # JSON
    new_values = db.Column(db.Text)  # JSON
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Alert(db.Model):
    """알림 정보"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    alert_type = db.Column(db.String(20), nullable=False)  # budget, contract, anomaly
    severity = db.Column(db.String(10), default='info')  # info, warning, error
    is_read = db.Column(db.Boolean, default=False)
    related_table = db.Column(db.String(50))
    related_id = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AlertSetting(db.Model):
    """사용자 정의 알림 설정"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    alert_type = db.Column(db.String(20), nullable=False)  # custom, budget, contract, anomaly
    condition = db.Column(db.Text, nullable=False)  # 사용자가 입력한 조건 텍스트
    
    # 파싱된 조건 필드들 (MappingRule과 유사)
    condition_type = db.Column(db.String(20))  # contains, equals, regex, amount_range
    condition_field = db.Column(db.String(50))  # description, counterparty, amount
    condition_value = db.Column(db.Text)
    
    # 알림 설정
    severity = db.Column(db.String(10), default='info')  # info, warning, error
    channel = db.Column(db.String(20), default='system')  # system, email, sms
    is_active = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CategoryBudget(db.Model):
    """분류별 예산 정보"""
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    budget_amount = db.Column(db.Numeric(15, 2), nullable=False)
    period_type = db.Column(db.String(10), default='monthly')  # monthly, yearly
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer)  # null for yearly budgets
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    category = db.relationship('Category', backref='budgets')

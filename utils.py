from datetime import datetime, date
import re
from models import MappingRule, Transaction

def apply_classification_rules(transaction):
    """거래에 분류 규칙 적용"""
    rules = MappingRule.query.filter_by(is_active=True).order_by(MappingRule.priority.desc()).all()
    
    for rule in rules:
        if check_rule_condition(transaction, rule):
            # 규칙 조건에 맞으면 분류 적용
            if rule.target_category_id:
                transaction.category_id = rule.target_category_id
            if rule.target_department_id:
                transaction.department_id = rule.target_department_id
            if rule.target_vendor_id:
                transaction.vendor_id = rule.target_vendor_id
            
            transaction.classification_status = 'classified'
            return True
    
    return False

def check_rule_condition(transaction, rule):
    """규칙 조건 확인"""
    field_value = getattr(transaction, rule.condition_field, '')
    if field_value is None:
        field_value = ''
    
    field_value = str(field_value).lower()
    condition_value = rule.condition_value.lower()
    
    if rule.condition_type == 'contains':
        return condition_value in field_value
    elif rule.condition_type == 'equals':
        return field_value == condition_value
    elif rule.condition_type == 'regex':
        try:
            return bool(re.search(condition_value, field_value))
        except re.error:
            return False
    elif rule.condition_type == 'amount_range':
        # condition_value 형식: "min,max" 예: "10000,50000"
        try:
            min_val, max_val = map(float, condition_value.split(','))
            amount = float(transaction.amount)
            return min_val <= abs(amount) <= max_val
        except (ValueError, AttributeError):
            return False
    
    return False

def format_currency(amount):
    """통화 포맷팅"""
    if amount is None:
        return "0원"
    return f"{amount:,.0f}원"

def get_transaction_type_text(transaction_type):
    """거래 유형 텍스트 변환"""
    type_map = {
        'debit': '출금',
        'credit': '입금',
        'transfer': '이체'
    }
    return type_map.get(transaction_type, transaction_type)

def get_classification_status_text(status):
    """분류 상태 텍스트 변환"""
    status_map = {
        'pending': '미분류',
        'classified': '자동분류',
        'manual': '수동분류'
    }
    return status_map.get(status, status)

def get_alert_type_text(alert_type):
    """알림 유형 텍스트 변환"""
    type_map = {
        'budget': '예산',
        'contract': '계약',
        'anomaly': '이상거래'
    }
    return type_map.get(alert_type, alert_type)

def calculate_month_diff(date1, date2):
    """두 날짜 간의 월 차이 계산"""
    return (date1.year - date2.year) * 12 + date1.month - date2.month

def get_color_for_amount(amount):
    """금액에 따른 색상 반환"""
    if amount > 0:
        return 'text-success'  # 수입 - 초록색
    elif amount < 0:
        return 'text-danger'   # 지출 - 빨간색
    else:
        return 'text-muted'    # 0원 - 회색

# 템플릿 필터 등록
from app import app

app.jinja_env.filters['currency'] = format_currency
app.jinja_env.filters['transaction_type'] = get_transaction_type_text
app.jinja_env.filters['classification_status'] = get_classification_status_text
app.jinja_env.filters['alert_type'] = get_alert_type_text
app.jinja_env.filters['amount_color'] = get_color_for_amount

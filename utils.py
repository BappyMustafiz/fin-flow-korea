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

def parse_alert_condition(condition_text):
    """
    사용자 입력 조건을 파싱하여 구조화된 조건으로 변환
    예시: "counterparty contains 스타벅스" -> {'type': 'contains', 'field': 'counterparty', 'value': '스타벅스'}
    """
    condition_text = condition_text.strip()
    
    # 기본 패턴들
    patterns = [
        (r'(\w+)\s+(contains?)\s+(.+)', 'contains'),
        (r'(\w+)\s+(equals?)\s+(.+)', 'equals'),  
        (r'(\w+)\s+(regex)\s+(.+)', 'regex'),
        (r'(\w+)\s+(range)\s+([0-9,]+)', 'amount_range'),
        (r'amount\s+>\s*([0-9]+)', 'amount_gt'),
        (r'amount\s+<\s*([0-9]+)', 'amount_lt'),
    ]
    
    for pattern, condition_type in patterns:
        match = re.search(pattern, condition_text, re.IGNORECASE)
        if match:
            if condition_type == 'amount_gt':
                return {
                    'type': 'amount_range',
                    'field': 'amount', 
                    'value': f"{match.group(1)},9999999999"
                }
            elif condition_type == 'amount_lt':
                return {
                    'type': 'amount_range',
                    'field': 'amount',
                    'value': f"0,{match.group(1)}"
                }
            else:
                return {
                    'type': condition_type,
                    'field': match.group(1).lower(),
                    'value': match.group(3 if condition_type != 'amount_range' else 3)
                }
    
    # 단순 텍스트인 경우 description contains로 처리
    if condition_text:
        return {
            'type': 'contains',
            'field': 'description', 
            'value': condition_text
        }
    
    return None


def generate_condition_from_type(condition_type, condition_value):
    """
    조건 유형과 값으로부터 조건 문자열 생성
    """
    if not condition_type or not condition_value:
        return None
    
    condition_map = {
        'counterparty_contains': f'counterparty contains {condition_value}',
        'counterparty_equals': f'counterparty equals {condition_value}',
        'description_contains': f'description contains {condition_value}',
        'description_equals': f'description equals {condition_value}',
        'amount_greater': f'amount > {condition_value}',
        'amount_less': f'amount < {condition_value}',
        'amount_range': f'amount range {condition_value}'  # condition_value should be "min,max" format
    }
    
    return condition_map.get(condition_type, condition_value)

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

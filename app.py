import os
import logging

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "korean-accounting-secret-key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1) # needed for url_for to generate with https

# Flask-Login 설정
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # type: ignore
login_manager.login_message = '이 페이지에 접근하려면 로그인이 필요합니다.'
login_manager.login_message_category = 'info'

# configure the database, relative to the app instance folder
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///accounting.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
# initialize the app with the extension, flask-sqlalchemy >= 3.0.x
db.init_app(app)

# Custom template filters
@app.template_filter('currency')
def currency_filter(amount):
    """Format amount as Korean currency"""
    if amount is None:
        return "₩0"
    return f"₩{int(amount):,}"

@app.template_filter('date')
def date_filter(date_value):
    """Format date for Korean display"""
    if date_value is None:
        return ""
    if hasattr(date_value, 'strftime'):
        return date_value.strftime('%Y-%m-%d')
    return str(date_value)

@app.template_filter('datetime')
def datetime_filter(datetime_value):
    """Format datetime for Korean display"""
    if datetime_value is None:
        return ""
    if hasattr(datetime_value, 'strftime'):
        return datetime_value.strftime('%Y-%m-%d %H:%M')
    return str(datetime_value)

@app.template_filter('amount_color')
def amount_color_filter(amount):
    """Return CSS class based on amount value"""
    if amount is None or amount == 0:
        return "text-muted"
    elif amount > 0:
        return "text-success"
    else:
        return "text-danger"

@app.template_filter('status_badge')
def status_badge_filter(status):
    """Return Bootstrap badge class for status"""
    status_map = {
        'active': 'bg-success',
        'pending': 'bg-warning',
        'classified': 'bg-primary',
        'manual': 'bg-info',
        'expired': 'bg-secondary',
        'revoked': 'bg-danger',
        'unread': 'bg-warning',
        'read': 'bg-secondary'
    }
    return status_map.get(status, 'bg-secondary')

@app.template_filter('classification_status')
def classification_status_filter(status):
    """Return Korean text for classification status"""
    status_map = {
        'pending': '미분류',
        'classified': '분류완료',
        'manual': '수동분류'
    }
    return status_map.get(status, status)

@app.template_filter('alert_type')
def alert_type_filter(alert_type):
    """Return Korean text for alert types"""
    type_map = {
        'budget': '예산 초과',
        'contract': '계약 만료',
        'anomaly': '이상 거래',
        'classification': '분류 필요'
    }
    return type_map.get(alert_type, alert_type)

@app.after_request
def after_request(response):
    """Add cache-busting headers for development"""
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

with app.app_context():
    # Make sure to import the models here or their tables won't be created
    import models  # noqa: F401
    import routes  # noqa: F401
    
    db.create_all()
    
    # Initialize sample data on first run
    from routes import create_tables
    from models import Institution, User
    if not Institution.query.first():  # Only if no institutions exist
        try:
            create_tables()
        except Exception as e:
            print(f"Sample data initialization error: {e}")
            # Continue anyway as the basic structure should work
    
    # Create default admin user if none exists
    if not User.query.filter_by(role='admin').first():
        admin_user = User()
        admin_user.email = 'admin@company.com'
        admin_user.name = '관리자'
        admin_user.role = 'admin'
        admin_user.set_password('admin123')
        db.session.add(admin_user)
        db.session.commit()
        print("Default admin user created: admin@company.com / admin123")

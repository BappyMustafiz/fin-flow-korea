# Korean Open Banking Accounting System

## Overview

This is a Flask-based Korean Open Banking accounting system designed for managing financial transactions, accounts, and institutional connections. The system provides comprehensive financial management capabilities including transaction classification, budget tracking, department-based accounting, and automated rule-based transaction categorization. It integrates with Korean financial institutions through open banking APIs and provides real-time financial dashboards, reporting, and audit capabilities.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Framework**: Server-side rendered Flask application with Jinja2 templates
- **UI Framework**: Bootstrap 5.3.0 for responsive design and components
- **Icons**: Feather Icons for consistent iconography
- **Charts**: Chart.js for data visualization and financial charts
- **Styling**: Custom CSS with Korean-specific design patterns and typography (Noto Sans KR)
- **Layout**: Fixed navigation with main content area, responsive grid system

### Backend Architecture
- **Framework**: Flask web framework with SQLAlchemy ORM
- **Database ORM**: Flask-SQLAlchemy with DeclarativeBase for modern SQLAlchemy patterns
- **Session Management**: Flask sessions with configurable secret key
- **Proxy Support**: ProxyFix middleware for proper HTTPS URL generation
- **Logging**: Python logging configured at DEBUG level
- **Connection Pooling**: SQLAlchemy connection pool with recycle and pre-ping settings

### Data Storage Solutions
- **Primary Database**: SQLite for development, PostgreSQL-ready via DATABASE_URL environment variable
- **ORM Models**: Comprehensive financial data models including:
  - Institution management (banks, cards, payment services)
  - Account management with multi-currency support
  - Transaction tracking with classification status
  - Department-based budget allocation
  - Vendor and contract management
  - Audit logging and alert system
  - Consent management for open banking

### Authentication and Authorization
- **Session-based Authentication**: Flask sessions for user state management
- **Open Banking Consent**: Structured consent management for financial institution access
- **Audit Trail**: Comprehensive logging of user actions and system changes
- **Security Headers**: ProxyFix for proper proxy header handling

### Transaction Classification System
- **Automated Rules Engine**: Rule-based transaction classification with priority system
- **Classification Types**: Contains, equals, regex, and amount range matching
- **Status Tracking**: Pending, classified, and manual classification states
- **Bulk Processing**: Utilities for applying classification rules to transactions

## External Dependencies

### Frontend Dependencies
- **Bootstrap 5.3.0**: UI framework via CDN
- **Feather Icons 4.29.0**: Icon library via CDN
- **Chart.js**: Data visualization library via CDN

### Backend Dependencies
- **Flask**: Web framework
- **Flask-SQLAlchemy**: Database ORM integration
- **SQLAlchemy**: Database toolkit with DeclarativeBase
- **Werkzeug**: WSGI utilities including ProxyFix middleware

### Financial Integration
- **Korean Open Banking APIs**: Integration points for financial institutions
- **Multi-institution Support**: Banks, credit cards, and payment services
- **Real-time Data Sync**: Account balance and transaction synchronization

### Database Integration
- **SQLite**: Development database (default)
- **PostgreSQL**: Production database support via environment configuration
- **Connection Management**: Automatic connection pooling and health checks
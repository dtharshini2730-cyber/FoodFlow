import os
from decimal import Decimal
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'foodflow-erp-secure-secret-key-2024-tiruchi'
    
    raw_db_url = os.environ.get('DATABASE_URL') or \
        'postgresql+psycopg2://postgres:postgres@localhost:5432/foodflow_db'
    if raw_db_url.startswith('postgresql://'):
        raw_db_url = raw_db_url.replace('postgresql://', 'postgresql+psycopg2://', 1)
    SQLALCHEMY_DATABASE_URI = raw_db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Business Defaults (Benchmark parameters)
    SUPPLIER_FACTORY_NAME = os.environ.get('FACTORY_NAME') or 'Sri Murugan Food Products'
    SUPPLIER_FACTORY_ADDRESS = os.environ.get('FACTORY_ADDRESS') or \
        '12/4 Industrial Estate, Thuvakudi, Tiruchirappalli, Tamil Nadu - 620015'
    SUPPLIER_FACTORY_STATE = os.environ.get('FACTORY_STATE') or 'Tamil Nadu'
    SUPPLIER_GSTIN = os.environ.get('FACTORY_GSTIN') or '33AABCF9876Q1Z2'
    
    # Default GST Exercise Rate for packaged snacks benchmark (5%)
    DEFAULT_GST_RATE = Decimal('5.0')
    # Default Production Variance Tolerance (3%)
    DEFAULT_TOLERANCE_PCT = Decimal('3.0')
    
    # Pagination
    ITEMS_PER_PAGE = 15
    
    # Session Security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours


class TestConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    # Use dedicated test DB if available, fallback to in-memory/test postgres
    raw_test_db_url = os.environ.get('TEST_DATABASE_URL') or \
        'postgresql+psycopg2://postgres:postgres@localhost:5432/foodflow_test_db'
    if raw_test_db_url.startswith('postgresql://'):
        raw_test_db_url = raw_test_db_url.replace('postgresql://', 'postgresql+psycopg2://', 1)
    SQLALCHEMY_DATABASE_URI = raw_test_db_url


config = {
    'development': Config,
    'testing': TestConfig,
    'default': Config
}

import os # System files and OS utilities
from pathlib import Path # Pathlib for file system path manipulations

class Config(object):
    # sets the base directory of the web app
    BASE_DIR = Path(__file__).resolve().parent
    
    # define user roles
    USERS_ROLES  = { 'ADMIN'  :1 , 'USER'      : 2 }
    # define user status
    USERS_STATUS = { 'ACTIVE' :1 , 'SUSPENDED' : 2 }
    
    # celery 
    CELERY_BROKER_URL     = "redis://localhost:6379"
    CELERY_RESULT_BACKEND = "redis://localhost:6379"
    CELERY_HOSTMACHINE    = "celery@app-generator"

    # Set up the App SECRET_KEY
    SECRET_KEY  = os.getenv('SECRET_KEY', 'S3cret_999')

    # OpenAI API Key for ChatGPT integration
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', None)

    # SQLAlchemy configuration for database connection and ORM
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Database connection parameters retrieved from environment variables
    DB_ENGINE   = os.getenv('DB_ENGINE'   , None)
    DB_USERNAME = os.getenv('DB_USERNAME' , None)
    DB_PASS     = os.getenv('DB_PASS'     , None)
    DB_HOST     = os.getenv('DB_HOST'     , None)
    DB_PORT     = os.getenv('DB_PORT'     , None)
    DB_NAME     = os.getenv('DB_NAME'     , None)

    # Flag to determine whether to use SQLite as the database
    USE_SQLITE  = True 

    # try to set up a Relational DBMS
    if DB_ENGINE and DB_NAME and DB_USERNAME:

        try:
            
            # Relational DBMS: PSQL, MySql
            SQLALCHEMY_DATABASE_URI = '{}://{}:{}@{}:{}/{}'.format(
                DB_ENGINE,
                DB_USERNAME,
                DB_PASS,
                DB_HOST,
                DB_PORT,
                DB_NAME
            ) 

            USE_SQLITE  = False

        except Exception as e:

            print('> Error: DBMS Exception: ' + str(e) )
            print('> Fallback to SQLite ')    

    if USE_SQLITE:

        # This will create a file in <app> FOLDER
        SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'db.sqlite3')
        SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Dynamic Data Table Mapping
    DYNAMIC_DATATB = {
        "products": "apps.models.Product"
    }

    # retrieves CDN domain and CDN HTTPS status from environment variables
    CDN_DOMAIN = os.getenv('CDN_DOMAIN')
    CDN_HTTPS = os.getenv('CDN_HTTPS', True)

    # retrieves the currency, payment type, and state from environment variables with default values
    CURRENCY = os.getenv("CURRENCY", "AED")
    PAYMENT_TYPE = os.getenv("PAYMENT_TYPE", "STANDARD")
    STATE = os.getenv("STATE", "DRAFT")

# Production configuration class that inherits from the base Config class
class ProductionConfig(Config):
    DEBUG = False

    # Security
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_DURATION = 3600

# Debug configuration class that inherits from the base Config class
class DebugConfig(Config):
    DEBUG = True

# Load all possible configurations
config_dict = {
    'Production': ProductionConfig,
    'Debug'     : DebugConfig
}

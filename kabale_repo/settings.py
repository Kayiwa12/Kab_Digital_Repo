import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables
load_dotenv(BASE_DIR / '.env')

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'kabale-idr-discovery-secure-key-default-382910')
DEBUG = os.getenv('DJANGO_DEBUG', 'True').lower() in ('true', '1', 'yes')

allowed_hosts_str = os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,0.0.0.0,.run.app,.vercel.app,*')
ALLOWED_HOSTS = [h.strip() for h in allowed_hosts_str.split(',') if h.strip()]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'dspace_integration.apps.DspaceIntegrationConfig',
    'research.apps.ResearchConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]

ROOT_URLCONF = 'kabale_repo.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'research' / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'research.context_processors.repo_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'kabale_repo.wsgi.application'

# Serverless / Read-only filesystem support (Vercel, AWS Lambda, etc.)
if os.getenv('VERCEL') == '1' or not os.access(BASE_DIR, os.W_OK):
    import shutil
    tmp_db = Path('/tmp/db.sqlite3')
    orig_db = BASE_DIR / 'db.sqlite3'
    if not tmp_db.exists() and orig_db.exists():
        try:
            shutil.copy2(orig_db, tmp_db)
        except Exception:
            pass
    DB_FILE = tmp_db if tmp_db.exists() else orig_db
else:
    DB_FILE = BASE_DIR / 'db.sqlite3'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': DB_FILE,
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'research' / 'static',
]
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# DSpace Repository Configuration
DSPACE_API_BASE_URL = os.getenv('DSPACE_API_BASE_URL', 'https://backend.kab.ac.ug/server/api').rstrip('/')
DSPACE_REPOSITORY_FRONTEND = os.getenv('DSPACE_REPOSITORY_FRONTEND', 'https://idr.kab.ac.ug').rstrip('/')
DSPACE_TARGET_COMMUNITY_UUID = os.getenv('DSPACE_TARGET_COMMUNITY_UUID', '95cbea8b-fdc6-4d8a-9f20-d51ad2814f12')
DSPACE_REQUEST_TIMEOUT = int(os.getenv('DSPACE_REQUEST_TIMEOUT', '20'))
DSPACE_PAGE_SIZE = int(os.getenv('DSPACE_PAGE_SIZE', '20'))

# Security settings
CSRF_TRUSTED_ORIGINS = [
    'https://*.run.app',
    'https://*.google.com',
    'https://*.aistudio.google.com',
    'https://*.googleusercontent.com',
    'https://*.vercel.app',
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'http://localhost:8888',
    'http://127.0.0.1:8888',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]
X_FRAME_OPTIONS = 'ALLOWALL'
SECURE_CROSS_ORIGIN_OPENER_POLICY = None
LOGIN_URL = '/admin/login/'
LOGIN_REDIRECT_URL = '/admin-dashboard/'

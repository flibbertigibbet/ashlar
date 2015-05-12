
"""
Django settings for use when testing Ashlar
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os

DEVELOP = True
PRODUCTION = False

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECRET_KEY = 'testing_travis!'

ALLOWED_HOSTS = []

# Application definition

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.gis',
    'rest_framework',

    'django_extensions',

    'ashlar'
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
)

ROOT_URLCONF = 'ashlar.urls'

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'postgres',
        'HOST': 'localhost',
        'PORT': 5432,
        'USER': 'postgres',
        'PASSWORD': '',
        'CONN_MAX_AGE': 3600,  # in seconds
    }
}

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


STATIC_URL = '/static/'

MEDIA_URL = '/media/'
MEDIA_ROOT = '/tmp'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': ('rest_framework.authentication.SessionAuthentication',),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_FILTER_BACKENDS': ('rest_framework.filters.DjangoFilterBackend',),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 10,
}

ASHLAR = {
    # It is suggested to change this if you know that your data will be limited to
    # a certain part of the world, for example to a UTM Grid projection or a state
    # plane.
    'SRID': 3857,
}
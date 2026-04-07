from pathlib import Path
import os,json
from datetime import timedelta
import pymysql
pymysql.install_as_MySQLdb()


DEBUG = True

BASE_DIR = Path(__file__).resolve().parent.parent
# SECRET_KEY = 'django-insecure-gwy43#w#m@sig#0o(3rsxphv6ttz$1e+tfhn09_#+vv(tpkf+7'
SECRET_KEY = 'django-insecure-&%+%gt$iqu^raos_nhr^62*bt8oj$ri3@c7nkypd9(n71-jx*p'
ROOT_URLCONF = 'ffwc_django_project.urls'
WSGI_APPLICATION = 'ffwc_django_project.wsgi.application'


CORS_ALLOW_ALL_ORIGINS = True
ALLOWED_HOSTS = ['*']
CORS_ORIGIN_ALLOW_ALL = True
CORS_ALLOW_METHODS = ('*',)  # Allow all HTTP methods
CORS_ALLOW_HEADERS = ('*',)  # Allow all headers
CORS_ALLOW_CREDENTIALS = True  # Allow credentials in cross-origin requests

CSRF_TRUSTED_ORIGINS = [
    'https://api3.ffwc.gov.bd',
    'https://ffwc.gov.bd'
]


# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Installed Packages
    'corsheaders',
    'rest_framework',
    'rest_framework_simplejwt',
    'import_export',

    'django_celery_results',
    'celery_progress',

    # Defined Apps
    'data_load',
    'indian_stations',
    'userauth',
    'fileuploads',
    
    # Shaif added app
    'app_user_mobile',
    'app_bulletin',
    'app_crontab',
    'app_data_deletion',
    'app_dissemination',
    'app_emails',
    'app_middlewares',
    'app_subscriptions',
    'app_visualization',
    'app_water_watch_mobile',
    'app_mobile_static_data',
    
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'app_user_mobile.authentication.MobileJWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        # 'rest_framework.authentication.SessionAuthentication',
    ],

    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ),
    
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend'],
    
    'TITLE': 'FFWC API VIEWS'

}

REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = (
    'rest_framework.renderers.JSONRenderer',
    'rest_framework.renderers.BrowsableAPIRenderer',
)
REST_FRAMEWORK['TITLE'] = 'FFWC API VIEWS'

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',  # Default backend
    'app_user_mobile.backends.MobileAuthBackend',         # Mobile backend
]

# SIMPLE_JWT = {
#     'ACCESS_TOKEN_LIFETIME': timedelta(days=365),     #minutes=60
#     'REFRESH_TOKEN_LIFETIME': timedelta(days=400),
#     'ROTATE_REFRESH_TOKENS': False,
#     'BLACKLIST_AFTER_ROTATION': False,
#     'UPDATE_LAST_LOGIN': True,

#     'ALGORITHM': 'HS256',   # HS256
#     'SIGNING_KEY': SECRET_KEY,
#     'VERIFYING_KEY': None,
#     'AUDIENCE': None,
#     'ISSUER': None,
#     'JWK_URL': None,
#     'LEEWAY': 0,

#     'AUTH_HEADER_TYPES': ('Bearer',),
#     'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
#     'USER_ID_FIELD': 'id',
#     'USER_ID_CLAIM': 'user_id',
#     'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',

#     'AUTH_TOKEN_CLASSES': (
#         # 'rest_framework_simplejwt.tokens.AccessToken',
#         'rest_framework_simplejwt.tokens.AccessToken',
#         'app_user_mobile.tokens.MobileAccessToken',  # We'll create this next
#     ),
#     'TOKEN_TYPE_CLAIM': 'token_type',
#     'TOKEN_USER_CLASS': 'rest_framework_simplejwt.models.TokenUser',

#     'JTI_CLAIM': 'jti',
# }

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=7),
    # "ACCESS_TOKEN_LIFETIME": timedelta(minutes=5),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=90),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": False,

    "ALGORITHM": "HS512",
    "VERIFYING_KEY": "",
    "AUDIENCE": None,
    "ISSUER": None,
    "JSON_ENCODER": None,
    "JWK_URL": None,
    "LEEWAY": 0,

    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "USER_AUTHENTICATION_RULE": "rest_framework_simplejwt.authentication.default_user_authentication_rule",

    # "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    'AUTH_TOKEN_CLASSES': (
        # 'rest_framework_simplejwt.tokens.AccessToken',
        'rest_framework_simplejwt.tokens.AccessToken',
        'app_user_mobile.tokens.MobileAccessToken',  # We'll create this next
    ),
    "TOKEN_TYPE_CLAIM": "token_type",
    "TOKEN_USER_CLASS": "rest_framework_simplejwt.models.TokenUser",

    "JTI_CLAIM": "jti",

    "SLIDING_TOKEN_REFRESH_EXP_CLAIM": "refresh_exp",
    "SLIDING_TOKEN_LIFETIME": timedelta(days=7),
    # "SLIDING_TOKEN_LIFETIME": timedelta(minutes=5),
    "SLIDING_TOKEN_REFRESH_LIFETIME": timedelta(days=90),

    "TOKEN_OBTAIN_SERIALIZER": "rest_framework_simplejwt.serializers.TokenObtainPairSerializer",
    "TOKEN_REFRESH_SERIALIZER": "rest_framework_simplejwt.serializers.TokenRefreshSerializer",
    "TOKEN_VERIFY_SERIALIZER": "rest_framework_simplejwt.serializers.TokenVerifySerializer",
    "TOKEN_BLACKLIST_SERIALIZER": "rest_framework_simplejwt.serializers.TokenBlacklistSerializer",
    "SLIDING_TOKEN_OBTAIN_SERIALIZER": "rest_framework_simplejwt.serializers.TokenObtainSlidingSerializer",
    "SLIDING_TOKEN_REFRESH_SERIALIZER": "rest_framework_simplejwt.serializers.TokenRefreshSlidingSerializer",
}


MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # Added for CORS handling
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]



TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases
DATABASES = DATABASES = json.load(open(os.path.join(BASE_DIR,'dbconfig.json'),'r'))

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]


# Internationalization
# LANGUAGE_CODE = 'en-us'
# # TIME_ZONE = 'UTC'
# TIME_ZONE = 'Asia/Dhaka'
# USE_I18N = True
# USE_TZ = True


LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True
DJANGO_CELERY_BEAT_TZ_AWARE = False


STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [os.path.join(BASE_DIR, "static"),]


MEDIA_URL = '/assets/'
MEDIA_ROOT = os.path.join(BASE_DIR,'assets')

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'



# Celery Configuration
CELERY_BROKER_URL = 'redis://localhost:6379/0'  # Use Redis as the broker
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0' # Store results in Redis
CELERY_ACCEPT_CONTENT = ['json'] # Accept JSON content
CELERY_TASK_SERIALIZER = 'json' # Serialize tasks as JSON
CELERY_RESULT_SERIALIZER = 'json' # Serialize results as JSON
CELERY_TIMEZONE = 'Asia/Dhaka' # IMPORTANT: Match your Django TIME_ZONE
CELERY_TASK_TRACK_STARTED = True # Enable tracking task 'STARTED' state
CELERY_TASK_STATUS_ON_EXCEPTION = True # Store task state as FAILURE on exception



# FFWC-RIMES-LEOTECH API Configuration
FFWC_BASE_URL = "https://sms.ffwc.gov.bd/hydro/api/data_share"
FFWC_TOKEN = "9f7a71621336b31d92801f394c730470"

# RIMES-FFWC SMS API Configuration
SMS_BASE_URL = "http://114.31.28.82/api/v1"
SMS_USERID = "urimes"
SMS_APIKEY = "9a02481013b31c9d234d1b50f7d81087"

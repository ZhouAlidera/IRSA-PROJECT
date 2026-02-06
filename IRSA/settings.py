
from pathlib import Path
from dotenv import load_dotenv
import os
import sys

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


sys.path.append(os.path.join(BASE_DIR,"Apps"))


load_dotenv()
SECRET_KEY = os.getenv('SECRET_KEY')
DEBUG = os.getenv('DEBUG') == 'True'

ALLOWED_HOSTS = []

import os

# Application definition

INSTALLED_APPS = [
    # "unfold",
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    "django_browser_reload",
    
    'utilisateurs',
    'declarations',
    'NifAPI',
    'Portail_employes',
    
    'tailwind',
    'theme',
    'formtools',
    'widget_tweaks',
    'rest_framework',
    'corsheaders',
    'axes',
]

AUTH_USER_MODEL = 'utilisateurs.UserCustom'

TAILWIND_APP_NAME = 'theme'

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'axes.middleware.AxesMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    "django_browser_reload.middleware.BrowserReloadMiddleware",
]

JAZZMIN_SETTINGS = {
    # --- Titres et Branding ---
    "site_title": "Portail Fiscal",
    "site_header": "Direction des Impôts",
    "site_brand": "Administration Fiscale",
    "site_logo": None,  # Tu peux mettre le chemin vers ton logo : "img/logo.png"
    "welcome_sign": "Bienvenue Agent Fiscal",
    "copyright": "Gouvernement - Ministère des Finances",

    # --- Recherche Globale ---
    # Permet de chercher un employeur directement depuis la barre du haut
    "search_model": ["utilisateurs.Employeur"], 

    # --- Menu Utilisateur (Haut à droite) ---
    "usermenu_links": [
        {"name": "Support Technique", "url": "/support", "new_window": True},
        {"model": "auth.user"}
    ],

    # --- Menu Latéral (Sidebar) ---
    "show_sidebar": True,
    "navigation_expanded": True,
    "hide_apps": [],
    "hide_models": [],

    # Groupement des menus par métier pour l'agent
    "side_menu_groups": [
        {
            "name": "Gestion des Contribuables",
            "models": ["utilisateurs.Employeur", "auth.User"],
        },
        {
            "name": "Opérations Fiscales",
            "models": [
                "declarations.PeriodeFiscale", 
                "declarations.Declaration", # Ajoute tes autres modèles ici
            ],
        },
    ],

    # --- Icônes (Font Awesome) ---
    "icons": {
        "auth": "fas fa-users-cog",
        "auth.user": "fas fa-user-tie",
        "utilisateurs.Employeur": "fas fa-building",
        "declarations.PeriodeFiscale": "fas fa-calendar-check",
        "declarations.Declaration": "fas fa-file-invoice-dollar",
    },
    "default_icon_parents": "fas fa-chevron-circle-right",
    "default_icon_children": "fas fa-circle",

    # --- Liens Rapides (Top Menu) ---
    "topmenu_links": [
        {"name": "Accueil", "url": "admin:index"},
        {"name": "Nouvelle Période", "model": "declarations.PeriodeFiscale"},
    ],

    # --- Personnalisation Visuelle ---
    "show_ui_builder": False,  # Désactivé pour la production
    
    # IMPORTANT : Chemin vers ton CSS Tailwind compilé pour styliser ton futur Dashboard
    # "custom_css": "css/output.css", 
    "custom_js": None,
}

# Configuration optionnelle pour un look plus "Institutionnel" (Bleu/Gris)
JAZZMIN_UI_CUSTOMIZER = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": "navbar-dark",
    "accent": "accent-primary",
    "navbar": "navbar-dark navbar-primary", # Bleu pro
    "no_navbar_border": False,
    "navbar_fixed": True,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": True,
    "sidebar": "sidebar-dark-primary",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": False,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "theme": "default",
    "dark_mode_theme": None,
    "button_classes": {
        "primary": "btn-primary",
        "secondary": "btn-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success"
    }
}
ROOT_URLCONF = 'IRSA.urls'

CORS_ALLOW_ALL_ORIGINS = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE = 1800
SESSION_SAVE_EVERY_REQUEST = True

REST_FRAMEWORK = {
    # Authentification par défaut (optionnel selon ton projet)
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    
    # Permissions par défaut
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',  # tu peux mettre AllowAny pour un endpoint public
    ],
    
    # Pagination par défaut (optionnel)
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
    
    # Format de rendu (JSON par défaut)
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
    
    # Filtres (si tu veux faire recherche ou filtre)
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
    ),
    
    # Format de parsers
    'DEFAULT_PARSER_CLASSES': (
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser',
    ),
}

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'IRSA.wsgi.application'


CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'",) 

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'axes.backends.AxesBackend', 
]

AXES_FAILURE_LIMIT = 5            # Bloquer après 5 tentatives
AXES_COOLOFF_TIME = 1             # Temps de blocage en heures
AXES_LOCK_OUT_BY_COMBINATION = True # Bloque la combinaison IP + Utilisateur

# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

# AUTH_PASSWORD_VALIDATORS = [
#     {
#         'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
#     },
#     {
#         'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
#     },
#     {
#         'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
#     },
#     {
#         'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
#     },
# ]

SESSION_ENGINE = "django.contrib.sessions.backends.db"

# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'fr-fr'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'

STATIC_ROOT = os.path.join(BASE_DIR,'staticfiles')

STATICFILES_DIRS=[os.path.join(BASE_DIR,'STATIC')]

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")
# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Snippet for a Django project's settings.py.
# The middleware reads TINYOWL (kwargs for TinyOwl) or TINYOWL_CLIENT (an existing client).
import os

TINYOWL = {
    "api_key": os.environ["TINYOWL_API_KEY"],
    "project_secret": os.environ["TINYOWL_PROJECT_SECRET"],
}

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "tinyowl.integrations.django_middleware.TinyOwlDjangoMiddleware",
]

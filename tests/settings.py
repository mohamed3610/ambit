SECRET_KEY = "test-only"
INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "ambit",
    "tests.orgtest",
]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True

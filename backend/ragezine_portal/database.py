from django.core.exceptions import ImproperlyConfigured


class SQLiteHandler:
    def configuration(self, base_dir, environ):
        return {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": base_dir / "db.sqlite3",
        }

    def residence_field(self):
        from django.db import models

        return models.JSONField(default=list, blank=True)


class PostgreSQLHandler:
    def configuration(self, base_dir, environ):
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": environ.get("POSTGRES_DB", "ragezine_portal"),
            "USER": environ.get("POSTGRES_USER", "postgres"),
            "PASSWORD": environ.get("POSTGRES_PASSWORD", "postgres"),
            "HOST": environ.get("POSTGRES_HOST", "127.0.0.1"),
            "PORT": environ.get("POSTGRES_PORT", "5432"),
        }

    def residence_field(self):
        from django.contrib.postgres.fields import ArrayField
        from django.db import models

        return ArrayField(
            base_field=models.CharField(max_length=100),
            default=list,
            blank=True,
        )


def get_database_handler(engine):
    handlers = {
        "sqlite": SQLiteHandler,
        "postgres": PostgreSQLHandler,
        "postgresql": PostgreSQLHandler,
    }
    try:
        return handlers[engine.lower()]()
    except KeyError as exc:
        raise ImproperlyConfigured(f"Unsupported DJANGO_DB_ENGINE: {engine}") from exc

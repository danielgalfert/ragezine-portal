from pathlib import Path

from django.contrib.postgres.fields import ArrayField
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.test import SimpleTestCase

from ragezine_portal.database import PostgreSQLHandler, SQLiteHandler, get_database_handler
from submissions.models import Submission


class DatabaseHandlerTests(SimpleTestCase):
    def test_sqlite_handler_uses_local_database_and_json_residences(self):
        handler = get_database_handler("sqlite")

        self.assertIsInstance(handler, SQLiteHandler)
        self.assertEqual(
            handler.configuration(Path("backend"), {}),
            {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": Path("backend/db.sqlite3"),
            },
        )
        self.assertIsInstance(handler.residence_field(), models.JSONField)

    def test_postgres_handler_preserves_array_residences(self):
        handler = get_database_handler("postgresql")

        self.assertIsInstance(handler, PostgreSQLHandler)
        self.assertEqual(
            handler.configuration(Path("backend"), {"POSTGRES_DB": "submissions"})["NAME"],
            "submissions",
        )
        self.assertIsInstance(handler.residence_field(), ArrayField)

    def test_unknown_engine_fails_fast(self):
        with self.assertRaisesMessage(ImproperlyConfigured, "Unsupported DJANGO_DB_ENGINE"):
            get_database_handler("mysql")

    def test_model_uses_the_selected_handler_field(self):
        actual = Submission._meta.get_field("countries_residence")
        expected = settings.DATABASE_HANDLER.residence_field()
        self.assertIsInstance(actual, type(expected))

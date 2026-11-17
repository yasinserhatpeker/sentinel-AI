from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings


class LocalSchemaCommandTests(TestCase):
    @override_settings(DEBUG=True)
    def test_existing_additive_column_is_idempotent(self) -> None:
        output = StringIO()

        call_command("ensure_local_additive_schema", stdout=output)

        self.assertIn("local_additive_schema_already_current", output.getvalue())

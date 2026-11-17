"""Repair explicitly allowlisted additive columns in legacy local databases."""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from demo.models import DetectionDecision


class Command(BaseCommand):
    help = "Ensure allowlisted nullable columns exist after legacy runtime-generated migrations."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("local_additive_schema_repair_requires_debug")

        table = DetectionDecision._meta.db_table
        with connection.cursor() as cursor:
            columns = {column.name for column in connection.introspection.get_table_description(cursor, table)}

        field = DetectionDecision._meta.get_field("normalized_score")
        if field.column in columns:
            self.stdout.write("local_additive_schema_already_current")
            return

        if not field.null:
            raise CommandError("local_additive_schema_field_must_be_nullable")
        with connection.schema_editor() as schema_editor:
            schema_editor.add_field(DetectionDecision, field)
        self.stdout.write(self.style.SUCCESS("local_additive_schema_normalized_score_added"))

# Generated by Django 3.2.5 on 2021-12-08 07:25

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("posthog", "0187_stale_events"),
    ]

    operations = [
        migrations.AddField(
            model_name="persondistinctid",
            name="version",
            field=models.BigIntegerField(blank=True, null=True),
        ),
    ]

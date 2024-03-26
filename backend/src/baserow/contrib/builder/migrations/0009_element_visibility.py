# Generated by Django 4.1.13 on 2024-03-06 15:44

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("builder", "0008_form_validation_changes"),
    ]

    operations = [
        migrations.AddField(
            model_name="element",
            name="visibility",
            field=models.CharField(
                choices=[
                    ("all", "All"),
                    ("logged-in", "Logged In"),
                    ("not-logged", "Not Logged"),
                ],
                default="all",
                max_length=20,
                db_index=True,
            ),
        ),
    ]

# Generated by Django 5.1.7 on 2025-04-01 08:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0003_profile_last_modified_profile_timestamp_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='verification_status',
            field=models.BooleanField(default=False),
        ),
    ]

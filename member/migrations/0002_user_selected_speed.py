# Generated by Django 5.1.7 on 2025-03-24 05:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('member', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='selected_speed',
            field=models.FloatField(blank=True, null=True),
        ),
    ]

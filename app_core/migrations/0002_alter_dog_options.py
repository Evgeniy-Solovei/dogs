# Generated by Django 5.1.4 on 2025-01-03 08:50

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('app_core', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='dog',
            options={'verbose_name': 'Собака', 'verbose_name_plural': 'Собаки'},
        ),
    ]

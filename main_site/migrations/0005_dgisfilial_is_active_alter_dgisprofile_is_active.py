# Generated by Django 5.1.1 on 2024-12-07 13:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main_site', '0004_dgisprofile_is_active'),
    ]

    operations = [
        migrations.AddField(
            model_name='dgisfilial',
            name='is_active',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='dgisprofile',
            name='is_active',
            field=models.BooleanField(default=False),
        ),
    ]

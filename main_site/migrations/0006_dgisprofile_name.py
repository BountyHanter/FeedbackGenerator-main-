# Generated by Django 5.1.1 on 2024-12-09 14:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main_site', '0005_dgisfilial_is_active_alter_dgisprofile_is_active'),
    ]

    operations = [
        migrations.AddField(
            model_name='dgisprofile',
            name='name',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]

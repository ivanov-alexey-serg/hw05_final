# Generated by Django 2.2.16 on 2023-04-27 22:08

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0003_auto_20230309_1327'),
    ]

    operations = [
        migrations.RenameField('Post', 'pub_date', 'created'),
    ]
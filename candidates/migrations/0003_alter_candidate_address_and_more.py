# Generated by Django 4.0.5 on 2022-06-29 15:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('candidates', '0002_alter_candidate_address_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='candidate',
            name='address',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='candidate',
            name='contact_details',
            field=models.JSONField(blank=True, null=True),
        ),
    ]

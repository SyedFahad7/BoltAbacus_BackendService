# Generated manually to add problem_times field to PVPRoomPlayer

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Authentication', '0012_practicequestions_problem_times'),
    ]

    operations = [
        migrations.AddField(
            model_name='pvproomplayer',
            name='problem_times',
            field=models.JSONField(blank=True, default=list),
        ),
    ]

# Generated manually to add problem_times field to PracticeQuestions

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Authentication', '0011_practicequestions_created_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='practicequestions',
            name='problemTimes',
            field=models.JSONField(blank=True, default=list),
        ),
    ]

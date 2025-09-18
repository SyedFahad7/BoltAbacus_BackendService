# Generated manually to add created_at field to PracticeQuestions

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Authentication', '0010_merge_20250919_0306'),
    ]

    operations = [
        migrations.AddField(
            model_name='practicequestions',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
    ]

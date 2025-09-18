# Generated manually to add practice mode settings to PVPRoom

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Authentication', '0008_pvproom_number_of_digits'),
    ]

    operations = [
        migrations.AddField(
            model_name='pvproom',
            name='numberOfDigitsLeft',
            field=models.IntegerField(default=1),
        ),
        migrations.AddField(
            model_name='pvproom',
            name='numberOfDigitsRight',
            field=models.IntegerField(default=1),
        ),
        migrations.AddField(
            model_name='pvproom',
            name='isZigzag',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='pvproom',
            name='numberOfRows',
            field=models.IntegerField(default=2),
        ),
        migrations.AddField(
            model_name='pvproom',
            name='includeSubtraction',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='pvproom',
            name='persistNumberOfDigits',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='pvproom',
            name='includeDecimals',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='pvproom',
            name='audioMode',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='pvproom',
            name='audioPace',
            field=models.CharField(default='normal', max_length=10),
        ),
        migrations.AddField(
            model_name='pvproom',
            name='showQuestion',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='pvproom',
            name='flashcard_speed',
            field=models.IntegerField(default=2500),
        ),
    ]

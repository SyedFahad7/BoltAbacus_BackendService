# Generated manually for PvPRoomResult model

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('Authentication', '0014_add_scheduling_to_personal_goals'),
    ]

    operations = [
        migrations.CreateModel(
            name='PvPRoomResult',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('questions_answered', models.IntegerField(default=0)),
                ('correct_answers', models.IntegerField(default=0)),
                ('total_time', models.FloatField(default=0)),
                ('average_time_per_question', models.FloatField(default=0)),
                ('accuracy_percentage', models.FloatField(default=0)),
                ('speed_per_minute', models.FloatField(default=0)),
                ('score', models.IntegerField(default=0)),
                ('is_winner', models.BooleanField(default=False)),
                ('is_draw', models.BooleanField(default=False)),
                ('problem_times', models.JSONField(blank=True, default=list)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('player', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pvp_room_results', to='Authentication.userdetails', to_field='userId')),
                ('room', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='room_results', to='Authentication.pvproom', to_field='room_id')),
            ],
            options={
                'unique_together': {('room', 'player')},
            },
        ),
        migrations.AddIndex(
            model_name='pvproomresult',
            index=models.Index(fields=['player', 'created_at'], name='Authentication_pvproomresult_player_created_idx'),
        ),
        migrations.AddIndex(
            model_name='pvproomresult',
            index=models.Index(fields=['created_at'], name='Authentication_pvproomresult_created_at_idx'),
        ),
    ]

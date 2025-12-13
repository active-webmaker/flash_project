from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0005_commit'),
    ]

    operations = [
        migrations.AlterField(
            model_name='agent',
            name='agent_id',
            field=models.CharField(max_length=100, primary_key=True, serialize=False),
        ),
        migrations.AddField(
            model_name='agent',
            name='current_job_id',
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.AddField(
            model_name='agent',
            name='telemetry',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='job',
            name='assigned_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='job',
            name='error_message',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='job',
            name='payload',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='job',
            name='progress_log',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name='job',
            name='tool_invocations',
            field=models.JSONField(blank=True, default=list),
        ),
    ]

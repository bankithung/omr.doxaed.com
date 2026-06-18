from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('omr', '0009_question_paper_file'),
    ]
    operations = [
        migrations.AddField(
            model_name='scanjob',
            name='warped_file',
            field=models.FileField(blank=True, null=True, upload_to='scans_warped/'),
        ),
    ]

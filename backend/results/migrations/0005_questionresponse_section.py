from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('assessments', '0004_section_modec'),
        ('results', '0004_publicresultshare'),
    ]

    operations = [
        migrations.AddField(
            model_name='questionresponse',
            name='section',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='question_responses',
                to='assessments.section',
            ),
        ),
        migrations.AddIndex(
            model_name='questionresponse',
            index=models.Index(fields=['student_result', 'section'], name='qresponse_result_section_idx'),
        ),
        migrations.AddField(
            model_name='studentresult',
            name='section_breakdown',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='studentresult',
            name='qualified_all',
            field=models.BooleanField(default=True),
        ),
    ]

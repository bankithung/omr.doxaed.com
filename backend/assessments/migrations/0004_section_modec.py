from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('assessments', '0003_mode_and_template_spec'),
    ]

    operations = [
        migrations.CreateModel(
            name='Section',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(max_length=16)),
                ('label', models.CharField(max_length=255)),
                ('order_index', models.PositiveIntegerField(default=0)),
                ('q_start', models.PositiveIntegerField()),
                ('q_end', models.PositiveIntegerField()),
                ('policy', models.CharField(choices=[('all', 'All'), ('choose_k', 'Choose K')], default='all', max_length=16)),
                ('choose_k', models.PositiveIntegerField(blank=True, null=True)),
                ('test', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sections', to='assessments.test')),
            ],
            options={
                'ordering': ['order_index', 'id'],
            },
        ),
        migrations.CreateModel(
            name='SectionMarkingScheme',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('marks_per_correct', models.DecimalField(decimal_places=4, default=1, max_digits=8)),
                ('negative_marks_per_wrong', models.DecimalField(decimal_places=4, default=0, max_digits=8)),
                ('negative_kind', models.CharField(choices=[('flat', 'Flat'), ('fractional', 'Fractional')], default='flat', max_length=12)),
                ('partial_marking', models.BooleanField(default=False)),
                ('multiple_correct_allowed', models.BooleanField(default=False)),
                ('qualify_pct', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('section', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='marking_scheme', to='assessments.section')),
            ],
        ),
        migrations.AddConstraint(
            model_name='section',
            constraint=models.UniqueConstraint(fields=['test', 'key'], name='uniq_section_test_key'),
        ),
        migrations.AddField(
            model_name='question',
            name='section',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='questions', to='assessments.section'),
        ),
        migrations.AddField(
            model_name='test',
            name='default_options',
            field=models.PositiveSmallIntegerField(default=4),
        ),
        migrations.AlterField(
            model_name='test',
            name='mode',
            field=models.CharField(
                choices=[
                    ('standard', 'Standard'),
                    ('roster_prebubbled', 'Roster (Pre-bubbled roll)'),
                    ('competitive', 'Competitive (Sections)'),
                ],
                default='standard',
                max_length=32,
            ),
        ),
    ]

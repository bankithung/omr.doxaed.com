from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assessments', '0004_section_modec'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sectionmarkingscheme',
            name='marks_per_correct',
            field=models.DecimalField(decimal_places=4, default=1, max_digits=8),
        ),
        migrations.AlterField(
            model_name='sectionmarkingscheme',
            name='negative_marks_per_wrong',
            field=models.DecimalField(decimal_places=4, default=0, max_digits=8),
        ),
    ]

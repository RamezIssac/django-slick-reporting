from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("slick_reporting_dashboard", "0002_savedwidget_restructure"),
    ]

    operations = [
        migrations.AddField(
            model_name="savedwidget",
            name="column_span",
            field=models.PositiveSmallIntegerField(
                default=12,
                help_text="Width of the widget on the dashboard, in Bootstrap's 12-column grid "
                "(12=full row, 6=half, 4=third, 3=quarter). Lets widgets sit side by side.",
            ),
        ),
    ]

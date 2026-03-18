from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("recommendations", "0001_initial"),
    ]

    operations = [
        migrations.DeleteModel(
            name="RecommendationTemplate",
        ),
    ]

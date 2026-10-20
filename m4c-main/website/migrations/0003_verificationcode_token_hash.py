from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("website", "0002_memberprofile_county_memberprofile_full_name_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="verificationcode",
            name="token_hash",
            field=models.CharField(blank=True, default="", max_length=128),
        ),
    ]

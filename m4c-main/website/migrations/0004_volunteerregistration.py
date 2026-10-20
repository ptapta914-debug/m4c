from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("website", "0003_verificationcode_token_hash")]

    operations = [
        migrations.CreateModel(
            name="VolunteerRegistration",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("full_name", models.CharField(max_length=150)),
                ("phone_number", models.CharField(max_length=32)),
                ("county", models.CharField(max_length=80)),
                ("interest", models.CharField(max_length=80)),
                ("email", models.EmailField(blank=True, default="", max_length=254)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ("-created_at",)},
        ),
    ]

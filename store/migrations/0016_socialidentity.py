from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('store', '0015_alter_register_pwd_alter_register_reenter_pwd')]

    operations = [
        migrations.CreateModel(
            name='SocialIdentity',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('provider', models.CharField(max_length=16, choices=[('google', 'Google'), ('github', 'GitHub'), ('x', 'X')])),
                ('subject', models.CharField(max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='social_identities', to='store.register')),
            ],
            options={'constraints': [models.UniqueConstraint(fields=['provider', 'subject'], name='store_social_provider_subject')]},
        ),
    ]

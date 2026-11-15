from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('shop', '0002_product_quantity')]
    operations = [
        migrations.AddField(model_name='orders', name='payment_state', field=models.CharField(default='unpaid', max_length=16)),
        migrations.AddField(model_name='orders', name='payment_mode', field=models.CharField(default='', max_length=12)),
        migrations.AddField(model_name='orders', name='paytm_order_id', field=models.CharField(blank=True, max_length=50, null=True, unique=True)),
        migrations.AddField(model_name='orders', name='paytm_transaction_id', field=models.CharField(blank=True, default='', max_length=100)),
    ]

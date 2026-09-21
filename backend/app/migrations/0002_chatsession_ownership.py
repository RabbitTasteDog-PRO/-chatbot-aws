# 새 대화에 사용자 소유권을 추가한다. 소유자를 알 수 없는 기존 메시지는 연결하지 않는다.
import uuid
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('app', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name='ChatSession',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at', '-pk']},
        ),
        migrations.AddField(
            model_name='chatmessage', name='conversation',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE,
                                    related_name='messages', to='app.chatsession'),
        ),
        migrations.AlterField(
            model_name='chatmessage', name='session_id',
            field=models.CharField(blank=True, db_index=True, default='', max_length=255),
        ),
        migrations.AlterModelOptions(name='chatmessage', options={'ordering': ['created_at', 'pk']}),
    ]

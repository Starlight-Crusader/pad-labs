# Generated by Django 5.1.1 on 2024-09-21 15:36

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('records', '0002_alter_gamerecord_player1_alter_gamerecord_player2'),
    ]

    operations = [
        migrations.RenameField(
            model_name='gamerecord',
            old_name='player1',
            new_name='black_player',
        ),
        migrations.RenameField(
            model_name='gamerecord',
            old_name='player2',
            new_name='white_player',
        ),
    ]

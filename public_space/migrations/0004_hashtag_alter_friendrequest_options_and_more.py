from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('public_space', '0003_share_mention'),
    ]

    operations = [

        # -----------------------------
        # POST CHANGES
        # -----------------------------

        migrations.RenameField(
            model_name='post',
            old_name='text',
            new_name='content',
        ),

        migrations.RenameField(
            model_name='post',
            old_name='views_count',
            new_name='view_count',
        ),

        migrations.RemoveField(
            model_name='post',
            name='likes_count',
        ),

        migrations.RemoveField(
            model_name='post',
            name='comments_count',
        ),

        migrations.RemoveField(
            model_name='post',
            name='shares_count',
        ),

        migrations.AddField(
            model_name='post',
            name='media_sha256',
            field=models.CharField(
                max_length=64,
                blank=True,
                null=True,
            ),
        ),

        migrations.AlterField(
            model_name='post',
            name='media',
            field=models.FileField(
                upload_to='public_space/',
                blank=True,
                null=True,
            ),
        ),

        migrations.AlterField(
            model_name='post',
            name='media_type',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('text', 'Text'),
                    ('image', 'Image'),
                    ('video', 'Video'),
                ],
                default='text',
            ),
        ),

        migrations.AlterField(
            model_name='post',
            name='privacy',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('public', 'Public'),
                    ('friends', 'Friends Only'),
                ],
                default='public',
            ),
        ),

        migrations.AlterField(
            model_name='post',
            name='user',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='public_space_posts',
                to=settings.AUTH_USER_MODEL,
            ),
        ),

        migrations.AlterModelOptions(
            name='post',
            options={
                'ordering': ['-created_at'],
            },
        ),

        # -----------------------------
        # COMMENT CHANGES
        # -----------------------------

        migrations.AddField(
            model_name='comment',
            name='updated_at',
            field=models.DateTimeField(
                auto_now=True,
            ),
        ),

        # -----------------------------
        # FRIEND REQUEST CHANGES
        # -----------------------------

        migrations.AddField(
            model_name='friendrequest',
            name='updated_at',
            field=models.DateTimeField(
                auto_now=True,
            ),
        ),

        migrations.AlterModelOptions(
            name='friendrequest',
            options={
                'ordering': ['-created_at'],
            },
        ),

        # -----------------------------
        # REPORT CHANGES
        # -----------------------------

        migrations.AddField(
            model_name='report',
            name='description',
            field=models.TextField(
                blank=True,
            ),
        ),

        migrations.AlterField(
            model_name='report',
            name='reason',
            field=models.CharField(
                max_length=30,
                choices=[
                    ('spam', 'Spam'),
                    ('inappropriate', 'Inappropriate Content'),
                    ('harassment', 'Harassment'),
                    ('other', 'Other'),
                ],
                default='other',
            ),
        ),

        # -----------------------------
        # SAVE POST
        # -----------------------------

        migrations.AlterField(
            model_name='savepost',
            name='post',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='saved_by',
                to='public_space.post',
            ),
        ),

        # -----------------------------
        # SHARE
        # -----------------------------

        migrations.AlterUniqueTogether(
            name='share',
            unique_together={
                ('post', 'user'),
            },
        ),

        # -----------------------------
        # HASHTAG
        # -----------------------------

        migrations.CreateModel(
            name='Hashtag',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                (
                    'name',
                    models.CharField(
                        max_length=100,
                        unique=True,
                    ),
                ),
                (
                    'created_at',
                    models.DateTimeField(
                        auto_now_add=True,
                    ),
                ),
            ],
        ),

        # -----------------------------
        # MENTION
        #
        # We intentionally keep the old
        # mention table fields untouched
        # here and add the new user field.
        # -----------------------------

        migrations.AddField(
            model_name='mention',
            name='user',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to=settings.AUTH_USER_MODEL,
            ),
        ),

        # -----------------------------
        # NOTIFICATION
        # -----------------------------

        migrations.CreateModel(
            name='Notification',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                (
                    'notification_type',
                    models.CharField(
                        max_length=30,
                        choices=[
                            ('like', 'Like'),
                            ('comment', 'Comment'),
                            ('share', 'Share'),
                            ('friend_request', 'Friend Request'),
                            ('friend_accept', 'Friend Accepted'),
                            ('mention', 'Mention'),
                            ('follow', 'Follow'),
                        ],
                    ),
                ),
                (
                    'message',
                    models.CharField(
                        max_length=255,
                    ),
                ),
                (
                    'is_read',
                    models.BooleanField(
                        default=False,
                    ),
                ),
                (
                    'created_at',
                    models.DateTimeField(
                        auto_now_add=True,
                    ),
                ),
                (
                    'post',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='notifications',
                        to='public_space.post',
                    ),
                ),
                (
                    'sender',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='public_space_sent_notifications',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    'user',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='public_space_notifications',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),

        # -----------------------------
        # POST CREATION LOG
        # -----------------------------

        migrations.CreateModel(
            name='PostCreationLog',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                (
                    'created_at',
                    models.DateTimeField(
                        auto_now_add=True,
                    ),
                ),
                (
                    'ip_address',
                    models.GenericIPAddressField(
                        blank=True,
                        null=True,
                    ),
                ),
                (
                    'success',
                    models.BooleanField(
                        default=True,
                    ),
                ),
                (
                    'reason',
                    models.CharField(
                        max_length=255,
                        blank=True,
                    ),
                ),
                (
                    'user',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='post_creation_logs',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]
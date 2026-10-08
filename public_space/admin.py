from django.contrib import admin
from .models import (
    Post,
    Hashtag,
    Like,
    Comment,
    SavePost,
    Report,
    FriendRequest,
    Follow,
    Share,
    Mention,
    Notification,
    PostCreationLog,
)


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'content_preview',
        'media_type',
        'privacy',
        'likes_count',
        'comments_count',
        'shares_count',
        'views_count',
        'created_at',
    )

    list_filter = (
        'media_type',
        'privacy',
        'created_at',
    )

    search_fields = (
        'user__username',
        'user__email',
        'content',
    )

    readonly_fields = (
        'created_at',
        'updated_at',
        'friend_count_at_post',
        'view_count',
        'media_sha256',
    )

    def content_preview(self, obj):
        if obj.content:
            return obj.content[:50]
        return '-'

    content_preview.short_description = 'Content'

    def likes_count(self, obj):
        return obj.likes.count()

    likes_count.short_description = 'Likes'

    def comments_count(self, obj):
        return obj.comments.count()

    comments_count.short_description = 'Comments'

    def shares_count(self, obj):
        return obj.shares.count()

    shares_count.short_description = 'Shares'

    def views_count(self, obj):
        return obj.view_count

    views_count.short_description = 'Views'


@admin.register(Hashtag)
class HashtagAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'name',
        'created_at',
    )

    search_fields = (
        'name',
    )


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'post',
        'user',
        'created_at',
    )

    search_fields = (
        'user__username',
        'post__content',
    )


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'post',
        'user',
        'short_text',
        'created_at',
    )

    search_fields = (
        'user__username',
        'text',
        'post__content',
    )

    def short_text(self, obj):
        return obj.text[:50]

    short_text.short_description = 'Comment'


@admin.register(SavePost)
class SavePostAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'post',
        'user',
        'created_at',
    )

    search_fields = (
        'user__username',
        'post__content',
    )


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'post',
        'user',
        'reason',
        'created_at',
    )

    list_filter = (
        'reason',
        'created_at',
    )

    search_fields = (
        'user__username',
        'post__content',
        'description',
    )


@admin.register(FriendRequest)
class FriendRequestAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'sender',
        'receiver',
        'accepted',
        'created_at',
    )

    list_filter = (
        'accepted',
        'created_at',
    )

    search_fields = (
        'sender__username',
        'receiver__username',
    )


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'follower',
        'following',
        'created_at',
    )

    search_fields = (
        'follower__username',
        'following__username',
    )


@admin.register(Share)
class ShareAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'post',
        'user',
        'created_at',
    )

    search_fields = (
        'user__username',
        'post__content',
    )


@admin.register(Mention)
class MentionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'post',
        'user',
        'created_at',
    )

    search_fields = (
        'user__username',
        'post__content',
    )


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'sender',
        'notification_type',
        'message',
        'is_read',
        'created_at',
    )

    list_filter = (
        'notification_type',
        'is_read',
        'created_at',
    )

    search_fields = (
        'user__username',
        'sender__username',
        'message',
    )


@admin.register(PostCreationLog)
class PostCreationLogAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'created_at',
        'ip_address',
        'success',
        'reason',
    )

    list_filter = (
        'success',
        'created_at',
    )

    search_fields = (
        'user__username',
        'ip_address',
        'reason',
    )
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import logout
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.db import IntegrityError
from django.http import HttpResponse

import hashlib
import re

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

from .forms import PostForm, CommentForm, ReportForm


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_friend_ids(user):
    accepted_requests = FriendRequest.objects.filter(
        Q(sender=user, accepted=True) |
        Q(receiver=user, accepted=True)
    )

    friend_ids = set()

    for request in accepted_requests:
        if request.sender_id == user.id:
            friend_ids.add(request.receiver_id)
        else:
            friend_ids.add(request.sender_id)

    return friend_ids


def get_friend_count(user):
    return len(get_friend_ids(user))


def get_daily_post_limit(friend_count):
    if friend_count == 0:
        return 0

    elif friend_count == 1:
        return 1

    elif 2 <= friend_count <= 5:
        return 2

    elif 6 <= friend_count <= 10:
        return 5

    else:
        return 999999


def get_client_ip(request):
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')

    if forwarded_for:
        return forwarded_for.split(',')[0]

    return request.META.get('REMOTE_ADDR')


def get_media_hash(uploaded_file):
    if not uploaded_file:
        return None

    sha256 = hashlib.sha256()

    for chunk in uploaded_file.chunks():
        sha256.update(chunk)

    uploaded_file.seek(0)

    return sha256.hexdigest()


def contains_inappropriate_content(text):
    if not text:
        return False

    blocked_words = getattr(
        settings,
        'PUBLIC_SPACE_BLOCKED_WORDS',
        []
    )

    text_lower = text.lower()

    for word in blocked_words:
        if word.lower() in text_lower:
            return True

    return False


def extract_hashtags(text):
    if not text:
        return []

    hashtags = re.findall(
        r'#([A-Za-z0-9_]+)',
        text
    )

    return list(dict.fromkeys(hashtags))


def extract_mentions(text):
    if not text:
        return []

    mentions = re.findall(
        r'@([A-Za-z0-9_.@+-]+)',
        text
    )

    return list(dict.fromkeys(mentions))


def create_notification(
    user,
    sender,
    notification_type,
    message,
    post=None
):
    if user == sender:
        return

    Notification.objects.create(
        user=user,
        sender=sender,
        notification_type=notification_type,
        message=message,
        post=post
    )


def process_post_hashtags(post):
    hashtags = extract_hashtags(post.content)

    max_hashtags = getattr(
        settings,
        'PUBLIC_SPACE_MAX_HASHTAGS',
        10
    )

    hashtags = hashtags[:max_hashtags]

    for hashtag_name in hashtags:

        hashtag_name = hashtag_name.lower()

        hashtag, created = Hashtag.objects.get_or_create(
            name=hashtag_name
        )


def process_post_mentions(post):
    mentions = extract_mentions(post.content)

    for username in mentions:

        user = User.objects.filter(
            username__iexact=username
        ).first()

        if not user:
            continue

        Mention.objects.get_or_create(
            post=post,
            user=user
        )

        create_notification(
            user=user,
            sender=post.user,
            notification_type='mention',
            message=f'{post.user.username} mentioned you in a post.',
            post=post
        )


def is_post_editable(post):
    limit_minutes = getattr(
        settings,
        'PUBLIC_SPACE_POST_EDIT_DELETE_LIMIT',
        30
    )

    elapsed = timezone.now() - post.created_at

    return elapsed.total_seconds() <= limit_minutes * 60


# ============================================================
# PUBLIC SPACE FEED
# ============================================================

@login_required
def public_space(request):

    user = request.user

    friend_ids = get_friend_ids(user)

    posts = Post.objects.filter(
        Q(privacy='public') |
        Q(user=user) |
        Q(user_id__in=friend_ids)
    ).select_related(
        'user'
    ).prefetch_related(
        'likes',
        'comments',
        'shares',
        'saved_by',
        'mentions'
    )

    trending_posts = Post.objects.filter(
        privacy='public'
    ).select_related(
        'user'
    ).order_by(
        '-view_count',
        '-created_at'
    )[:5]

    today = timezone.localdate()

    posts_today = Post.objects.filter(
        user=user,
        created_at__date=today
    ).count()

    friend_count = get_friend_count(user)

    daily_post_limit = get_daily_post_limit(
        friend_count
    )

    unread_notifications = Notification.objects.filter(
        user=user,
        is_read=False
    ).count()

    pending_friend_requests = FriendRequest.objects.filter(
        receiver=user,
        accepted=False
    ).count()

    context = {
        'posts': posts,
        'trending_posts': trending_posts,
        'comment_form': CommentForm(),
        'unread_notifications': unread_notifications,
        'pending_friend_requests': pending_friend_requests,
        'friend_count': friend_count,
        'posts_today': posts_today,
        'daily_post_limit': daily_post_limit,
        'today': today,
    }

    return render(
        request,
        'public_space/feed.html',
        context
    )


# ============================================================
# CREATE POST
# ============================================================

@login_required
def create_post(request):

    if request.method != 'POST':
        form = PostForm()

        return render(
            request,
            'public_space/create_post.html',
            {'form': form}
        )

    form = PostForm(request.POST, request.FILES)

    if not form.is_valid():
        return render(
            request,
            'public_space/create_post.html',
            {'form': form}
        )

    user = request.user

    friend_count = get_friend_count(user)

    daily_limit = get_daily_post_limit(
        friend_count
    )

    today = timezone.localdate()

    posts_today = Post.objects.filter(
        user=user,
        created_at__date=today
    ).count()

    if posts_today >= daily_limit:

        PostCreationLog.objects.create(
            user=user,
            ip_address=get_client_ip(request),
            success=False,
            reason='Daily post limit reached'
        )

        messages.error(
            request,
            'You have reached your daily post limit.'
        )

        return redirect('public_space')

    content = form.cleaned_data.get(
        'content',
        ''
    )

    if contains_inappropriate_content(content):

        PostCreationLog.objects.create(
            user=user,
            ip_address=get_client_ip(request),
            success=False,
            reason='Blocked content'
        )

        messages.error(
            request,
            'This content cannot be posted.'
        )

        return redirect('public_space')

    media = form.cleaned_data.get('media')

    media_hash = None

    if media:

        max_size = getattr(
            settings,
            'PUBLIC_SPACE_MAX_UPLOAD_SIZE',
            20 * 1024 * 1024
        )

        if media.size > max_size:

            messages.error(
                request,
                'Uploaded file is too large.'
            )

            return redirect('create_post')

        media_hash = get_media_hash(media)

        duplicate_media = Post.objects.filter(
            user=user,
            media_sha256=media_hash
        ).exists()

        if duplicate_media:

            messages.error(
                request,
                'You have already posted this media.'
            )

            return redirect('create_post')

    post = form.save(commit=False)

    post.user = user
    post.friend_count_at_post = friend_count
    post.media_sha256 = media_hash

    post.save()

    process_post_hashtags(post)
    process_post_mentions(post)

    PostCreationLog.objects.create(
        user=user,
        ip_address=get_client_ip(request),
        success=True,
        reason='Post created'
    )

    messages.success(
        request,
        'Post created successfully.'
    )

    return redirect('public_space')


# ============================================================
# EDIT POST
# ============================================================

@login_required
def edit_post(request, post_id):

    post = get_object_or_404(
        Post,
        id=post_id
    )

    if post.user != request.user:

        messages.error(
            request,
            'You can edit only your own posts.'
        )

        return redirect('public_space')

    if not is_post_editable(post):

        messages.error(
            request,
            'The editing time limit has expired.'
        )

        return redirect('public_space')

    if request.method == 'POST':

        form = PostForm(
            request.POST,
            request.FILES,
            instance=post
        )

        if form.is_valid():

            content = form.cleaned_data.get(
                'content',
                ''
            )

            if contains_inappropriate_content(content):

                messages.error(
                    request,
                    'This content cannot be posted.'
                )

                return redirect(
                    'edit_post',
                    post_id=post.id
                )

            form.save()

            process_post_hashtags(post)
            process_post_mentions(post)

            messages.success(
                request,
                'Post updated successfully.'
            )

            return redirect('public_space')

    else:

        form = PostForm(
            instance=post
        )

    return render(
        request,
        'public_space/edit_post.html',
        {
            'form': form,
            'post': post
        }
    )


# ============================================================
# DELETE POST
# ============================================================

@login_required
def delete_post(request, post_id):

    post = get_object_or_404(
        Post,
        id=post_id
    )

    if post.user != request.user:

        messages.error(
            request,
            'You can delete only your own posts.'
        )

        return redirect('public_space')

    if request.method != 'POST':

        return redirect('public_space')

    if not is_post_editable(post):

        messages.error(
            request,
            'The delete time limit has expired.'
        )

        return redirect('public_space')

    post.delete()

    messages.success(
        request,
        'Post deleted successfully.'
    )

    return redirect('public_space')


# ============================================================
# VIEW POST
# ============================================================

@login_required
def view_post(request, post_id):

    post = get_object_or_404(
        Post,
        id=post_id
    )

    # Owner can always view their own post
    if post.user == request.user:
        allowed = True

    # Public posts can be viewed by everyone
    elif post.privacy == 'public':
        allowed = True

    # Friends Only posts can be viewed only by accepted friends
    elif post.privacy == 'friends':
        allowed = post.user_id in get_friend_ids(request.user)

    # Any other privacy setting is denied
    else:
        allowed = False

    # Block unauthorized access
    if not allowed:

        messages.error(
            request,
            'You do not have permission to view this post.'
        )

        return redirect('public_space')

    # Increase view count only for authorized users
    post.view_count += 1

    post.save(
        update_fields=['view_count']
    )

    return render(
        request,
        'public_space/view_post.html',
        {
            'post': post,
            'comment_form': CommentForm()
        }
    )


# ============================================================
# LIKE
# ============================================================

@login_required
def like_post(request, post_id):

    if request.method != 'POST':
        return redirect('public_space')

    post = get_object_or_404(
        Post,
        id=post_id
    )

    like, created = Like.objects.get_or_create(
        post=post,
        user=request.user
    )

    if created:

        create_notification(
            user=post.user,
            sender=request.user,
            notification_type='like',
            message=f'{request.user.username} liked your post.',
            post=post
        )

    else:

        like.delete()

    return redirect('public_space')


# ============================================================
# COMMENT
# ============================================================

@login_required
def add_comment(request, post_id):

    post = get_object_or_404(
        Post,
        id=post_id
    )

    if request.method != 'POST':
        return redirect('public_space')

    form = CommentForm(request.POST)

    if form.is_valid():

        comment = form.save(commit=False)

        comment.post = post
        comment.user = request.user

        comment.save()

        create_notification(
            user=post.user,
            sender=request.user,
            notification_type='comment',
            message=f'{request.user.username} commented on your post.',
            post=post
        )

    return redirect('public_space')


# ============================================================
# SHARE
# ============================================================

@login_required
def share_post(request, post_id):

    if request.method != 'POST':
        return redirect('public_space')

    post = get_object_or_404(
        Post,
        id=post_id
    )

    share, created = Share.objects.get_or_create(
        post=post,
        user=request.user
    )

    if created:

        create_notification(
            user=post.user,
            sender=request.user,
            notification_type='share',
            message=f'{request.user.username} shared your post.',
            post=post
        )

    return redirect('public_space')


# ============================================================
# SAVE
# ============================================================

@login_required
def save_post(request, post_id):

    if request.method != 'POST':
        return redirect('public_space')

    post = get_object_or_404(
        Post,
        id=post_id
    )

    saved, created = SavePost.objects.get_or_create(
        post=post,
        user=request.user
    )

    if not created:
        saved.delete()

    return redirect('public_space')


# ============================================================
# REPORT
# ============================================================

@login_required
def report_post(request, post_id):

    post = get_object_or_404(
        Post,
        id=post_id
    )

    if request.method == 'POST':

        form = ReportForm(request.POST)

        if form.is_valid():

            report = form.save(commit=False)

            report.post = post
            report.user = request.user

            try:

                report.save()

                messages.success(
                    request,
                    'Post reported successfully.'
                )

            except IntegrityError:

                messages.warning(
                    request,
                    'You have already reported this post.'
                )

            return redirect('public_space')

    else:

        form = ReportForm()

    return render(
        request,
        'public_space/report_post.html',
        {
            'form': form,
            'post': post
        }
    )


# ============================================================
# FIND FRIENDS / USERS
# ============================================================

@login_required
def users_list(request):

    current_user = request.user

    users = User.objects.exclude(
        id=current_user.id
    ).order_by('username')

    user_data = []

    for user in users:

        followers_count = Follow.objects.filter(
            following=user
        ).count()

        following_count = Follow.objects.filter(
            follower=user
        ).count()

        is_friend = FriendRequest.objects.filter(
            accepted=True
        ).filter(
            Q(
                sender=current_user,
                receiver=user
            ) |
            Q(
                sender=user,
                receiver=current_user
            )
        ).exists()

        pending_request = FriendRequest.objects.filter(
            sender=current_user,
            receiver=user,
            accepted=False
        ).exists()

        already_following = Follow.objects.filter(
            follower=current_user,
            following=user
        ).exists()

        user_data.append({
            'user': user,
            'followers_count': followers_count,
            'following_count': following_count,
            'is_friend': is_friend,
            'pending_request': pending_request,
            'already_following': already_following,
        })

    return render(
        request,
        'public_space/users.html',
        {
            'user_data': user_data,
        }
    )


# ============================================================
# SEND FRIEND REQUEST
# ============================================================

@login_required
def send_friend_request(request, user_id):

    if request.method != 'POST':
        return redirect('users_list')

    receiver = get_object_or_404(
        User,
        id=user_id
    )

    if receiver == request.user:

        messages.error(
            request,
            'You cannot send a friend request to yourself.'
        )

        return redirect('users_list')

    existing = FriendRequest.objects.filter(
        sender=request.user,
        receiver=receiver
    ).first()

    if existing:

        if existing.accepted:

            messages.info(
                request,
                'You are already friends.'
            )

        else:

            messages.info(
                request,
                'Friend request already sent.'
            )

        return redirect('users_list')

    reverse_existing = FriendRequest.objects.filter(
        sender=receiver,
        receiver=request.user,
        accepted=False
    ).first()

    if reverse_existing:

        messages.info(
            request,
            'This user already sent you a friend request.'
        )

        return redirect('friend_requests')

    FriendRequest.objects.create(
        sender=request.user,
        receiver=receiver
    )

    create_notification(
        user=receiver,
        sender=request.user,
        notification_type='friend_request',
        message=f'{request.user.username} sent you a friend request.'
    )

    messages.success(
        request,
        'Friend request sent.'
    )

    return redirect('users_list')


# ============================================================
# FRIEND REQUESTS
# ============================================================

@login_required
def friend_requests(request):

    received_requests = FriendRequest.objects.filter(
        receiver=request.user,
        accepted=False
    ).select_related(
        'sender'
    )

    sent_requests = FriendRequest.objects.filter(
        sender=request.user,
        accepted=False
    ).select_related(
        'receiver'
    )

    return render(
        request,
        'public_space/friend_requests.html',
        {
            'received_requests': received_requests,
            'sent_requests': sent_requests,
        }
    )


# ============================================================
# ACCEPT FRIEND REQUEST
# ============================================================

@login_required
def accept_friend_request(request, request_id):

    if request.method != 'POST':
        return redirect('friend_requests')

    friend_request = get_object_or_404(
        FriendRequest,
        id=request_id,
        receiver=request.user,
        accepted=False
    )

    friend_request.accepted = True
    friend_request.save()

    create_notification(
        user=friend_request.sender,
        sender=request.user,
        notification_type='friend_accept',
        message=f'{request.user.username} accepted your friend request.'
    )

    messages.success(
        request,
        'Friend request accepted.'
    )

    return redirect('friend_requests')


# ============================================================
# FOLLOW / UNFOLLOW
# ============================================================

@login_required
def follow_user(request, user_id):

    if request.method != 'POST':
        return redirect('users_list')

    user_to_follow = get_object_or_404(
        User,
        id=user_id
    )

    if user_to_follow == request.user:

        messages.error(
            request,
            'You cannot follow yourself.'
        )

        return redirect('users_list')

    follow = Follow.objects.filter(
        follower=request.user,
        following=user_to_follow
    ).first()

    if follow:

        follow.delete()

        messages.success(
            request,
            f'Unfollowed {user_to_follow.username}.'
        )

    else:

        Follow.objects.create(
            follower=request.user,
            following=user_to_follow
        )

        create_notification(
            user=user_to_follow,
            sender=request.user,
            notification_type='follow',
            message=f'{request.user.username} started following you.'
        )

        messages.success(
            request,
            f'Now following {user_to_follow.username}.'
        )

    return redirect('users_list')


# ============================================================
# HASHTAG POSTS
# ============================================================

@login_required
def hashtag_posts(request, hashtag_name):

    hashtag_name = hashtag_name.lower()

    posts = Post.objects.filter(
        content__icontains=f'#{hashtag_name}',
        privacy='public'
    ).select_related(
        'user'
    ).order_by(
        '-created_at'
    )

    return render(
        request,
        'public_space/hashtag_posts.html',
        {
            'hashtag_name': hashtag_name,
            'posts': posts,
        }
    )


# ============================================================
# NOTIFICATIONS
# ============================================================

@login_required
def notifications(request):

    notification_list = Notification.objects.filter(
        user=request.user
    ).select_related(
        'sender',
        'post'
    )

    Notification.objects.filter(
        user=request.user,
        is_read=False
    ).update(
        is_read=True
    )

    return render(
        request,
        'public_space/notifications.html',
        {
            'notifications': notification_list
        }
    )


# ============================================================
# LOGOUT
# ============================================================

@login_required
def logout_user(request):

    if request.method != 'POST':
        return redirect('public_space')

    logout(request)

    return redirect('/')
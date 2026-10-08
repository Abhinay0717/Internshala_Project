from django.urls import path
from . import views


urlpatterns = [

    path(
        '',
        views.public_space,
        name='public_space'
    ),

    path(
        'create/',
        views.create_post,
        name='create_post'
    ),

    path(
        'edit/<int:post_id>/',
        views.edit_post,
        name='edit_post'
    ),

    path(
        'delete/<int:post_id>/',
        views.delete_post,
        name='delete_post'
    ),

    path(
        'view/<int:post_id>/',
        views.view_post,
        name='view_post'
    ),

    path(
        'like/<int:post_id>/',
        views.like_post,
        name='like_post'
    ),

    path(
        'comment/<int:post_id>/',
        views.add_comment,
        name='add_comment'
    ),

    path(
        'share/<int:post_id>/',
        views.share_post,
        name='share_post'
    ),

    path(
        'save/<int:post_id>/',
        views.save_post,
        name='save_post'
    ),

    path(
        'report/<int:post_id>/',
        views.report_post,
        name='report_post'
    ),

    path(
        'users/',
        views.users_list,
        name='users_list'
    ),

    path(
        'friend-request/<int:user_id>/',
        views.send_friend_request,
        name='send_friend_request'
    ),

    path(
        'follow/<int:user_id>/',
        views.follow_user,
        name='follow_user'
    ),

    path(
        'hashtag/<str:hashtag_name>/',
        views.hashtag_posts,
        name='hashtag_posts'
    ),

    path(
        'notifications/',
        views.notifications,
        name='notifications'
    ),

    path(
        'friend-requests/',
        views.friend_requests,
        name='friend_requests'
    ),

    path(
        'friend-request/accept/<int:request_id>/',
        views.accept_friend_request,
        name='accept_friend_request'
    ),

    path(
        'logout/',
        views.logout_user,
        name='logout_user'
    ),
]
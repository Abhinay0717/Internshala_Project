from django.contrib import admin
from django.urls import path, include

from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [

    path(
        'admin/',
        admin.site.urls
    ),

    path(
        '',
        include('core.urls')
    ),

    path(
        'resume/',
        include('resume.urls')
    ),

    path(
        'public-space/',
        include('public_space.urls')
    ),

    path(
        'subscriptions/',
        include('subscriptions.urls')
    ),
]


urlpatterns += static(
    settings.MEDIA_URL,
    document_root=settings.MEDIA_ROOT
)
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from letters import views

urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('', include('letters.urls')),
    path('attachment/<int:pk>/<str:field_name>/', views.serve_attachment, name='serve_attachment'),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

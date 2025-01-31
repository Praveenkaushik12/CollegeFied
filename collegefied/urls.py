from django.contrib import admin
from django.urls import path,include


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/user/', include('api.urls')),  # Import API URLs from api app
    path("chat/", include("chat.urls")),
]

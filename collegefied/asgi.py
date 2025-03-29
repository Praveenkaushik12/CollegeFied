import os
from django.core.asgi import get_asgi_application

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'collegefied.settings')

# Initialize Django application
django_application = get_asgi_application()

# Import middleware and routing AFTER Django is initialized
from channels.routing import ProtocolTypeRouter, URLRouter
from chats.routing import websocket_urlpatterns
from chats.middleware import JWTAuthMiddlewareStack

application = ProtocolTypeRouter({
    'http': django_application,
    'websocket': JWTAuthMiddlewareStack(
        URLRouter(
            websocket_urlpatterns
        )
    ),
})
from django.db.models.signals import post_save,pre_save,post_delete
from django.dispatch import receiver
from django.apps import apps
from django.contrib.auth import get_user_model
from api.models import UserProfile,ProductRequest,Product
from chats.utils import create_chat_room, delete_chat_room
User = get_user_model()

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance,name=instance.username)
          
@receiver(post_save, sender=ProductRequest)
def update_product_status(sender, instance, created, **kwargs):
    """
    Update the product status based on the request status.
    """
    if instance.product:
        product = instance.product
        # If the request is accepted, move the product to 'reserved'
        if instance.status == 'accepted':
            if product.status == 'available':
                product.status = 'reserved'
        # If the request is rejected, move the product back to 'available'
        elif instance.status == 'rejected':
            if product.status == 'reserved' or product.status == 'unavailable':
                product.status = 'available'
        # If the request is approved, move the product to 'unavailable'
        elif instance.status == 'approved':
            if product.status == 'reserved':
                product.status = 'unavailable'

        # Save the product status change
        product.save()

# Signal to handle product status changes when a request is deleted
@receiver(post_delete, sender=ProductRequest)
def handle_request_deletion(sender, instance, **kwargs):
    """
    Revert the product status when a request is deleted or canceled.
    """
    if instance.product:
        product = instance.product
        if instance.status == 'approved' and product.status == 'unavailable':
            product.status = 'available'
        elif instance.status == 'rejected' and product.status == 'reserved':
            product.status = 'available'
        # In case of deletion, set the product to 'available' if no requests are pending
        elif product.requests.filter(status='approved').exists():
            product.status = 'unavailable'
        else:
            product.status = 'available'

        product.save()
    

@receiver(post_save, sender=ProductRequest)
def handle_product_request_status_change(sender, instance, **kwargs):
    """
    Signal handler to create or delete chat rooms based on product request status changes.
    """
    if instance.status == 'accepted':
        # Create a chat room when the request is accepted
        create_chat_room(
            product=instance.product,
            buyer=instance.buyer,
            seller=instance.product.seller,
        )
    elif instance.status == 'rejected':
        # Delete the chat room when the request is rejected
        delete_chat_room(
            product=instance.product,
            buyer=instance.buyer,
            seller=instance.product.seller,
        )


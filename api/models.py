from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models
from django.core.exceptions import ValidationError
from django.apps import apps
from django.conf import settings
from django.utils.timezone import now


def validate_kiet_email(email):
    domain = "kiet.edu"
    if not email.endswith(f"@{domain}"):
        raise ValidationError(f"Email must belong to the '{domain}' domain.")

    username = email.split('@')[0]
    if not username:
        raise ValidationError("The username part of the email cannot be empty.")

class UserManager(BaseUserManager):
    def create_user(self, email, username, password,**extra_fields):
        if not email:
            raise ValueError("The Email field must be set.")
        if not username:
            raise ValueError("The Name field must be set.")
        if not password:
            raise ValueError("The Password field must be set.")
        
        email = self.normalize_email(email)
        #validate_kiet_email(email)  # Validate email format and domain

        if User.objects.filter(email=email).exists():  # Check for duplicate email
            raise ValidationError("This email is already registered.")
        
       
        user = self.model(email=email, username=username,**extra_fields)
        user.set_password(password)  # Hash and store the password
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None,**extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_admin', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_email_verified', True)  # Automatically verify superuser emails

        return self.create_user(email=email, username=username, password=password, **extra_fields)

    
class User(AbstractBaseUser):
    username=models.CharField(max_length=255,unique=True)
    email = models.EmailField(unique=True) #validators=[validate_kiet_email])
    is_email_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_superuser=models.BooleanField(default=False)
    
    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email

    def has_perm(self, perm, obj=None):
        return self.is_admin

    def has_module_perms(self, app_label):
        return self.is_admin

class OTP(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        return (now() - self.created_at).seconds < 300  # 5-minute validity

class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name= models.CharField(max_length=255)
    address=models.TextField(blank=True, null=True)
    course=models.CharField(max_length=100,null=True)
    college_year=models.IntegerField(default=1)
    gender=models.CharField(max_length=20,choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')])
    image=models.ImageField(upload_to='profile_images/',blank=True,null=True)
    
    @property
    def average_rating(self):
        ratings = self.user.received_ratings.all()
        return ratings.aggregate(models.Avg('rating'))['rating__avg'] or 0

    
    def clean(self):
        if not (1 <= self.college_year <= 4):
            raise ValidationError("College year must be between 1 and 4.")
    
    def __str__(self):
        return f"{self.user.username}'s Profile"
 

class Product(models.Model):
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('sold', 'Sold'),
        ('reserved', 'Reserved'), #reserved use?
        ('unavailable', 'Unavailable'),
    ]
    
    CATEGORY_CHOICES = [
        ('books', 'Books & Study Material'),
        ('electronics', 'Electronics & Accessories'),
        ('hostel', 'Hostel Essentials'),
        ('stationery', 'Stationery & Art Supplies'),
        ('sports', 'Sports & Fitness'),
        ('clothing', 'Clothing & Accessories'),
        ('music', 'Musical Instruments'),
        ('vehicles', 'Bicycles & Vehicles'),
        ('misc', 'Miscellaneous'),
    ]

    title = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='products', on_delete=models.CASCADE)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='misc')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available') 
    upload_date = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True) 
      
     
    def __str__(self):
        return self.title
    
     
class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='product_images/')

    def __str__(self):
        return f"Image for {self.product.title}"
    
    
class ProductRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'), 
        ('approved', 'Approved'),
    ]

    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='sent_requests', on_delete=models.CASCADE)
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='received_requests', on_delete=models.CASCADE)
    product = models.ForeignKey('Product', related_name='requests', on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True) 

    def save(self, *args, **kwargs):
        # Automatically set the seller to the product's seller if not set
        if not self.seller:
            self.seller = self.product.seller

        # Check if status is being updated and validate the transition
        if self.pk:  # Check if the object already exists in the database
            old_status = ProductRequest.objects.get(pk=self.pk).status
            allowed_transitions = {
                'pending': ['accepted','rejected'],
                'accepted': ['approved', 'rejected'],
                'approved': ['rejected'],
                'rejected': [],
            }
            if self.status not in allowed_transitions.get(old_status, []):
                raise ValidationError(f"Invalid status transition from {old_status} to {self.status}.")
        
        super().save(*args, **kwargs)
        
        # Create chat when request is accepted
        if self.status == "accepted":
            Chat=apps.get_model('chat','Chat')
            Chat.objects.get_or_create(product_request=self)
           
        # Close chat when request is rejected 
        if self.status == "rejected":
            Chat=apps.get_model('chat','Chat')
            chat = Chat.objects.filter(product_request=self).first()
            if chat:
                chat.is_active = False
                chat.save()
              
        

    def __str__(self):
        return f"Request from {self.buyer.username} for {self.product.title}"
    
    
class Rating(models.Model):
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="given_ratings", on_delete=models.CASCADE)
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="received_ratings", on_delete=models.CASCADE)
    product = models.ForeignKey('Product', related_name="ratings", on_delete=models.CASCADE)
    rating = models.DecimalField(max_digits=3, decimal_places=1) 
    review = models.TextField(blank=True, null=True)  # Optional review
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('buyer', 'product')  # Prevent duplicate ratings for the same product

    def __str__(self):
        return f"{self.buyer.username} rated {self.seller.username} for {self.product.title} ({self.rating}/5)"
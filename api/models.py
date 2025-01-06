from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings

def validate_kiet_email(email):
    domain = "kiet.edu"
    if not email.endswith(f"@{domain}"):
        raise ValidationError(f"Email must belong to the '{domain}' domain.")

    username = email.split('@')[0]
    if not username:
        raise ValidationError("The username part of the email cannot be empty.")

class UserManager(BaseUserManager):
    def create_user(self, email, username, password):
        if not email:
            raise ValueError("The Email field must be set.")
        if not username:
            raise ValueError("The Name field must be set.")
        if not password:
            raise ValueError("The Password field must be set.")
        
        email = self.normalize_email(email)
        validate_kiet_email(email)  # Validate email format and domain

        if User.objects.filter(email=email).exists():  # Check for duplicate email
            raise ValidationError("This email is already registered.")
        
       
        user = self.model(email=email, username=username)
        user.set_password(password)  # Hash and store the password
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password):
        return self.create_user(email=email, username=username, password=password)
          
class User(AbstractBaseUser):
    # username=models.CharField(max_length=255,unique=True)
    username=models.CharField(max_length=255,unique=True)
    email = models.EmailField(unique=True, validators=[validate_kiet_email])
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    
    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email

    def has_perm(self, perm, obj=None):
        return self.is_admin

    def has_module_perms(self, app_label):
        return self.is_admin

class UserProfile(models.Model):
    user = models.OneToOneField('User', on_delete=models.CASCADE)
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

    title = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='products', on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')  # Changed from is_available to status
    upload_date = models.DateTimeField(auto_now_add=True)
    resourceImg = models.ImageField(upload_to='resource_images/',null=True,blank=True)
    
    # def save(self, *args, **kwargs):
    #     # Track the current and new status
    #     if self.pk:
    #         current_status = Product.objects.get(pk=self.pk).status
    #     else:
    #         current_status = None

    #     # Prevent reverting to 'available' if there are active approved requests
    #     # if self.status in ['available', 'reserved'] and current_status == 'unavailable':
    #     #     active_approved_requests = self.requests.filter(status='approved')
    #     #     if active_approved_requests.exists():
    #     #         raise ValidationError("Cannot change product status,while there is an approved request.")

    #     # Handle status change to 'sold'
    #     if self.status == 'sold' and current_status != 'sold':
    #         # Cancel all accepted or approved requests
    #         self.requests.filter(status__in=['accepted', 'approved']).update(status='cancelled')
    #         # Reject all pending requests
    #         self.requests.filter(status='pending').update(status='rejected')

    #     super().save(*args, **kwargs)
    
    def __str__(self):
        return self.title
    
    
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
                'accepted': ['accepted','approved', 'rejected'],
                'approved': ['rejected'],
                'rejected': [],
            }
            if self.status not in allowed_transitions.get(old_status, []):
                raise ValidationError(f"Invalid status transition from {old_status} to {self.status}.")
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Request from {self.buyer.username} for {self.product.title}"
    
    
class Rating(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="ratings")
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="received_ratings")
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="given_ratings")
    rating = models.PositiveIntegerField()  # Ratings between 1-5
    feedback = models.TextField(blank=True, null=True)  # Optional feedback
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Rating {self.rating} by {self.buyer} for {self.seller} on {self.product}"
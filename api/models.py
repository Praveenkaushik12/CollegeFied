from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone


def validate_kiet_email(email):
    domain = "kiet.edu"
    if not email.endswith(f"@{domain}"):
        raise ValidationError(f"Email must belong to the '{domain}' domain.")

    username = email.split('@')[0]
    if not username:
        raise ValidationError("The username part of the email cannot be empty.")

class UserManager(BaseUserManager):
    def create_user(self, email, name, password):
        if not email:
            raise ValueError("The Email field must be set.")
        if not name:
            raise ValueError("The Name field must be set.")
        if not password:
            raise ValueError("The Password field must be set.")
        
        email = self.normalize_email(email)
        validate_kiet_email(email)  # Validate email format and domain

        if User.objects.filter(email=email).exists():  # Check for duplicate email
            raise ValidationError("This email is already registered.")
        
       
        user = self.model(email=email, name=name)
        user.set_password(password)  # Hash and store the password
        user.save(using=self._db)
        return user

    def create_superuser(self, email, name, password):
        return self.create_user(email=email, name=name, password=password)
          
class User(AbstractBaseUser):
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True, validators=[validate_kiet_email])
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    
    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

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
    
    def __str__(self):
        return f"{self.user.name}'s Profile"

class Product(models.Model):
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('sold', 'Sold'),
        ('reserved', 'Reserved'),
        ('unavailable', 'Unavailable'),
    ]

    title = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    seller = models.ForeignKey('User', related_name='products', on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')  # Changed from is_available to status
    upload_date = models.DateTimeField(auto_now_add=True)
    resourceImg = models.ImageField(upload_to='resource_images/')

    def __str__(self):
        return self.title
    


class SaleHistory(models.Model):
    seller = models.ForeignKey('User', related_name='sales', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name='sales_history', on_delete=models.CASCADE)
    buyer = models.ForeignKey('User', related_name='purchases', on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    sale_date = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"{self.seller.name} sold {self.product.title} to {self.buyer.name} for {self.price}"
    

class PurchaseHistory(models.Model):
    buyer = models.ForeignKey('User', related_name='purchase_history', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name='purchase_history', on_delete=models.CASCADE)
    seller = models.ForeignKey('User', related_name='sales_history', on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    purchase_date = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"{self.buyer.name} bought {self.product.title} from {self.seller.name} for {self.price}"
    
    

class Reviews(models.Model):
    reviewer=models.ForeignKey(User,on_delete=models.SET_NULL,null=True)
    rating = models.IntegerField(choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')])
    review_text = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Review for seller {self.seller.name} by {self.buyer.name}"
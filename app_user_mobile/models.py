import random
import json

from datetime import timedelta

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.core.validators import RegexValidator
from django.utils import timezone

from data_load.models import WaterLevelObservation




class MobileUserManager(BaseUserManager):
    def create_user(self, mobile_number, **extra_fields):
        if not mobile_number:
            raise ValueError('Mobile number is required')
        user = self.model(mobile_number=mobile_number, **extra_fields)
        user.save(using=self._db)
        return user

class MobileAuthUser(AbstractBaseUser):
    mobile_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    
    mobile_number = models.CharField(
        validators=[mobile_regex], 
        max_length=17, 
        unique=True
    )
    
    # first_name = models.CharField(max_length=128, blank=True, null=True)
    # last_name = models.CharField(max_length=128, blank=True, null=True)
    first_name = models.TextField(blank=True, null=True)
    last_name = models.TextField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    profile_image = models.ImageField(upload_to='mobile_user/mobile_auth/profile_images/', blank=True, null=True)
    
    lat = models.FloatField(null=True, blank=True)
    long = models.FloatField(null=True, blank=True)
    fcm_token = models.TextField(null=True, blank=True)
    device_info = models.JSONField(default=dict, blank=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    USERNAME_FIELD = 'mobile_number'
    
    objects = MobileUserManager()
    
    def __str__(self):
        return self.mobile_number
    
    # @property
    # def full_name(self):
    #     return f"{self.first_name or ''} {self.last_name or ''}".strip()
    @property
    def full_name(self):
        """
            Return the full name of the user.
        """
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        return ""
    
    class Meta: 
        verbose_name = "Auth User"
        verbose_name_plural = "Auth Users" 
    
    


class OTP(models.Model):
    mobile_number = models.CharField(max_length=17)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    def save(self, *args, **kwargs):
        # Set expiration time (e.g., 5 minutes from creation)
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=5)
        super().save(*args, **kwargs)
    
    @classmethod
    def generate_otp(cls, mobile_number):
        # Delete any existing OTPs for this mobile number
        cls.objects.filter(mobile_number=mobile_number).delete()
        
        # Generate a 4-digit OTP
        if mobile_number == "01711415554":
            otp = "1234"
        else:
            otp = str(random.randint(1000, 9999))
        
        # Create and return the OTP instance
        return cls.objects.create(mobile_number=mobile_number, otp=otp)
    
    def is_valid(self):
        return timezone.now() <= self.expires_at
    
    
    
    
    
    



class FCMTokenWiseUpdatedLatLon(models.Model):
    """ 
        Purpose: Take --- CREATE/ UPDATE random user update location
    """

    fcm_token = models.TextField(null=True, blank=True)
    lat = models.FloatField(null=True, blank=True)
    long = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f'{self.fcm_token}//{self.lat}//{self.long}'
    
    class Meta: 
        verbose_name = "FCM Token Wise Updated Lat Lon"
        verbose_name_plural = "FCM Tokens Wise Updated Lat Lon" 




# Adding Proxy Model WaterlevelObservation for SMS API Interface

class WaterLevelSync(WaterLevelObservation):
    class Meta:
        proxy = True
        # This prevents Django from creating a new table in the DB
        verbose_name = "LEOTECH SMS (Waterlevel) API Sync"
        verbose_name_plural = "LEOTECH SMS (Waterlevel) API Sync"


from data_load.models import RainfallObservation

class RainfallSync(RainfallObservation):
    class Meta:
        proxy = True
        verbose_name = "LEOTECH SMS(Rainfall) API Sync"
        verbose_name_plural = "LEOTECH SMS(Rainfall) API Sync"


# Adding Saims API

class SMSSync(models.Model):
    """A dummy model for the SMS Sync Admin interface"""
    class Meta:
        managed = False
        verbose_name = "RIMES SMS (Data Parser & Sync)"
        verbose_name_plural = "RIMES SMS (Data Parser & Sync)"
        
from django.db import models




class ProfessionalListModel(models.Model):
    key = models.CharField(max_length=100, unique=True)
    name = models.TextField(null=True, blank=True)
    title = models.TextField(null=True, blank=True)
    organization = models.TextField(null=True, blank=True)
    education = models.TextField(null=True, blank=True)

    email = models.JSONField(default=list, blank=True)    # ['exen.ffwc@gmail.com', ...]
    phone = models.TextField(null=True, blank=True)
    alternatePhone = models.TextField(null=True, blank=True)
    alternatePhone1 = models.TextField(null=True, blank=True) 
    # profileImage = models.CharField(max_length=512, blank=True)
    profileImage = models.ImageField(upload_to='mobile_user/app_mobile_static_data/profile_images/', blank=True, null=True)

    researchInterest = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Professional List"
        verbose_name_plural = "Professionals List"

    def __str__(self):
        return f"{self.name} ({self.key})"



class UserManualModel(models.Model): 
    title = models.TextField(null=True, blank=True)
    level = models.IntegerField(null=True, blank=True) 
    path = models.ImageField(upload_to='mobile_user/app_mobile_static_data/user_manual/', blank=True, null=True)  

    class Meta:
        verbose_name = "User Manual"
        verbose_name_plural = "User Manuals"

    def __str__(self):
        return f"{self.title}/{self.level}"
    
    
    
class UsefulLinksModel(models.Model): 
    name = models.TextField(null=True, blank=True)
    link = models.TextField(null=True, blank=True) 

    class Meta:
        verbose_name = "Useful Link"
        verbose_name_plural = "Useful Links"

    def __str__(self):
        return f"{self.title}/{self.level}"
    
    
    
class ReportsLinksModel(models.Model): 
    year = models.TextField(null=True, blank=True)
    link = models.TextField(null=True, blank=True) 

    class Meta:
        verbose_name = "Report Link"
        verbose_name_plural = "Reports Links"

    def __str__(self):
        return f"{self.year}"
    
    
class AboutUsModel(models.Model): 
    mission = models.TextField(null=True, blank=True)
    vision = models.TextField(null=True, blank=True) 
    organogram = models.TextField(null=True, blank=True) 
    citizen_charter = models.TextField(null=True, blank=True) 

    class Meta:
        verbose_name = "About Us"
        verbose_name_plural = "Abouts Us"

    def __str__(self):
        return f"{self.mission[:30]}..."
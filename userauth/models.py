from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from data_load.models import Station
from indian_stations.models import IndianStations


class Profile(models.Model):  
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    userProfileStations = models.ManyToManyField(Station, db_constraint=False)
    userProfileIndianStations = models.ManyToManyField(IndianStations, db_constraint=False)

    @receiver(post_save, sender=User)
    def create_user_profile(sender, instance, created, **kwargs):
        if created:
            Profile.objects.create(user=instance)
    
    @receiver(post_save, sender=User)
    def save_user_profile(sender, instance, **kwargs):
        instance.profile.save()

class UserAuthProfile(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.DO_NOTHING)

    class Meta:
        managed = True
        db_table = 'userauth_userprofile'

class UserAuthProfileStations(models.Model):
    id = models.BigAutoField(primary_key=True)
    profile_id = models.BigIntegerField()
    station_id = models.BigIntegerField()

    class Meta:
        managed = True
        db_table = 'userauth_userprofile_stations'
        unique_together = (('profile_id', 'station_id'),)

class UserAuthProfileIndianStations(models.Model):
    id = models.BigAutoField(primary_key=True)
    profile_id = models.BigIntegerField()
    indianstations_id = models.BigIntegerField()

    class Meta:
        managed = True
        db_table = 'userauth_userprofile_indianstations'
        unique_together = (('profile_id', 'indianstations_id'),)
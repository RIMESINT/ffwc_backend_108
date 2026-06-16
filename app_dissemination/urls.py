from django.urls import path

################################################################
################################################################
### Working Part
################################################################
from app_dissemination.email_dissemination.views import (
    AMBulletinToQueueView,
    AMBulletinToQueueDetailsView, 
    AddAMBulletinToQueueView,
    
    ### for testing
    AMBulletinToQueueDetailsTestingView,
) 


urlpatterns = [
    ################################################################
    ################################################################
    ### Working Part
    ################################################################
    ################################################################
    ################################################################
    ### Email dissimination part
    ################################################################
    path(
        'v1/email_dissemination/am_bulletin_list/',
        AMBulletinToQueueView.as_view(),
        name='am_bulletin_list'
    ),
    path(
        'v1/email_dissemination/add_am_bulletin/',
        AddAMBulletinToQueueView.as_view(),
        name='add_am_bulletin'
    ),    
    path(
        'v1/email_dissemination/am_bulletin/<int:id>/',
        AMBulletinToQueueDetailsView.as_view(),
        name='am_bulletin'
    ),
    
    
    ####################################################
    ### Email dissimination testing
    ####################################################
    path(
        'v1/email_dissemination/am_bulletin_testing/<int:id>/',
        AMBulletinToQueueDetailsTestingView.as_view(),
        name='am_bulletin'
    ),
]
    
    
    
    


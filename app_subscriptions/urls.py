from django.urls import path

from app_subscriptions.email_subscriptions.views import (
    ListEmailSubscription, EmailSubscriptionDetailsView,
    AddEmailSubscription,
)









urlpatterns = [
    
    #####################################################################################
    ### Email Subscriptions
    #####################################################################################
    path(
        'v1/email_subscriptions/subscription_email_list/', 
        ListEmailSubscription.as_view(), 
        name='subscription_email_list'
    ),
    path(
        'v1/email_subscriptions/subscription_email_details/<int:id>/', 
        EmailSubscriptionDetailsView.as_view(), 
        name='subscription_email_details'
    ),
    path(
        'v1/email_subscriptions/add_subscription_email/', 
        AddEmailSubscription.as_view(), 
        name='add_subscription_email'
    ),
    
]


from django.contrib import admin
from app_user_mobile.models import MobileAuthUser




@admin.register(MobileAuthUser)
class MobileAuthUserAdmin(admin.ModelAdmin):
    # Fields to display in the list view
    list_display = [
        'mobile_number', 
        'full_name', 
        'is_verified', 
        'created_at'
    ]
    
    # Fields that can be clicked to edit
    list_display_links = ['mobile_number', 'full_name']
    
    # Fields to filter by (right sidebar)
    list_filter = ['is_verified', 'created_at']
    
    # Fields to search in
    search_fields = ['mobile_number', 'first_name', 'last_name']
    
    # Fields to make editable directly from list view
    list_editable = ['is_verified']
    
    # Pagination (show 20 records per page)
    list_per_page = 20
    
    # Order records by most recent first
    ordering = ['-created_at']
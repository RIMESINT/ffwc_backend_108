from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from app_user_mobile.models import MobileAuthUser
from app_water_watch_mobile.dropdown_api_mobile_user.serializers import MobileAuthUserSerializer







class MobileAuthUserListView(APIView):
    """
        API view to list all MobileAuthUser records without pagination
    """
    
    def get(self, request):
        try:
            users = MobileAuthUser.objects.all()
            
            serializer = MobileAuthUserSerializer(users, many=True)
            
            return Response({
                'success': True,
                'message': 'Users retrieved successfully',
                'data': serializer.data,
                'count': users.count()
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Error retrieving users: {str(e)}',
                'data': []
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)







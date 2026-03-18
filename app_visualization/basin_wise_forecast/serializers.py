from rest_framework import serializers

class ForcastStateDDReqSerializer(serializers.Serializer): 
    # Use CharField for these to allow the View to parse them manually 
    # since GET requests pass lists as multiple identical keys
    parameter = serializers.CharField(required=False)  
    source = serializers.IntegerField(required=True)  
    forecast_date = serializers.CharField(required=True)  
    
    # Keeping this flexible as you are passing it as a string "[]" in the URL
    basin_details = serializers.CharField(required=False, allow_blank=True)

    def validate_parameter(self, value):
        # This is a helper to ensure we handle single or multiple parameters
        return value
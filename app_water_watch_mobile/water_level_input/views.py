from datetime import timedelta

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework import generics, permissions 
from rest_framework import viewsets

from django.db import transaction
from django.utils.timezone import now
from django.utils import timezone
from django.shortcuts import get_object_or_404

from app_water_watch_mobile.water_level_input.serializers import (
    WaterWatchWaterLevelStationForMobileUserSerializer,
    SingleWaterLevelInputSerializer,
    WaterLevelInputForMobileUserSerializer,
    WaterLevelUpdateSerializer,
)

from app_water_watch_mobile.models import (
    WaterLevelInputForMobileUser,
    WaterWatchWaterLevelStationForMobileUser,
)

from app_user_mobile.authentication import (
    MobileJWTAuthentication
)







# class WaterLevelStationForMobileUserViewSet(generics.ListAPIView):
#     """
#         Read-only endpoint that returns the WaterWatchWaterLevelStationForMobileUser
#         records for the authenticated mobile user, with nested station + user details.
#     """
#     serializer_class = WaterWatchWaterLevelStationForMobileUserSerializer
#     authentication_classes = [MobileJWTAuthentication]
#     permission_classes = [permissions.IsAuthenticated]
#     lookup_field = "id"  

#     def get_queryset(self):
#         user = self.request.user 
#         return (
#             WaterWatchWaterLevelStationForMobileUser.objects
#             .filter(mobile_user=user, is_active=True)
#             .select_related("water_level_station", "mobile_user")
#             .order_by("-created_at")
#         )

class WaterLevelStationForMobileUserViewSet(generics.ListAPIView):
    """
        GET /api/my-stations/  -> list of WaterWatchWaterLevelStationForMobileUser
        Returns records for the authenticated mobile user (only active ones).
    """
    serializer_class = WaterWatchWaterLevelStationForMobileUserSerializer
    authentication_classes = [MobileJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated] 

    # safe default to avoid accidental large query before auth
    queryset = WaterWatchWaterLevelStationForMobileUser.objects.none()

    def get_queryset(self):
        """
            Return records for the authenticated mobile user only.
            If your authentication makes request.user a Django User (not MobileAuthUser),
            map it to MobileAuthUser here (example in the comment below).
        """
        user = self.request.user

        qs = WaterWatchWaterLevelStationForMobileUser.objects.filter(
            mobile_user=user,
            is_active=True
        )

        return qs.select_related("water_level_station", "mobile_user").order_by("-created_at")



class BulkWaterLevelCreateAPIView(APIView):
    """
        POST a list of water level inputs.
        Request body (example):
        [
            {"station_id": 101, "observation_date": "2025-09-15T14:30:00Z", "water_level": "2.34"},
            {"station_id": 102, "observation_date": "2025-09-15T14:35:00Z", "water_level": "3.21"}
        ]
    """
    authentication_classes = [MobileJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        payload = request.data

        # Basic payload check
        if not isinstance(payload, list) or len(payload) == 0:
            return Response(
                {"detail": "Expected a non-empty list of records."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer_context = {'request': request}
        responses = []   # collect per-item result/errors
        valid_objs = []
        seen = set()  # to detect duplicates inside payload: (station_id, obs_iso, water_level_str)

        for idx, item in enumerate(payload):
            item_ctx = {'request': request}
            s = SingleWaterLevelInputSerializer(data=item, context=item_ctx)
            if not s.is_valid():
                responses.append({
                    "index": idx,
                    "input": item,
                    "errors": s.errors
                })
                continue

            validated = s.validated_data
            station_id = validated['station_id']
            obs_dt = validated['observation_date']
            wl = validated['water_level']

            key = (int(station_id), obs_dt.isoformat(), str(wl))
            if key in seen:
                responses.append({
                    "index": idx,
                    "input": item,
                    "errors": {"non_field_errors": ["Duplicate entry in request payload."]}
                })
                continue
            seen.add(key)

            # Build model instance but don't save yet
            obj = WaterLevelInputForMobileUser(
                station=validated['station_obj'],
                observation_date=obs_dt,
                water_level=wl,
                created_by=request.user,
                updated_by=request.user,
            )
            valid_objs.append((idx, item, obj))

        # Bulk create valid objects in a transaction; capture created IDs
        created = []
        if valid_objs:
            with transaction.atomic():
                instances = [t[2] for t in valid_objs]
                created_instances = WaterLevelInputForMobileUser.objects.bulk_create(instances)
                # Compose created info
                for (idx, item, _), inst in zip(valid_objs, created_instances):
                    created.append({
                        "index": idx,
                        "input": item,
                        "id": inst.pk
                    })

        result = {
            "created_count": len(created),
            "created": created,
            "errors": responses
        }

        # HTTP 201 if at least one created, otherwise 400
        status_code = status.HTTP_201_CREATED if created else status.HTTP_400_BAD_REQUEST
        return Response(result, status=status_code)
    


class Last7DaysWaterLevelAPIView(generics.ListAPIView):
    """
        Returns all water level inputs for the authenticated mobile user
        from the last 7 days, ordered by observation_date DESC.
    """
    serializer_class = WaterLevelInputForMobileUserSerializer
    authentication_classes = [MobileJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]  

    def get_queryset(self):
        user = self.request.user
        seven_days_ago = now() - timedelta(days=13)
        return (
            WaterLevelInputForMobileUser.objects.filter(
                created_by=user,
                observation_date__gte=seven_days_ago
            )
            .order_by('-observation_date')
        )





class WaterLevelUpdateAPIView(generics.UpdateAPIView):
    """
        PUT endpoint to update a WaterLevelInputForMobileUser by id using QuerySet.update()
    """
    serializer_class = WaterLevelUpdateSerializer
    authentication_classes = [MobileJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated,]

    def get_object(self):
        pk = self.kwargs.get('pk')
        try:
            obj = WaterLevelInputForMobileUser.objects.select_related('created_by', 'station').get(pk=pk)
        except WaterLevelInputForMobileUser.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound("Record not found.")

        user = self.request.user

        # Must be the creator
        if obj.created_by_id != getattr(user, 'pk', None):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can only update records you created.")

        # Within 1 hour window
        print("now:", timezone.now(), "created_at:", obj.created_at, "diff:", timezone.now() - obj.created_at)
        if timezone.now() - obj.created_at > timedelta(hours=1):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Update window expired: can update only within 1 hour of creation.")

        # Must be assigned to user (mapping active)
        has_access = obj.station and WaterWatchWaterLevelStationForMobileUser.objects.filter(
            mobile_user=user,
            water_level_station__station_id=obj.station.station_id,
            is_active=True
        ).exists()
        if not has_access:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You are not assigned to this station or mapping is inactive.")

        return obj

    def put(self, request, *args, **kwargs):
        instance = self.get_object()

        # Ensure required fields present in payload (station_id, observation_date, water_level)
        missing = [f for f in ('station_id', 'observation_date', 'water_level') if f not in request.data or request.data.get(f) in (None, '', [])]
        if missing:
            return Response(
                {"detail": f"Missing required fields: {', '.join(missing)}"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(
            instance, data=request.data, 
            partial=False, 
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)

        # Extract validated values
        validated = serializer.validated_data
        station_id = validated['station_id']
        obs_dt = validated['observation_date']
        wl = validated['water_level']

        with transaction.atomic():
            update_count = WaterLevelInputForMobileUser.objects.filter(pk=instance.pk).update(
                station_id=station_id,                 
                observation_date=obs_dt,
                water_level=wl,
                updated_by_id=request.user.pk,        
                updated_at=timezone.now()             
            )

        if update_count != 1:
            return Response(
                {"detail": "Update failed (no rows updated)."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Re-fetch updated instance and serialize for response
        updated_obj = WaterLevelInputForMobileUser.objects.select_related(
            'station', 'created_by', 'updated_by'
        ).get(pk=instance.pk)

        from .serializers import WaterLevelUpdateSerializer as ResponseSerializer
        resp_serializer = ResponseSerializer(
            updated_obj, context={'request': request}
        )

        return Response(resp_serializer.data, status=status.HTTP_200_OK)
    
    


class DeleteWaterLevelInputAPIView(APIView):
    """
        DELETE /api/mobile/waterlevel/<int:pk>/
        Only the mobile user (authenticated via MobileAuthBackend) can delete their own record
        within 1 hour of creation and only if the station belongs to their assigned stations.
    """
    authentication_classes = [MobileJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk, *args, **kwargs):
        user = request.user

        obj = get_object_or_404(WaterLevelInputForMobileUser, pk=pk)

        # Must be created by this user
        if obj.created_by_id != getattr(user, 'id', None):
            return Response({'detail': 'You can only delete records you created.'},
                            status=status.HTTP_403_FORBIDDEN)

        # Check created_at within 1 hour
        print("now:", timezone.now(), "created_at:", obj.created_at, "diff:", timezone.now() - obj.created_at)
        one_hour_ago = timezone.now() - timedelta(hours=1)
        if obj.created_at < one_hour_ago:
            return Response({'detail': 'Deletion window expired (allowed only within 1 hour of creation).'},
                            status=status.HTTP_400_BAD_REQUEST)

        # Ensure the user has this station assigned and mapping is active
        station_id = obj.station_id
        if not station_id:
            return Response({'detail': 'Record has no station; cannot verify assignment.'},
                            status=status.HTTP_400_BAD_REQUEST)

        mapping_exists = WaterWatchWaterLevelStationForMobileUser.objects.filter(
            mobile_user=user,
            water_level_station__station_id=station_id,
            is_active=True
        ).exists()

        if not mapping_exists:
            return Response({'detail': 'You do not have permission for this station.'},
                            status=status.HTTP_403_FORBIDDEN)

        obj.delete()
        return Response(
            {"detail": "Record deleted successfully."},
            status=status.HTTP_200_OK, 
        )

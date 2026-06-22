import logging
from django.core.management.base import BaseCommand
from django.db import transaction, IntegrityError
from data_load.models import Station, FfwcStations, FfwcStations2023, FfwcStations2025, Basin, Unit
from datetime import datetime

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    
    help = 'Populates the stations table in ffwcdb with data from ffwc_stations, ffwc_stations_2023, and ffwc_stations_2025 in c7ffwcdb, prioritizing FfwcStations2025 over FfwcStations and FfwcStations2023'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Preview changes without saving to the database')

    def validate_date(self, date_value):
        """Validate and return a date if valid, else return None."""
        if date_value and date_value != '0000-00-00':
            try:
                datetime.strptime(str(date_value), '%Y-%m-%d')
                return date_value
            except (ValueError, TypeError):
                logger.warning(f'Invalid date value: {date_value}, setting to None')
                return None
        return None

    def validate_station_id(self, station_id, station_name, st_id, used_station_ids):
        """Validate station_id to ensure uniqueness, return None if invalid or duplicate."""
        if station_id == 0 or station_id in used_station_ids:
            logger.warning(f'Invalid or duplicate station_id {station_id} for station {station_name} (st_id: {st_id}), setting to None')
            return None
        if station_id is not None:
            used_station_ids.add(station_id)
        return station_id

    def int_to_bool(self, value):
        """Convert integer to boolean."""
        return bool(value) if value is not None else None

    def get_basin(self, basin_name, basin_bn=None):
        """Get Basin object from ffwcdb, matching name and name_bn with basin and basin_bn from FfwcStations2025."""
        if basin_name:
            try:
                # For FfwcStations2025, try matching both name and name_bn
                if basin_bn:
                    basin = Basin.objects.using('default').get(name=basin_name, name_bn=basin_bn)
                    return basin
                # For other datasets or if basin_bn is None, match only by name
                basin = Basin.objects.using('default').get(name=basin_name)
                # If basin_bn is provided but doesn't match, log discrepancy but don't update
                if basin_bn and basin.name_bn != basin_bn:
                    logger.warning(f'Basin name_bn mismatch for {basin_name}: {basin.name_bn} (existing) vs. {basin_bn} (FfwcStations2025), retaining existing')
                return basin
            except Basin.DoesNotExist:
                logger.warning(f'Basin with name {basin_name}' + (f' and name_bn {basin_bn}' if basin_bn else '') + ' not found in ffwcdb, setting to None')
                return None
            except Basin.MultipleObjectsReturned:
                logger.warning(f'Multiple basins found for name {basin_name}' + (f' and name_bn {basin_bn}' if basin_bn else '') + ', returning None')
                return None
        return None

    def get_unit(self, unit_id):
        """Get Unit object from ffwcdb."""
        if unit_id:
            try:
                unit = Unit.objects.using('default').get(id=unit_id)
                return unit
            except Unit.DoesNotExist:
                logger.warning(f'Unit {unit_id} not found in ffwcdb, setting to None')
                return None
        return None

    def log_discrepancy(self, field, station_name, existing_value, new_value, source, station_source):
        """Log discrepancies between existing and new data, only if existing data is not from FfwcStations2025."""
        if station_source == 'FfwcStations2025' and source in ['FfwcStations', 'FfwcStations2023']:
            logger.info(f'Skipping {field} discrepancy for {station_name} from {source} as existing data is from FfwcStations2025')
            return
        logger.warning(
            f'{field} discrepancy for {station_name}: '
            f'{existing_value} (existing, from {station_source}) vs. {new_value} ({source})'
        )

    def log_coordinate_discrepancy(self, station_name, new_lat, new_lon, existing_lat, existing_lon, source, station_source):
        """Log coordinate discrepancies, only if existing data is not from FfwcStations2025."""
        if station_source == 'FfwcStations2025' and source in ['FfwcStations', 'FfwcStations2023']:
            logger.info(f'Skipping coordinate discrepancy for {station_name} from {source} as existing data is from FfwcStations2025')
            return False
        if abs(new_lat - existing_lat) > 0.0001 or abs(new_lon - existing_lon) > 0.0001:
            logger.warning(
                f'Coordinate discrepancy for {station_name} in {source}: '
                f'({new_lat}, {new_lon}) vs. existing ({existing_lat}, {existing_lon}, from {station_source})'
            )
            return True
        return False

    def handle(self, *args, **kwargs):
        dry_run = kwargs.get('dry_run', False)

        # Dictionary to hold station data, using (name, station_code) as the key
        station_data = {}
        used_station_ids = set(Station.objects.using('default').values_list('station_id', flat=True).exclude(station_id__isnull=True))
        used_station_codes = set(Station.objects.using('default').values_list('station_code', flat=True).exclude(station_code__isnull=True))

        # Process datasets in order: FfwcStations2025, FfwcStations, FfwcStations2023
        datasets = [
            ('FfwcStations2025', FfwcStations2025.objects.using('c7ffwcdb').all()),
            ('FfwcStations', FfwcStations.objects.using('c7ffwcdb').all()),
            ('FfwcStations2023', FfwcStations2023.objects.using('c7ffwcdb').all()),
        ]

        for dataset_name, stations in datasets:
            for station in stations:
                name = station.station if dataset_name == 'FfwcStations2025' else station.name
                try:
                    lat = float(station.latitude if dataset_name == 'FfwcStations2025' else station.lat)
                    lon = float(station.longitude if dataset_name == 'FfwcStations2025' else station.long)
                except (ValueError, TypeError):
                    logger.warning(f'Invalid coordinates for {name} in {dataset_name}, skipping')
                    continue
                station_code = station.st_id if dataset_name == 'FfwcStations2025' else None
                river = station.river if hasattr(station, 'river') else ''
                division = station.division if hasattr(station, 'division') else ''
                district = station.district if hasattr(station, 'district') else ''

                # Validate NOT NULL fields
                if not all([name, river, division, district, lat, lon]):
                    logger.warning(f'Skipping station {name} (code: {station_code}) in {dataset_name} due to missing required fields')
                    continue

                key = (name, station_code)

                # Skip FfwcStations or FfwcStations2023 if the station is already in station_data (from FfwcStations2025)
                if dataset_name in ['FfwcStations', 'FfwcStations2023'] and key in station_data:
                    logger.info(f'Skipping duplicate station {name} (code: {station_code}) in {dataset_name} as it exists in a higher-priority dataset')
                    continue

                if key in station_data:
                    logger.warning(f'Duplicate station found in {dataset_name}: {name} (code: {station_code}) at ({lat}, {lon})')
                    self.log_coordinate_discrepancy(
                        name, lat, lon, 
                        station_data[key]['latitude'], 
                        station_data[key]['longitude'], 
                        dataset_name, 
                        station_data[key]['source']
                    )
                else:
                    # Initialize new station data with source tracking
                    station_data[key] = {
                        'source': dataset_name,  # Track the source dataset
                        'station_id': None,
                        'station_code': station_code,
                        'bwdb_id': None,
                        'name': name,
                        'name_bn': None,
                        'ffdata_header': None,
                        'ffdata_header_1': None,
                        'river': river,
                        'river_bn': None,
                        'river_chainage': None,
                        'basin': None,
                        'basin_bn': None,
                        'danger_level': None,
                        'pmdl': None,
                        'highest_water_level': None,
                        'highest_water_level_date': None,
                        'gauge_shift': None,
                        'gauge_factor': None,
                        'effective_date': None,
                        'latitude': lat,
                        'longitude': lon,
                        'h_division': None,
                        'h_division_bn': None,
                        'division': division,
                        'division_bn': None,
                        'district': district,
                        'district_bn': None,
                        'upazilla': None,
                        'upazilla_bn': None,
                        'union': None,
                        'union_bn': None,
                        'five_days_forecast': False,
                        'ten_days_forecast': False,
                        'monsoon_station': False,
                        'pre_monsoon_station': False,
                        'dry_period_station': False,
                        'sms_id': None,
                        'msi_date': None,
                        'msi_year': None,
                        'order_up_down': None,
                        'forecast_observation': None,
                        'status': True,
                        'station_order': None,
                        'medium_range_station': False,
                        'jason_2_satellite_station': False,
                        'experimental': False,
                        'unit': None,
                    }

                existing_data = station_data[key]
                basin = self.get_basin(
                    basin_name=station.basin if dataset_name != 'FfwcStations2025' else getattr(station, 'basin', None),
                    basin_bn=getattr(station, 'basin_bn', None) if dataset_name == 'FfwcStations2025' else None
                )

                if dataset_name == 'FfwcStations':
                    new_danger_level = float(station.dangerlevel) if station.dangerlevel else None
                    new_highest_water_level = float(station.riverhighestwaterlevel) if station.riverhighestwaterlevel else None
                    if existing_data['danger_level'] is not None and existing_data['danger_level'] != new_danger_level:
                        self.log_discrepancy('Danger level', name, existing_data['danger_level'], new_danger_level, dataset_name, existing_data['source'])
                    if existing_data['highest_water_level'] is not None and existing_data['highest_water_level'] != new_highest_water_level:
                        self.log_discrepancy('Highest water level', name, existing_data['highest_water_level'], new_highest_water_level, dataset_name, existing_data['source'])
                    existing_data.update({
                        'river': station.river,
                        'river_chainage': station.river_chainage if station.river_chainage else existing_data.get('river_chainage'),
                        'basin': basin,
                        'basin_bn': basin.name_bn if basin else None,
                        'danger_level': new_danger_level,
                        'highest_water_level': new_highest_water_level,
                        'h_division': station.division,
                        'division': station.division,
                        'district': station.district,
                        'upazilla': station.upazilla,
                        'union': station.union,
                        'five_days_forecast': self.int_to_bool(station.forecast_observation),
                        'order_up_down': station.order_up_down if station.order_up_down is not None else existing_data.get('order_up_down'),
                        'forecast_observation': str(station.forecast_observation),
                        'status': True,
                        'station_order': station.station_order if station.station_order is not None else existing_data.get('station_order'),
                        'medium_range_station': self.int_to_bool(station.medium_range_station),
                        'jason_2_satellite_station': self.int_to_bool(station.jason_2_satellie_station),
                        'experimental': self.int_to_bool(station.experimental),
                        'unit': existing_data.get('unit') or self.get_unit(station.unit_id),
                        'latitude': lat,
                        'longitude': lon,
                    })

                elif dataset_name == 'FfwcStations2023':
                    new_danger_level = float(station.dangerlevel) if station.dangerlevel else None
                    new_highest_water_level = float(station.riverhighestwaterlevel) if station.riverhighestwaterlevel else None
                    if existing_data['danger_level'] is not None and existing_data['danger_level'] != new_danger_level:
                        self.log_discrepancy('Danger level', name, existing_data['danger_level'], new_danger_level, dataset_name, existing_data['source'])
                    if existing_data['highest_water_level'] is not None and existing_data['highest_water_level'] != new_highest_water_level:
                        self.log_discrepancy('Highest water level', name, existing_data['highest_water_level'], new_highest_water_level, dataset_name, existing_data['source'])
                    existing_data.update({
                        'river': station.river,
                        'river_chainage': station.river_chainage if station.river_chainage else existing_data.get('river_chainage'),
                        'basin': basin,
                        'basin_bn': basin.name_bn if basin else None,
                        'danger_level': new_danger_level,
                        'pmdl': None if station.pmdl == '-' else station.pmdl,
                        'highest_water_level': new_highest_water_level,
                        'h_division': station.division,
                        'division': station.division,
                        'district': station.district,
                        'upazilla': station.upazilla,
                        'union': station.union,
                        'five_days_forecast': self.int_to_bool(station.forecast_observation),
                        'order_up_down': station.order_up_down if station.order_up_down is not None else existing_data.get('order_up_down'),
                        'forecast_observation': str(station.forecast_observation),
                        'status': True,
                        'station_order': station.station_order if station.station_order is not None else existing_data.get('station_order'),
                        'medium_range_station': self.int_to_bool(station.medium_range_station),
                        'jason_2_satellite_station': self.int_to_bool(station.jason_2_satellie_station),
                        'unit': existing_data.get('unit') or self.get_unit(station.unit_id),
                        'latitude': lat,
                        'longitude': lon,
                    })

                elif dataset_name == 'FfwcStations2025':
                    new_danger_level = station.dl if hasattr(station, 'dl') else None
                    new_highest_water_level = station.rhwl if hasattr(station, 'rhwl') else None
                    if existing_data['danger_level'] is not None and existing_data['danger_level'] != new_danger_level:
                        self.log_discrepancy('Danger level', name, existing_data['danger_level'], new_danger_level, dataset_name, existing_data['source'])
                    if existing_data['highest_water_level'] is not None and existing_data['highest_water_level'] != new_highest_water_level:
                        self.log_discrepancy('Highest water level', name, existing_data['highest_water_level'], new_highest_water_level, dataset_name, existing_data['source'])
                    if station_code and station_code in used_station_codes and station_code != existing_data['station_code']:
                        logger.warning(f'Duplicate station_code {station_code} for {name}, retaining existing')
                        station_code = existing_data['station_code']
                    existing_data.update({
                        'station_id': self.validate_station_id(station.web_id, name, station.st_id, used_station_ids) if hasattr(station, 'web_id') and hasattr(station, 'st_id') else None,
                        'station_code': station_code,
                        'name_bn': station.station_bn if hasattr(station, 'station_bn') else None,
                        'ffdata_header': station.ffdata_header if hasattr(station, 'ffdata_header') else None,
                        'ffdata_header_1': station.ffdata_header_1 if hasattr(station, 'ffdata_header_1') else None,
                        'river': station.river if hasattr(station, 'river') else river,
                        'river_bn': station.river_bn if hasattr(station, 'river_bn') else None,
                        'river_chainage': station.river_chainage if hasattr(station, 'river_chainage') and station.river_chainage else existing_data.get('river_chainage'),
                        'basin': basin,
                        'basin_bn': basin.name_bn if basin else None,
                        'danger_level': new_danger_level,
                        'pmdl': None if hasattr(station, 'pmdl') and station.pmdl == '-' else station.pmdl if hasattr(station, 'pmdl') else None,
                        'highest_water_level': new_highest_water_level,
                        'highest_water_level_date': self.validate_date(station.date_of_rhwl) if hasattr(station, 'date_of_rhwl') else None,
                        'gauge_shift': station.gauge_shift_pwd_msl if hasattr(station, 'gauge_shift_pwd_msl') else None,
                        'effective_date': self.validate_date(station.effective_date) if hasattr(station, 'effective_date') else None,
                        'latitude': lat,
                        'longitude': lon,
                        'h_division': station.h_division if hasattr(station, 'h_division') else None,
                        'h_division_bn': station.h_division_bn if hasattr(station, 'h_division_bn') else None,
                        'division': station.division if hasattr(station, 'division') else division,
                        'division_bn': station.division_bn if hasattr(station, 'division_bn') else None,
                        'district': station.district if hasattr(station, 'district') else district,
                        'district_bn': station.district_bn if hasattr(station, 'district_bn') else None,
                        'upazilla': station.upazilla if hasattr(station, 'upazilla') else None,
                        'upazilla_bn': station.upazilla_bn if hasattr(station, 'upazilla_bn') else None,
                        'union': station.union if hasattr(station, 'union') else None,
                        'union_bn': station.union_bn if hasattr(station, 'union_bn') else None,
                        'five_days_forecast': self.int_to_bool(station.five_days_forecast) if hasattr(station, 'five_days_forecast') else False,
                        'ten_days_forecast': self.int_to_bool(station.ten_days_forecast) if hasattr(station, 'ten_days_forecast') else False,
                        'monsoon_station': self.int_to_bool(station.monsoon_station) if hasattr(station, 'monsoon_station') else False,
                        'pre_monsoon_station': self.int_to_bool(station.pre_monsoon_station) if hasattr(station, 'pre_monsoon_station') else False,
                        'dry_period_station': self.int_to_bool(station.dry_period_station) if hasattr(station, 'dry_period_station') else False,
                        'sms_id': station.sms_id if hasattr(station, 'sms_id') else None,
                        'status': True,
                        'medium_range_station': self.int_to_bool(station.medium_range_station) if hasattr(station, 'medium_range_station') else existing_data.get('medium_range_station', False),
                        'jason_2_satellite_station': self.int_to_bool(station.jason_2_satellie_station) if hasattr(station, 'jason_2_satellie_station') else existing_data.get('jason_2_satellite_station', False),
                        'unit': existing_data.get('unit') or self.get_unit(None),
                        'order_up_down': existing_data.get('order_up_down'),
                        'forecast_observation': existing_data.get('forecast_observation'),
                        'station_order': existing_data.get('station_order'),
                    })

        # Save to Station model
        if not dry_run:
            with transaction.atomic(using='default'):
                for (name, station_code), data in station_data.items():
                    try:
                        existing_station = Station.objects.using('default').filter(
                            name=data['name'], station_code=data['station_code']
                        ).first()
                        if existing_station:
                            for key, value in data.items():
                                if key != 'source':  # Exclude source from being saved to Station model
                                    setattr(existing_station, key, value)
                            existing_station.save()
                            logger.info(f'Updated station: {name} (code: {station_code})')
                        else:
                            # Exclude source from data when creating new station
                            station_data_to_save = {k: v for k, v in data.items() if k != 'source'}
                            Station.objects.using('default').create(**station_data_to_save)
                            logger.info(f'Created station: {name} (code: {station_code})')
                    except IntegrityError as e:
                        logger.error(f'Failed to save station {name} at ({data["latitude"]}, {data["longitude"]}): {str(e)}')
                        raise
        else:
            logger.info(f'Dry run: Would process {len(station_data)} stations')

        logger.info(f'Successfully processed {len(station_data)} stations in {"dry run" if dry_run else "ffwcdb"}')
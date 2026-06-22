import os
import django
from django.db import connection

# 1. Setup Django Environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ffwc_django_project.settings')
django.setup()

from data_load.models import WaterLevelObservation

def clean_duplicates():
    print("Finding duplicates via Raw SQL in table 'water_level_observations'...")
    
    # Updated query with the correct table name and column names from your models.py
    # Note: station_id is a ForeignKey, so the column in DB is station_id_id
    query = """
        SELECT id FROM water_level_observations
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM water_level_observations
            GROUP BY station_id_id, observation_date
        )
    """
    
    try:
        with connection.cursor() as cursor:
            cursor.execute(query)
            duplicate_ids = [row[0] for row in cursor.fetchall()]

        if not duplicate_ids:
            print("No duplicates found. Your database is clean!")
            return

        print(f"Found {len(duplicate_ids)} duplicate records. Deleting...")
        
        # Delete using Django ORM
        deleted = WaterLevelObservation.objects.filter(id__in=duplicate_ids).delete()
        
        print(f"Cleanup finished! Removed {deleted[0]} records.")
        
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    clean_duplicates()
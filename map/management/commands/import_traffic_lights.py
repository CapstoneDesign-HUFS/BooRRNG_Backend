import csv
from django.core.management.base import BaseCommand
from map.models import TrafficLight

class Command(BaseCommand):
    help = 'Import traffic lights from location.csv file'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to the location.csv file')

    def handle(self, *args, **options):
        file_path = options['csv_file']
        created_count = 0

        with open(file_path, newline='', encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                try:
                    itst_id = int(row['itstId'])
                    name = row['itstNm']
                    lat = float(row['mapCtptIntLat'])
                    lon = float(row['mapCtptIntLot'])

                    obj, created = TrafficLight.objects.update_or_create(
                        itst_id=itst_id,
                        defaults={
                            'name': name,
                            'latitude': lat,
                            'longitude': lon,
                        }
                    )
                    if created:
                        created_count += 1
                except Exception as e:
                    self.stderr.write(f"Error importing row {row}: {e}")

        self.stdout.write(self.style.SUCCESS(f"{created_count} traffic lights imported successfully."))

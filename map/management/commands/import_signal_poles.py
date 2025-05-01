import csv
from django.core.management.base import BaseCommand
from map.models import SignalPole
from map.utils import convert_tm_to_wgs84

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        with open('location.csv', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            count = 0
            skipped = 0
            for row in reader:
                pole_id = row['지주관리번호'].strip()
                x_str = row['X좌표'].strip()
                y_str = row['Y좌표'].strip()

                if x_str == '-' or y_str == '-':
                    skipped += 1
                    continue 

                try:
                    x = float(x_str)
                    y = float(y_str)
                    lat, lon = convert_tm_to_wgs84(x, y)

                    SignalPole.objects.update_or_create(
                        pole_id=pole_id,
                        defaults={
                            'direction': row.get('방향', '').strip(),
                            'x': x,
                            'y': y,
                            'latitude': lat,
                            'longitude': lon
                        }
                    )
                    count += 1
                except Exception as e:
                    skipped += 1
                    print(f"[!] 오류 row 스킵됨 (지주관리번호: {pole_id}) - {e}")

        self.stdout.write(self.style.SUCCESS(f'SignalPole import 완료: {count}개 추가, {skipped}개 스킵됨'))

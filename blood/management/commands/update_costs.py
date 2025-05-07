from django.core.management.base import BaseCommand
from blood.models import BloodRequest, Stock

class Command(BaseCommand):
    help = 'Updates costs for all blood requests'

    def handle(self, *args, **options):
        requests = BloodRequest.objects.all()
        updated = 0
        
        for request in requests:
            try:
                stock = Stock.objects.get(bloodgroup=request.bloodgroup)
                request.cost_at_request = stock.cost_per_unit
                request.total_cost = stock.calculate_total_cost(request.unit)
                request.save()
                updated += 1
            except Stock.DoesNotExist:
                self.stdout.write(self.style.WARNING(
                    f'No stock found for blood group {request.bloodgroup}'
                ))
        
        self.stdout.write(self.style.SUCCESS(
            f'Successfully updated costs for {updated} blood requests'
        )) 
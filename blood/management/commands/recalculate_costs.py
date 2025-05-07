from django.core.management.base import BaseCommand
from blood.models import BloodRequest, Stock
from decimal import Decimal

class Command(BaseCommand):
    help = 'Recalculates total costs for all blood requests'

    def handle(self, *args, **options):
        requests = BloodRequest.objects.all()
        updated = 0
        
        for request in requests:
            try:
                # Get the stock for this blood group
                stock = Stock.objects.get(bloodgroup=request.bloodgroup)
                
                # Update cost information
                request.cost_at_request = stock.cost_per_unit
                request.total_cost = Decimal(str(request.unit)) * stock.cost_per_unit
                request.save()
                
                updated += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Updated request {request.id}: {request.bloodgroup} - {request.unit} units - Total: ₹{request.total_cost}'
                    )
                )
            except Stock.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(
                        f'No stock found for blood group {request.bloodgroup} (Request ID: {request.id})'
                    )
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'Error updating request {request.id}: {str(e)}'
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully updated costs for {updated} blood requests'
            )
        ) 
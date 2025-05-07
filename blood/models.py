from django.db import models
from django.core.validators import MinValueValidator
from patient import models as pmodels
from donor import models as dmodels
from decimal import Decimal

class Stock(models.Model):
    BLOOD_GROUPS = [
        ('A+', 'A+'),
        ('A-', 'A-'),
        ('B+', 'B+'),
        ('B-', 'B-'),
        ('AB+', 'AB+'),
        ('AB-', 'AB-'),
        ('O+', 'O+'),
        ('O-', 'O-'),
    ]
    
    bloodgroup = models.CharField(max_length=10, choices=BLOOD_GROUPS, unique=True)
    unit = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Number of units available"
    )
    cost_per_unit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Cost per unit in currency"
    )
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.bloodgroup} - {self.unit} units (₹{self.cost_per_unit} per unit)"
    
    def add_units(self, units):
        if units > 0:
            self.unit += units
            self.save()
            return True
        return False
    
    def remove_units(self, units):
        if units > 0 and self.unit >= units:
            self.unit -= units
            self.save()
            return True
        return False

    def calculate_total_cost(self, units):
        return self.cost_per_unit * units

    class Meta:
        ordering = ['bloodgroup']
        verbose_name = 'Blood Stock'
        verbose_name_plural = 'Blood Stocks'

class BloodRequest(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
        ('Completed', 'Completed'),
    ]
    
    request_by_patient = models.ForeignKey(pmodels.Patient, null=True, on_delete=models.CASCADE)
    request_by_donor = models.ForeignKey(dmodels.Donor, null=True, on_delete=models.CASCADE)
    patient_name = models.CharField(max_length=30)
    patient_age = models.PositiveIntegerField()
    reason = models.CharField(max_length=500)
    bloodgroup = models.CharField(max_length=10)
    unit = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Pending")
    request_date = models.DateField(auto_now=True)
    cost_at_request = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Cost per unit at the time of request"
    )
    total_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Total cost for the request"
    )

    def calculate_total_cost(self):
        """Calculate the total cost based on units and cost per unit"""
        if self.unit and self.cost_at_request:
            return Decimal(str(self.unit)) * self.cost_at_request
        return Decimal('0.00')

    def save(self, *args, **kwargs):
        # Get the current cost from Stock if not set
        if not self.cost_at_request:
            try:
                stock = Stock.objects.get(bloodgroup=self.bloodgroup)
                self.cost_at_request = stock.cost_per_unit
            except Stock.DoesNotExist:
                self.cost_at_request = Decimal('0.00')
        
        # Calculate total cost
        self.total_cost = self.calculate_total_cost()
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.bloodgroup} - {self.unit} units - Total: ₹{self.total_cost if self.total_cost else 0:.2f}"

class Payment(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Completed', 'Completed'),
        ('Failed', 'Failed'),
    ]
    
    blood_request = models.OneToOneField(BloodRequest, on_delete=models.CASCADE, related_name='payment')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    razorpay_order_id = models.CharField(max_length=255, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=255, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=255, blank=True, null=True)
    payment_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='Pending')
    payment_method = models.CharField(max_length=50, default='Razorpay')
    
    def __str__(self):
        return f"Payment for {self.blood_request} - {self.status}"
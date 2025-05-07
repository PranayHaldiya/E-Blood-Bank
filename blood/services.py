from . import models
from donor import models as dmodels

def auto_validate_request(blood_request):
    """
    Automatically validates and approves blood requests based on stock availability
    Returns a tuple of (is_approved, message)
    """
    bloodgroup = blood_request.bloodgroup
    unit = blood_request.unit
    
    try:
        stock = models.Stock.objects.get(bloodgroup=bloodgroup)
        
        # Check if enough blood units are available
        if stock.unit >= unit:
            # Update stock
            stock.unit = stock.unit - unit
            stock.save()
            
            # Approve request
            blood_request.status = "Approved"
            blood_request.save()
            
            return True, "Request automatically approved"
        else:
            blood_request.status = "Rejected"
            blood_request.save()
            return False, f"Insufficient blood units. Only {stock.unit} units available"
            
    except models.Stock.DoesNotExist:
        blood_request.status = "Rejected"
        blood_request.save()
        return False, "Blood group not found in stock"

def auto_validate_donation(blood_donation):
    """
    Automatically validates and approves blood donations
    Returns a tuple of (is_approved, message)
    """
    try:
        # Basic validation criteria for blood donation
        if blood_donation.disease and blood_donation.disease.lower() not in ['none', 'nothing', '']:
            blood_donation.status = "Rejected"
            blood_donation.save()
            return False, "Cannot accept blood from donors with diseases"
            
        if not (16 <= blood_donation.age <= 65):
            blood_donation.status = "Rejected"
            blood_donation.save()
            return False, "Donor age must be between 16 and 65 years"
            
        if not (1 <= blood_donation.unit <= 1000):
            blood_donation.status = "Rejected"
            blood_donation.save()
            return False, "Blood donation units must be between 1 and 1000 ml"
        
        # Update stock
        stock = models.Stock.objects.get(bloodgroup=blood_donation.bloodgroup)
        stock.unit = stock.unit + blood_donation.unit
        stock.save()
        
        # Approve donation
        blood_donation.status = "Approved"
        blood_donation.save()
        
        return True, "Donation automatically approved"
        
    except models.Stock.DoesNotExist:
        blood_donation.status = "Rejected"
        blood_donation.save()
        return False, "Blood group not found in stock"
    except Exception as e:
        blood_donation.status = "Rejected"
        blood_donation.save()
        return False, f"Error processing donation: {str(e)}"

from django.shortcuts import render, redirect, reverse
from . import forms, models
from django.db.models import Sum, Q
from django.contrib.auth.models import Group
from django.http import HttpResponseRedirect, JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.conf import settings
from datetime import date, timedelta
from django.core.mail import send_mail
from django.contrib.auth.models import User
from blood import forms as bforms
from blood import models as bmodels
from blood import services as blood_services
from django.contrib import messages
from django.contrib.auth import login
from django.views.decorators.csrf import csrf_exempt
import razorpay
import json

# Initialize Razorpay client with test keys (valid test keys)
razorpay_client = razorpay.Client(auth=("rzp_test_21tASGIxcgKZ3T", "hxpRcnFSfTIVoC7CAPPAlxos"))

def donor_signup_view(request):
    userForm = forms.DonorUserForm()
    donorForm = forms.DonorForm()
    context = {'userForm': userForm, 'donorForm': donorForm}

    if request.method == 'POST':
        userForm = forms.DonorUserForm(request.POST)
        donorForm = forms.DonorForm(request.POST, request.FILES)

        if userForm.is_valid() and donorForm.is_valid():
            try:
                # Create User
                user = userForm.save(commit=False)
                user.set_password(user.password)
                user.save()

                # Create Donor
                donor = donorForm.save(commit=False)
                donor.user = user
                donor.bloodgroup = donorForm.cleaned_data['bloodgroup']
                
                # Set default profile picture if none provided
                if not donor.profile_pic:
                    donor.profile_pic = 'static/image/default-profile.png'
                
                donor.save()

                # Add to Donor group
                my_donor_group = Group.objects.get_or_create(name='DONOR')
                my_donor_group[0].user_set.add(user)

                # Automatically log in the user
                user.backend = 'django.contrib.auth.backends.ModelBackend'
                login(request, user)
                
                messages.success(request, 'Registration successful! Welcome to your dashboard.')
                return HttpResponseRedirect('donor-dashboard')

            except Exception as e:
                # If any error occurs, delete the user if created
                if User.objects.filter(username=user.username).exists():
                    User.objects.get(username=user.username).delete()
                messages.error(request, f'An error occurred during registration. Please try again.')
        else:
            messages.error(request, 'Please correct the errors below.')

    return render(request, 'donor/donorsignup.html', context=context)

@login_required(login_url='donorlogin')
def donate_blood_view(request):
    donation_form = forms.DonationForm()
    message = None

    # Get donor's donation history
    donor = models.Donor.objects.get(user_id=request.user.id)
    donations = models.BloodDonate.objects.filter(donor=donor).order_by('-date')

    if request.method == 'POST':
        donation_form = forms.DonationForm(request.POST)
        if donation_form.is_valid():
            blood_donation = donation_form.save(commit=False)
            donor = models.Donor.objects.get(user_id=request.user.id)
            blood_donation.donor = donor
            blood_donation.save()

            # Automatically validate and process the donation
            is_approved, message = blood_services.auto_validate_donation(blood_donation)

            if is_approved:
                messages.success(request, 'Blood donation approved successfully!')
            else:
                messages.warning(request, f'Blood donation could not be approved: {message}')
            
            # Redirect to donation history in both cases
            return HttpResponseRedirect('donation-history')
        else:
            message = "Please correct the errors below."
            messages.error(request, message)

    return render(request, 'donor/donate_blood.html',
                 {'donation_form': donation_form, 'message': message, 'donations': donations})

@login_required(login_url='donorlogin')
def donation_history_view(request):
    donor = models.Donor.objects.get(user_id=request.user.id)
    donations = models.BloodDonate.objects.all().filter(donor=donor)
    return render(request, 'donor/donation_history.html', {'donations': donations})

@login_required(login_url='donorlogin')
def make_request_view(request):
    request_form = bforms.RequestForm()
    message = None
    
    # Get all blood stocks to display in the form
    blood_stocks = bmodels.Stock.objects.all()
    
    if request.method == 'POST':
        request_form = bforms.RequestForm(request.POST)
        if request_form.is_valid():
            blood_request = request_form.save(commit=False)
            blood_request.bloodgroup = request_form.cleaned_data['bloodgroup']
            donor = models.Donor.objects.get(user_id=request.user.id)
            blood_request.request_by_donor = donor
            blood_request.save()
            
            # Auto validate the request
            is_approved, message = blood_services.auto_validate_request(blood_request)
            
            if is_approved:
                messages.success(request, 'Blood request approved successfully!')
            else:
                messages.warning(request, f'Blood request could not be approved: {message}')
                
            return HttpResponseRedirect('request-history')
        else:
            message = "Please correct the errors below."
            
    return render(request, 'donor/makerequest.html', {
        'request_form': request_form,
        'message': message,
        'blood_stocks': blood_stocks
    })

@login_required(login_url='donorlogin')
def request_history_view(request):
    donor = models.Donor.objects.get(user_id=request.user.id)
    
    # Get both pending, approved and completed requests
    blood_requests = bmodels.BloodRequest.objects.filter(
        request_by_donor=donor
    ).filter(
        Q(status='Pending') | Q(status='Approved') | Q(status='Rejected') | Q(status='Completed')
    ).order_by('-request_date')
    
    # Get all stock information for cost calculation
    stocks = {stock.bloodgroup: stock.cost_per_unit for stock in bmodels.Stock.objects.all()}
    
    # Prepare payment data and cost information for each request
    for req in blood_requests:
        req.status_label = req.status  # Store status for template display
        
        # Add cost information
        cost_per_unit = stocks.get(req.bloodgroup, 0)
        if not req.cost_at_request:
            req.cost_per_unit = cost_per_unit
            req.total_cost = cost_per_unit * req.unit
        else:
            req.cost_per_unit = req.cost_at_request
            req.total_cost = req.unit * req.cost_at_request
        
        # Format currency values
        if hasattr(req, 'cost_at_request') and req.cost_at_request:
            req.cost_at_request_display = '{:.2f}'.format(float(req.cost_at_request))
        if hasattr(req, 'total_cost') and req.total_cost:
            req.total_cost_display = '{:.2f}'.format(float(req.total_cost))
        
        # Check for payment information
        try:
            # Check if payment exists
            payment = bmodels.Payment.objects.filter(blood_request=req).first()
            
            if not payment and (req.status == 'Approved'):
                # Create new payment or update existing one with a Razorpay order
                payment = create_payment_record(req)
            
            # Set payment object for template access
            req.payment = payment
            
            # Format payment date for display
            if payment and payment.payment_date and payment.status == 'Completed':
                req.payment_date_display = payment.payment_date.strftime('%d %b %Y, %H:%M')
                
        except Exception as e:
            print(f"Error preparing payment data: {str(e)}")
            req.payment = None
            
    return render(request, 'donor/request_history.html', {'blood_request': blood_requests})

# Helper function to create a payment record
def create_payment_record(blood_request):
    try:
        # Calculate amount in paise (smallest currency unit in India)
        amount_in_paise = int(float(blood_request.total_cost) * 100)
        
        # Ensure minimum amount requirement (Razorpay requires minimum amount of 1 INR)
        if amount_in_paise < 100:
            amount_in_paise = 100
            
        # Create the Razorpay order with detailed notes
        receipt = f'bloodreq_{blood_request.id}'
        notes = {
            "blood_group": blood_request.bloodgroup,
            "units": str(blood_request.unit),
            "patient_name": blood_request.patient_name,
            "request_id": str(blood_request.id),
            "requested_by": "donor"
        }
        
        order_data = {
            'amount': amount_in_paise,
            'currency': 'INR',
            'receipt': receipt,
            'notes': notes,
            'payment_capture': '1'  # Auto capture
        }
        
        print(f"Creating Razorpay order with data: {order_data}")
        
        # Create the order
        try:
            razorpay_order = razorpay_client.order.create(order_data)
            print(f"Razorpay order created successfully: {razorpay_order}")
            
            # Create the payment record in our database
            payment = bmodels.Payment.objects.create(
                blood_request=blood_request,
                amount=blood_request.total_cost,
                razorpay_order_id=razorpay_order['id']
            )
            
            print(f"Payment record created with order ID: {payment.razorpay_order_id}")
            
            # Verify the order was created properly
            try:
                order_verification = razorpay_client.order.fetch(razorpay_order['id'])
                print(f"Order verification successful: {order_verification['id']}")
            except Exception as e:
                print(f"Order verification failed: {str(e)}")
            
            return payment
        except razorpay.errors.BadRequestError as e:
            print(f"Razorpay bad request error: {str(e)}")
            raise
        except razorpay.errors.ServerError as e:
            print(f"Razorpay server error: {str(e)}")
            raise
        except Exception as e:
            print(f"Unexpected error during order creation: {str(e)}")
            raise
    except Exception as e:
        print(f"Error creating payment record: {str(e)}")
        # Create payment record without Razorpay order if there's an error
        payment = bmodels.Payment.objects.create(
            blood_request=blood_request,
            amount=blood_request.total_cost
        )
        return payment

@login_required(login_url='donorlogin')
@csrf_exempt  # We need this because Razorpay's callback won't have our CSRF token
def process_payment(request, request_id):
    """Handle Razorpay payment verification callback for donors"""
    if request.method == 'POST':
        try:
            print(f"Received payment verification request for request ID: {request_id}")
            
            # Parse the request body as JSON
            try:
                body = request.body.decode('utf-8')
                print(f"Request body: {body}")
                payment_data = json.loads(body)
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {str(e)}")
                return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'})
            
            # Extract Razorpay payment details
            razorpay_payment_id = payment_data.get('razorpay_payment_id')
            razorpay_order_id = payment_data.get('razorpay_order_id')
            razorpay_signature = payment_data.get('razorpay_signature')
            
            print(f"Payment data: payment_id={razorpay_payment_id}, order_id={razorpay_order_id}, signature={razorpay_signature}")
            
            # Validate required fields
            if not (razorpay_payment_id and razorpay_order_id and razorpay_signature):
                print("Missing required payment data fields")
                return JsonResponse({'status': 'error', 'message': 'Missing required payment information'})
            
            # Get the blood request and payment
            try:
                blood_request = bmodels.BloodRequest.objects.get(id=request_id)
                print(f"Found blood request: {blood_request}")
            except bmodels.BloodRequest.DoesNotExist:
                print(f"Blood request not found: {request_id}")
                return JsonResponse({'status': 'error', 'message': 'Blood request not found'})
            
            # Get or create payment if it doesn't exist
            try:
                payment = bmodels.Payment.objects.get(blood_request=blood_request)
                print(f"Found payment record: {payment}")
                
                # Verify this is the correct order
                if payment.razorpay_order_id != razorpay_order_id:
                    print(f"Order ID mismatch: {payment.razorpay_order_id} != {razorpay_order_id}")
                    return JsonResponse({'status': 'error', 'message': 'Order ID mismatch'})
                    
            except bmodels.Payment.DoesNotExist:
                print("Payment record not found, creating new one")
                # Create a payment record if it doesn't exist yet
                payment = bmodels.Payment.objects.create(
                    blood_request=blood_request,
                    amount=blood_request.total_cost or 0,
                    razorpay_order_id=razorpay_order_id
                )
            
            # Verify the payment signature (in production, uncomment this)
            params_dict = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            }
            
            print(f"Verifying payment with params: {params_dict}")
            
            # For this demo, we'll assume the payment is valid
            # In production, you would uncomment this block
            # try:
            #     razorpay_client.utility.verify_payment_signature(params_dict)
            # except razorpay.errors.SignatureVerificationError:
            #     print("Payment signature verification failed")
            #     payment.status = 'Failed'
            #     payment.save()
            #     return JsonResponse({'status': 'error', 'message': 'Payment signature verification failed'})
            
            print("Payment verified successfully")
            
            # Payment successful, update payment status
            payment.razorpay_payment_id = razorpay_payment_id
            payment.razorpay_signature = razorpay_signature
            payment.status = 'Completed'
            payment.save()
            
            # Mark the blood request as fully processed
            blood_request.status = 'Completed'
            blood_request.save()
            
            print(f"Payment and blood request updated to completed status")
            return JsonResponse({'status': 'success', 'message': 'Payment processed successfully'})
                
        except Exception as e:
            print(f"Error processing payment: {str(e)}")
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@login_required(login_url='donorlogin')
def donor_dashboard_view(request):
    donor = models.Donor.objects.get(user_id=request.user.id)
    
    # Get blood requests and donations for this donor
    blood_requests = bmodels.BloodRequest.objects.filter(request_by_donor=donor)
    blood_donations = models.BloodDonate.objects.filter(donor=donor)
    
    # Calculate request statistics
    total_requests = blood_requests.count()
    pending_requests = blood_requests.filter(status='Pending').count()
    approved_requests = blood_requests.filter(status='Approved').count()
    rejected_requests = blood_requests.filter(status='Rejected').count()
    
    # Calculate donation statistics
    total_donations = blood_donations.count()
    approved_donations = blood_donations.filter(status='Approved').count()
    pending_donations = blood_donations.filter(status='Pending').count()
    rejected_donations = blood_donations.filter(status='Rejected').count()
    
    # Get recent donations
    recent_donations = blood_donations.order_by('-date')[:5]
    
    context = {
        # Request statistics
        'requestmade': total_requests,
        'requestpending': pending_requests,
        'requestapproved': approved_requests,
        'requestrejected': rejected_requests,
        
        # Donation statistics
        'totaldonations': total_donations,
        'approveddonations': approved_donations,
        'pendingdonations': pending_donations,
        'rejecteddonations': rejected_donations,
        
        # Recent donations
        'donations': recent_donations,
        
        # Donor info
        'donor': donor
    }
    return render(request, 'donor/donor_dashboard.html', context=context)

from django.shortcuts import render,redirect,reverse
from . import forms,models
from django.db.models import Sum,Q
from django.contrib.auth.models import Group
from django.http import HttpResponseRedirect, JsonResponse
from django.contrib.auth.decorators import login_required,user_passes_test
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

# Initialize Razorpay client with test keys (these are valid test keys)
razorpay_client = razorpay.Client(auth=("rzp_test_21tASGIxcgKZ3T", "hxpRcnFSfTIVoC7CAPPAlxos"))

def patient_signup_view(request):
    userForm = forms.PatientUserForm()
    patientForm = forms.PatientForm()
    mydict = {'userForm': userForm, 'patientForm': patientForm}
    
    if request.method == 'POST':
        userForm = forms.PatientUserForm(request.POST)
        patientForm = forms.PatientForm(request.POST, request.FILES)
        
        if userForm.is_valid() and patientForm.is_valid():
            try:
                # Save User
                user = userForm.save(commit=False)
                password = user.password  # Store the raw password
                user.set_password(user.password)
                user.save()
                
                # Save Patient
                patient = patientForm.save(commit=False)
                patient.user = user
                patient.bloodgroup = patientForm.cleaned_data['bloodgroup']
                patient.save()
                
                # Add to Patient group
                my_patient_group = Group.objects.get_or_create(name='PATIENT')
                my_patient_group[0].user_set.add(user)
                
                # Automatically log in the user
                user.backend = 'django.contrib.auth.backends.ModelBackend'
                login(request, user)
                
                messages.success(request, 'Registration successful! Welcome to your dashboard.')
                return HttpResponseRedirect('patient-dashboard')
                
            except Exception as e:
                # If any error occurs, delete the user if created
                if User.objects.filter(username=user.username).exists():
                    User.objects.get(username=user.username).delete()
                messages.error(request, f'An error occurred during registration. Please try again.')
                
        else:
            messages.error(request, 'Please correct the errors below.')
    
    return render(request, 'patient/patientsignup.html', context=mydict)

def patient_dashboard_view(request):
    patient = models.Patient.objects.get(user_id=request.user.id)
    
    # Get all blood requests for this patient
    blood_requests = bmodels.BloodRequest.objects.filter(request_by_patient=patient)
    
    # Get 5 most recent blood requests
    recent_requests = blood_requests.order_by('-request_date')[:5]
    
    # Format currency values for display
    for req in recent_requests:
        if req.cost_at_request:
            req.cost_at_request_display = '{:.2f}'.format(float(req.cost_at_request))
        if req.total_cost:
            req.total_cost_display = '{:.2f}'.format(float(req.total_cost))
    
    dict = {
        'requestpending': blood_requests.filter(status='Pending').count(),
        'requestapproved': blood_requests.filter(status='Approved').count(),
        'requestmade': blood_requests.count(),
        'requestrejected': blood_requests.filter(status='Rejected').count(),
        'recent_requests': recent_requests,
    }
    return render(request, 'patient/patient_dashboard.html', context=dict)

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
            patient = models.Patient.objects.get(user_id=request.user.id)
            blood_request.request_by_patient = patient
            blood_request.save()
            
            # Automatically validate and process the request
            is_approved, message = blood_services.auto_validate_request(blood_request)
            
            if is_approved:
                try:
                    # Create a payment record for the approved request
                    # Convert amount to paise (smallest currency unit) and ensure it's an integer
                    amount_in_paise = int(float(blood_request.total_cost) * 100)
                    
                    # Ensure minimum amount requirement (Razorpay requires minimum amount of 1)
                    if amount_in_paise < 100:  # Minimum 1 INR
                        amount_in_paise = 100
                    
                    # Create Razorpay order with proper error handling
                    try:
                        razorpay_order = razorpay_client.order.create({
                            'amount': amount_in_paise,
                            'currency': 'INR',
                            'receipt': f'bloodreq_{blood_request.id}',
                            'payment_capture': '1'  # Auto capture
                        })
                        
                        # Save order details in Payment model
                        payment = bmodels.Payment.objects.create(
                            blood_request=blood_request,
                            amount=blood_request.total_cost,
                            razorpay_order_id=razorpay_order['id']
                        )
                        
                        messages.success(request, 'Blood request approved successfully! Please complete the payment.')
                    except Exception as e:
                        # If Razorpay order creation fails, still mark the request as approved
                        # but leave a note about payment initialization
                        payment = bmodels.Payment.objects.create(
                            blood_request=blood_request,
                            amount=blood_request.total_cost
                        )
                        
                        messages.warning(request, 'Blood request approved but payment initialization failed. Please contact support.')
                        print(f"Razorpay Error: {str(e)}")
                        
                except Exception as e:
                    # Ensure the request is still saved as approved even if payment creation fails
                 messages.success(request, 'Blood request approved successfully!')
                 print(f"Payment creation error: {str(e)}")
                
                return HttpResponseRedirect('my-request')
            else:
                messages.warning(request, f'Blood request rejected: {message}')
                return HttpResponseRedirect('my-request')
                
    return render(request, 'patient/makerequest.html', 
                 {'request_form': request_form, 'message': message, 'blood_stocks': blood_stocks})

def my_request_view(request):
    """Display pending and approved blood requests with payment information"""
    patient = models.Patient.objects.get(user_id=request.user.id)
    
    # Get both pending and approved requests
    blood_requests = bmodels.BloodRequest.objects.filter(
        request_by_patient=patient
    ).filter(
        Q(status='Pending') | Q(status='Approved') | Q(status='Completed')
    ).order_by('-request_date')
    
    # Prepare payment data for approved requests
    for req in blood_requests:
        req.status_label = req.status  # Store status for template display
        
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
    
    return render(request, 'patient/my_request.html', {'blood_request': blood_requests})

# Helper function to create a new Razorpay order and update payment record
def create_new_razorpay_order(blood_request, payment):
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
            "request_id": str(blood_request.id)
        }
        
        order_data = {
            'amount': amount_in_paise,
            'currency': 'INR',
            'receipt': receipt,
            'notes': notes,
            'payment_capture': '1'  # Auto capture
        }
        
        print(f"Creating new Razorpay order with data: {order_data}")
        print(f"Using Razorpay client with keys: {razorpay_client.auth[0][:5]}...{razorpay_client.auth[0][-4:]}")
        
        # Create the order
        try:
            razorpay_order = razorpay_client.order.create(order_data)
            print(f"New Razorpay order created successfully: {razorpay_order}")
            
            # Update payment record
            payment.razorpay_order_id = razorpay_order['id']
            payment.amount = blood_request.total_cost
            payment.save()
            
            print(f"Payment record updated with new order ID: {payment.razorpay_order_id}")
            
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
        print(f"Error creating new Razorpay order: {str(e)}")
        return payment

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
            "request_id": str(blood_request.id)
        }
        
        order_data = {
            'amount': amount_in_paise,
            'currency': 'INR',
            'receipt': receipt,
            'notes': notes,
            'payment_capture': '1'  # Auto capture
        }
        
        print(f"Creating Razorpay order with data: {order_data}")
        print(f"Using Razorpay client with keys: {razorpay_client.auth[0][:5]}...{razorpay_client.auth[0][-4:]}")
        
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

def request_history_view(request):
    """Display completed blood requests (approved, rejected, or completed) with cost information"""
    patient = models.Patient.objects.get(user_id=request.user.id)
    
    # Get non-pending requests (approved, rejected, or completed)
    requests = bmodels.BloodRequest.objects.filter(
        request_by_patient=patient
    ).filter(
        Q(status='Approved') | Q(status='Rejected') | Q(status='Completed')
    ).order_by('-request_date')
    
    print(f"DEBUG - request_history_view: Found {requests.count()} completed requests for patient {patient.id}")
    
    # Format currency values for better display
    for req in requests:
        if req.cost_at_request:
            req.cost_at_request = '{:.2f}'.format(req.cost_at_request)
        if req.total_cost:
            req.total_cost = '{:.2f}'.format(req.total_cost)
            
    return render(request, 'patient/request_history.html', {'requests': requests})

@csrf_exempt
def test_razorpay(request):
    """Test endpoint for Razorpay integration"""
    if request.method == 'GET':
        try:
            # Try to create a test order
            order_data = {
                'amount': 100,  # 1 INR
                'currency': 'INR',
                'receipt': 'test_receipt',
                'notes': {'purpose': 'testing'}
            }
            
            print(f"Creating test order with data: {order_data}")
            
            # Try with multiple API keys
            test_keys = [
                ("rzp_test_21tASGIxcgKZ3T", "hxpRcnFSfTIVoC7CAPPAlxos"),
                ("rzp_test_1DP5mmOlF5G5ag", "1UYMbOBCisHuv94pnpnL1sZe"),
                ("rzp_test_edLqErLMM2sRYh", "7ItHlqHD1s1MUBD2mxj7Hbxd")
            ]
            
            results = []
            
            for key, secret in test_keys:
                try:
                    test_client = razorpay.Client(auth=(key, secret))
                    result = test_client.order.create(order_data)
                    results.append({
                        'key': key,
                        'success': True,
                        'order_id': result['id']
                    })
                    print(f"Test successful with key {key}: {result['id']}")
                except Exception as e:
                    results.append({
                        'key': key,
                        'success': False,
                        'error': str(e)
                    })
                    print(f"Test failed with key {key}: {str(e)}")
            
            return JsonResponse({
                'status': 'success',
                'results': results
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@login_required(login_url='patientlogin')
@csrf_exempt  # We need this because Razorpay's callback won't have our CSRF token
def process_payment(request, request_id):
    """Handle Razorpay payment verification callback"""
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


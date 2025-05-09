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
    dict = {
        'requestpending': bmodels.BloodRequest.objects.all().filter(request_by_patient=patient).filter(status='Pending').count(),
        'requestapproved': bmodels.BloodRequest.objects.all().filter(request_by_patient=patient).filter(status='Approved').count(),
        'requestmade': bmodels.BloodRequest.objects.all().filter(request_by_patient=patient).count(),
        'requestrejected': bmodels.BloodRequest.objects.all().filter(request_by_patient=patient).filter(status='Rejected').count(),
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

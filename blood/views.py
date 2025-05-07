from django.shortcuts import render,redirect,reverse
from . import forms,models
from django.db.models import Sum,Q
from django.contrib.auth.models import Group
from django.http import HttpResponseRedirect, HttpResponse
from django.contrib.auth.decorators import login_required,user_passes_test
from django.conf import settings
from datetime import date, timedelta
from django.core.mail import send_mail
from django.contrib.auth.models import User
from donor import models as dmodels
from patient import models as pmodels
from donor import forms as dforms
from patient import forms as pforms
from . import services
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from datetime import datetime
from django.contrib import messages

def home_view(request):
    x=models.Stock.objects.all()
    print(x)
    if len(x)==0:
        blood1=models.Stock()
        blood1.bloodgroup="A+"
        blood1.save()

        blood2=models.Stock()
        blood2.bloodgroup="A-"
        blood2.save()

        blood3=models.Stock()
        blood3.bloodgroup="B+"
        blood3.save()        

        blood4=models.Stock()
        blood4.bloodgroup="B-"
        blood4.save()

        blood5=models.Stock()
        blood5.bloodgroup="AB+"
        blood5.save()

        blood6=models.Stock()
        blood6.bloodgroup="AB-"
        blood6.save()

        blood7=models.Stock()
        blood7.bloodgroup="O+"
        blood7.save()

        blood8=models.Stock()
        blood8.bloodgroup="O-"
        blood8.save()

    if request.user.is_authenticated:
        return HttpResponseRedirect('afterlogin')  
    return render(request,'blood/index.html')

def is_donor(user):
    return user.groups.filter(name='DONOR').exists()

def is_patient(user):
    return user.groups.filter(name='PATIENT').exists()


def afterlogin_view(request):
    if is_donor(request.user):      
        return redirect('donor-dashboard')
                
    elif is_patient(request.user):
        return redirect('patient-dashboard')
    else:
        return redirect('admin-dashboard')

@login_required(login_url='adminlogin')
def admin_dashboard_view(request):
    totalunit=models.Stock.objects.aggregate(Sum('unit'))
    dict={

        'A1':models.Stock.objects.get(bloodgroup="A+"),
        'A2':models.Stock.objects.get(bloodgroup="A-"),
        'B1':models.Stock.objects.get(bloodgroup="B+"),
        'B2':models.Stock.objects.get(bloodgroup="B-"),
        'AB1':models.Stock.objects.get(bloodgroup="AB+"),
        'AB2':models.Stock.objects.get(bloodgroup="AB-"),
        'O1':models.Stock.objects.get(bloodgroup="O+"),
        'O2':models.Stock.objects.get(bloodgroup="O-"),
        'totaldonors':dmodels.Donor.objects.all().count(),
        'totalbloodunit':totalunit['unit__sum'],
        'totalrequest':models.BloodRequest.objects.all().count(),
        'totalapprovedrequest':models.BloodRequest.objects.all().filter(status='Approved').count()
    }
    return render(request,'blood/admin_dashboard.html',context=dict)

@login_required(login_url='adminlogin')
def admin_blood_view(request):
    dict={
        'bloodForm':forms.BloodForm(),
        'A1':models.Stock.objects.get(bloodgroup="A+"),
        'A2':models.Stock.objects.get(bloodgroup="A-"),
        'B1':models.Stock.objects.get(bloodgroup="B+"),
        'B2':models.Stock.objects.get(bloodgroup="B-"),
        'AB1':models.Stock.objects.get(bloodgroup="AB+"),
        'AB2':models.Stock.objects.get(bloodgroup="AB-"),
        'O1':models.Stock.objects.get(bloodgroup="O+"),
        'O2':models.Stock.objects.get(bloodgroup="O-"),
    }
    if request.method=='POST':
        bloodgroup = request.POST.get('bloodgroup')
        unit = request.POST.get('unit')
        cost_per_unit = request.POST.get('cost_per_unit')
        
        if bloodgroup and unit and cost_per_unit:
            try:
                stock = models.Stock.objects.get(bloodgroup=bloodgroup)
                stock.unit = int(unit)
                stock.cost_per_unit = float(cost_per_unit)
                stock.save()
                messages.success(request, f'Successfully updated {bloodgroup} blood stock and cost')
            except models.Stock.DoesNotExist:
                messages.error(request, f'Blood group {bloodgroup} not found')
            except (ValueError, TypeError):
                messages.error(request, 'Invalid values provided')
        else:
            messages.error(request, 'Please fill all fields')
        
        return redirect('admin-blood')
    return render(request,'blood/admin_blood.html',context=dict)


@login_required(login_url='adminlogin')
def admin_donor_view(request):
    donors=dmodels.Donor.objects.all()
    return render(request,'blood/admin_donor.html',{'donors':donors})

@login_required(login_url='adminlogin')
def update_donor_view(request,pk):
    donor = dmodels.Donor.objects.get(id=pk)
    user = dmodels.User.objects.get(id=donor.user_id)
    userForm = dforms.DonorUserUpdateForm(instance=user)
    donorForm = dforms.DonorForm(request.FILES,instance=donor)
    mydict = {'userForm':userForm,'donorForm':donorForm}
    
    if request.method=='POST':
        userForm = dforms.DonorUserUpdateForm(request.POST,instance=user)
        donorForm = dforms.DonorForm(request.POST,request.FILES,instance=donor)
        if userForm.is_valid() and donorForm.is_valid():
            user = userForm.save()
            donor = donorForm.save(commit=False)
            donor.user = user
            donor.bloodgroup = donorForm.cleaned_data['bloodgroup']
            
            # Set default profile picture if none provided
            if not donor.profile_pic:
                donor.profile_pic = 'static/image/default-profile.png'
                
            donor.save()
            return redirect('admin-donor')
    return render(request,'blood/update_donor.html',context=mydict)


@login_required(login_url='adminlogin')
def delete_donor_view(request,pk):
    donor=dmodels.Donor.objects.get(id=pk)
    user=User.objects.get(id=donor.user_id)
    user.delete()
    donor.delete()
    return HttpResponseRedirect('/admin-donor')

@login_required(login_url='adminlogin')
def admin_patient_view(request):
    patients=pmodels.Patient.objects.all()
    return render(request,'blood/admin_patient.html',{'patients':patients})


@login_required(login_url='adminlogin')
def update_patient_view(request,pk):
    patient = pmodels.Patient.objects.get(id=pk)
    user = pmodels.User.objects.get(id=patient.user_id)
    userForm = pforms.PatientUserUpdateForm(instance=user)
    patientForm = pforms.PatientForm(request.FILES,instance=patient)
    mydict = {'userForm':userForm,'patientForm':patientForm}
    
    if request.method=='POST':
        userForm = pforms.PatientUserUpdateForm(request.POST,instance=user)
        patientForm = pforms.PatientForm(request.POST,request.FILES,instance=patient)
        if userForm.is_valid() and patientForm.is_valid():
            user = userForm.save()
            patient = patientForm.save(commit=False)
            patient.user = user
            patient.bloodgroup = patientForm.cleaned_data['bloodgroup']
            patient.save()
            return redirect('admin-patient')
    return render(request,'blood/update_patient.html',context=mydict)


@login_required(login_url='adminlogin')
def delete_patient_view(request,pk):
    patient=pmodels.Patient.objects.get(id=pk)
    user=User.objects.get(id=patient.user_id)
    user.delete()
    patient.delete()
    return HttpResponseRedirect('/admin-patient')

@login_required(login_url='adminlogin')
def admin_request_view(request):
    requests = models.BloodRequest.objects.all().filter(status='Pending')
    
    # Add payment information for each request
    for req in requests:
        # Format the cost values to 2 decimal places
        if hasattr(req, 'cost_at_request') and req.cost_at_request:
            req.cost_at_request_display = '{:.2f}'.format(float(req.cost_at_request))
        if hasattr(req, 'total_cost') and req.total_cost:
            req.total_cost_display = '{:.2f}'.format(float(req.total_cost))
            
        # Check for payment information
        try:
            payment = models.Payment.objects.filter(blood_request=req).first()
            req.payment = payment
            # Format payment date for display
            if payment and payment.payment_date:
                req.payment_date_display = payment.payment_date.strftime('%d %b %Y, %H:%M')
        except Exception as e:
            print(f"Error fetching payment data: {str(e)}")
            req.payment = None
            
    return render(request,'blood/admin_request.html',{'requests':requests})

@login_required(login_url='adminlogin')
def admin_request_history_view(request):
    requests = models.BloodRequest.objects.all().exclude(status='Pending').order_by('-request_date')
    
    for req in requests:
        # Format the cost values to 2 decimal places
        if req.cost_at_request:
            req.cost_at_request = '{:.2f}'.format(req.cost_at_request)
        if req.total_cost:
            req.total_cost = '{:.2f}'.format(req.total_cost)
            
        # Add payment information
        try:
            payment = models.Payment.objects.filter(blood_request=req).first()
            if payment:
                req.payment = payment
                # Format payment date for display
                if payment.payment_date:
                    req.payment_date_display = payment.payment_date.strftime('%d %b %Y, %H:%M')
        except Exception as e:
            print(f"Error fetching payment data: {str(e)}")
            req.payment = None
            
    return render(request,'blood/admin_request_history.html',{'requests':requests})

@login_required(login_url='adminlogin')
def admin_donation_view(request):
    donations=dmodels.BloodDonate.objects.all()
    return render(request,'blood/admin_donation.html',{'donations':donations})

@login_required(login_url='adminlogin')
def update_approve_status_view(request,pk):
    req = models.BloodRequest.objects.get(id=pk)
    is_approved, message = services.auto_validate_request(req)
    requests = models.BloodRequest.objects.all().filter(status='Pending')
    return render(request,'blood/admin_request.html',{'requests':requests,'message':message})

@login_required(login_url='adminlogin')
def update_reject_status_view(request,pk):
    req = models.BloodRequest.objects.get(id=pk)
    req.status = "Rejected"
    req.save()
    return HttpResponseRedirect('/admin-request')

@login_required(login_url='adminlogin')
def approve_donation_view(request,pk):
    donation = dmodels.BloodDonate.objects.get(id=pk)
    is_approved, message = services.auto_validate_donation(donation)
    if not is_approved:
        # If validation fails, redirect with message
        return render(request, 'blood/admin_donation.html', 
                     {'donations': dmodels.BloodDonate.objects.all(), 'message': message})
    return HttpResponseRedirect('/admin-donation')

@login_required(login_url='adminlogin')
def reject_donation_view(request,pk):
    donation = dmodels.BloodDonate.objects.get(id=pk)
    donation.status = 'Rejected'
    donation.save()
    return HttpResponseRedirect('/admin-donation')

@login_required(login_url='adminlogin')
def download_request_history_pdf(request):
    # Get all blood requests excluding pending ones
    requests = models.BloodRequest.objects.all().exclude(status='Pending')
    
    # Fetch payment information for each request
    for req in requests:
        # Format the cost values to 2 decimal places
        if req.cost_at_request:
            req.cost_at_request = '{:.2f}'.format(req.cost_at_request)
        if req.total_cost:
            req.total_cost = '{:.2f}'.format(req.total_cost)
            
        # Add payment information
        try:
            payment = models.Payment.objects.filter(blood_request=req).first()
            if payment:
                req.payment = payment
                # Format payment date for display
                if payment.payment_date:
                    req.payment_date_display = payment.payment_date.strftime('%d %b %Y, %H:%M')
        except Exception as e:
            print(f"Error fetching payment data: {str(e)}")
            req.payment = None
    
    # Create the HttpResponse object with PDF headers
    response = HttpResponse(content_type='application/pdf')
    current_date = datetime.now().strftime('%Y%m%d%H%M%S')  # Adding hours, minutes, seconds for uniqueness
    response['Content-Disposition'] = f'attachment; filename="blood_request_history_{current_date}.pdf"'
    
    # Create the PDF object using ReportLab
    doc = SimpleDocTemplate(
        response,
        pagesize=landscape(letter),
        rightMargin=inch/2,
        leftMargin=inch/2,
        topMargin=inch/2,
        bottomMargin=inch/2
    )
    
    # Container for PDF elements
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=1,  # Center alignment
        textColor=colors.HexColor('#086fd6')  # Matching the website's blue
    )
    
    # Add title with current date
    title = Paragraph("Blood Request History Report", title_style)
    elements.append(title)
    elements.append(Spacer(1, 20))
    
    # Add date
    date_style = ParagraphStyle(
        'DateStyle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.grey,
        alignment=1
    )
    date_text = Paragraph(f"Generated on: {datetime.now().strftime('%B %d, %Y, %H:%M:%S')}", date_style)
    elements.append(date_text)
    elements.append(Spacer(1, 30))
    
    # Define table data
    data = [['Request Date', 'Blood Group', 'Unit (ml)', 'Status', 'Payment Status', 'Total Cost', 'Patient Name', 'Reason']]
    
    for request in requests:
        if hasattr(request, 'request_by_patient') and request.request_by_patient:
            patient = request.request_by_patient
            patient_name = f"{patient.user.first_name} {patient.user.last_name}"
            disease = patient.disease
        else:
            patient_name = request.patient_name
            disease = request.reason
            
        status_color = colors.green if request.status == 'Approved' else colors.red
        
        # Determine payment status
        if hasattr(request, 'payment') and request.payment:
            if request.payment.status == 'Completed':
                payment_status = "Paid"
                if hasattr(request.payment, 'razorpay_payment_id') and request.payment.razorpay_payment_id:
                    payment_id = request.payment.razorpay_payment_id[:10] + "..."
                    if hasattr(request, 'payment_date_display'):
                        payment_status = f"Paid ({payment_id})\n{request.payment_date_display}"
                    else:
                        payment_status = f"Paid ({payment_id})"
            elif request.payment.status == 'Pending':
                payment_status = "Payment Pending"
            else:
                payment_status = "Payment Failed"
        elif request.status == 'Approved':
            payment_status = "Not Paid"
        else:
            payment_status = "N/A"
        
        data.append([
            request.request_date.strftime('%Y-%m-%d'),
            request.bloodgroup,
            str(request.unit),
            request.status,
            payment_status,
            f"₹{request.total_cost}",
            patient_name,
            disease
        ])
    
    # Create table with adjusted column widths
    table = Table(data, colWidths=[1.2*inch, 0.8*inch, 0.8*inch, 0.8*inch, 1.5*inch, 0.8*inch, 1.5*inch, 2.6*inch])
    
    # Enhanced table style
    style = TableStyle([
        # Header style
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#086fd6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        
        # Body style
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (7, 1), (7, -1), 'LEFT'),  # Left align reason/disease
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        
        # Zebra striping
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        
        # Rounded corners for header
        ('ROUNDEDCORNERS', [10, 10, 10, 10]),
        
        # Cell padding
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ])
    table.setStyle(style)
    
    # Add table to elements
    elements.append(table)
    
    # Add footer
    footer_style = ParagraphStyle(
        'FooterStyle',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        alignment=1
    )
    elements.append(Spacer(1, 30))
    footer = Paragraph(f"Generated by Blood Bank Management System - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", footer_style)
    elements.append(footer)
    
    # Generate PDF
    doc.build(elements)
    return response

@login_required(login_url='adminlogin')
def download_donor_list_pdf(request):
    # Get all donors
    donors = dmodels.Donor.objects.all()
    
    # Create the HttpResponse object with PDF headers
    response = HttpResponse(content_type='application/pdf')
    current_date = datetime.now().strftime('%Y%m%d%H%M%S')  # Adding hours, minutes, seconds for uniqueness
    response['Content-Disposition'] = f'attachment; filename="donor_list_{current_date}.pdf"'
    
    # Create the PDF object using ReportLab
    doc = SimpleDocTemplate(
        response,
        pagesize=landscape(letter),
        rightMargin=inch/2,
        leftMargin=inch/2,
        topMargin=inch/2,
        bottomMargin=inch/2
    )
    
    # Container for PDF elements
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=1,
        textColor=colors.HexColor('#086fd6')
    )
    
    # Add title
    title = Paragraph("Blood Donor List", title_style)
    elements.append(title)
    elements.append(Spacer(1, 20))
    
    # Add date
    date_style = ParagraphStyle(
        'DateStyle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.grey,
        alignment=1
    )
    date_text = Paragraph(f"Generated on: {datetime.now().strftime('%B %d, %Y, %H:%M:%S')}", date_style)
    elements.append(date_text)
    elements.append(Spacer(1, 30))
    
    # Define table data
    data = [['Name', 'Blood Group', 'Mobile', 'Address']]
    
    for donor in donors:
        data.append([
            f"{donor.user.first_name} {donor.user.last_name}",
            donor.bloodgroup,
            donor.mobile,
            donor.address
        ])
    
    # Create table
    table = Table(data, colWidths=[2*inch, 1.5*inch, 2*inch, 4.5*inch])
    
    # Add style to table
    style = TableStyle([
        # Header style
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#086fd6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        
        # Body style
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (3, 1), (3, -1), 'LEFT'),  # Left align addresses
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        
        # Zebra striping
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        
        # Cell padding
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ])
    table.setStyle(style)
    
    # Add table to elements
    elements.append(table)
    
    # Add footer
    footer_style = ParagraphStyle(
        'FooterStyle',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        alignment=1
    )
    elements.append(Spacer(1, 30))
    footer = Paragraph(f"Generated by Blood Bank Management System - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", footer_style)
    elements.append(footer)
    
    # Generate PDF
    doc.build(elements)
    return response

@login_required(login_url='adminlogin')
def download_patient_list_pdf(request):
    # Get all patients
    patients = pmodels.Patient.objects.all()
    
    # Create the HttpResponse object with PDF headers
    response = HttpResponse(content_type='application/pdf')
    current_date = datetime.now().strftime('%Y%m%d%H%M%S')  # Adding hours, minutes, seconds for uniqueness
    response['Content-Disposition'] = f'attachment; filename="patient_list_{current_date}.pdf"'
    
    # Create the PDF object using ReportLab
    doc = SimpleDocTemplate(
        response,
        pagesize=landscape(letter),
        rightMargin=inch/2,
        leftMargin=inch/2,
        topMargin=inch/2,
        bottomMargin=inch/2
    )
    
    # Container for PDF elements
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=1,
        textColor=colors.HexColor('#086fd6')
    )
    
    # Add title
    title = Paragraph("Blood Patient List", title_style)
    elements.append(title)
    elements.append(Spacer(1, 20))
    
    # Add date
    date_style = ParagraphStyle(
        'DateStyle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.grey,
        alignment=1
    )
    date_text = Paragraph(f"Generated on: {datetime.now().strftime('%B %d, %Y, %H:%M:%S')}", date_style)
    elements.append(date_text)
    elements.append(Spacer(1, 30))
    
    # Define table data
    data = [['Name', 'Age', 'Blood Group', 'Disease', 'Doctor', 'Mobile']]
    
    for patient in patients:
        data.append([
            f"{patient.user.first_name} {patient.user.last_name}",
            str(patient.age),
            patient.bloodgroup,
            patient.disease,
            patient.doctorname,
            patient.mobile
        ])
    
    # Create table
    table = Table(data, colWidths=[2*inch, 0.8*inch, 1.2*inch, 2.5*inch, 2*inch, 1.5*inch])
    
    # Add style to table
    style = TableStyle([
        # Header style
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#086fd6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        
        # Body style
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (3, 1), (3, -1), 'LEFT'),  # Left align disease
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        
        # Zebra striping
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        
        # Cell padding
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ])
    table.setStyle(style)
    
    # Add table to elements
    elements.append(table)
    
    # Add footer
    footer_style = ParagraphStyle(
        'FooterStyle',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        alignment=1
    )
    elements.append(Spacer(1, 30))
    footer = Paragraph(f"Generated by Blood Bank Management System - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", footer_style)
    elements.append(footer)
    
    # Generate PDF
    doc.build(elements)
    return response

def contact_view(request):
    return render(request, 'blood/contact.html')
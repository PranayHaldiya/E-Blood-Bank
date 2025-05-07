from django import forms
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from . import models

class PatientUserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'password']
        widgets = {
            'password': forms.PasswordInput(),
            'first_name': forms.TextInput(attrs={'required': True, 'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'required': True, 'class': 'form-control'}),
            'username': forms.TextInput(attrs={'required': True, 'class': 'form-control'})
        }
        
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), validators=[
        RegexValidator(
            regex=r'^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{8,}$',
            message='Password must be at least 8 characters long and contain both letters and numbers'
        )
    ])
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        username = cleaned_data.get('username')
        
        if not cleaned_data.get('first_name'):
            self.add_error('first_name', 'First name is required')
            
        if not cleaned_data.get('last_name'):
            self.add_error('last_name', 'Last name is required')
            
        if not self.instance.pk:  # Only validate passwords for new users
            if password and confirm_password:
                if password != confirm_password:
                    self.add_error('confirm_password', 'Passwords do not match')
            
        if username and User.objects.filter(username=username).exists() and not User.objects.filter(username=username, id=self.instance.id).exists():
            self.add_error('username', 'Username already exists')
            
        return cleaned_data

class PatientUserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username']
        widgets = {
            'first_name': forms.TextInput(attrs={'required': True, 'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'required': True, 'class': 'form-control'}),
            'username': forms.TextInput(attrs={'required': True, 'class': 'form-control'})
        }
    
    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        
        if not cleaned_data.get('first_name'):
            self.add_error('first_name', 'First name is required')
            
        if not cleaned_data.get('last_name'):
            self.add_error('last_name', 'Last name is required')
            
        if username and User.objects.filter(username=username).exists() and not User.objects.filter(username=username, id=self.instance.id).exists():
            self.add_error('username', 'Username already exists')
            
        return cleaned_data

class PatientForm(forms.ModelForm):
    BLOOD_GROUPS = [
        ('', 'Select Blood Group'),
        ('A+', 'A+'),
        ('A-', 'A-'),
        ('B+', 'B+'),
        ('B-', 'B-'),
        ('AB+', 'AB+'),
        ('AB-', 'AB-'),
        ('O+', 'O+'),
        ('O-', 'O-'),
    ]
    
    bloodgroup = forms.ChoiceField(
        choices=BLOOD_GROUPS,
        widget=forms.Select(attrs={'class': 'form-control', 'required': True})
    )
    
    age = forms.IntegerField(
        min_value=0,
        max_value=150,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'required': True}),
        help_text='Age must be between 0 and 150 years'
    )
    
    disease = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'required': True}),
        help_text='Please specify your medical condition'
    )
    
    doctorname = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'required': True}),
        help_text='Name of your treating doctor'
    )
    
    mobile = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'required': True}),
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message='Phone number must be entered in the format: "+999999999". Up to 15 digits allowed.'
            )
        ],
        help_text='Enter a valid phone number (e.g., +919876543210)'
    )
    
    address = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'required': True}),
        help_text='Enter your complete address'
    )
    
    profile_pic = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control'}),
        help_text='Upload your profile picture (optional)'
    )
    
    class Meta:
        model = models.Patient
        fields = ['age', 'bloodgroup', 'disease', 'address', 'doctorname', 'mobile', 'profile_pic']
        
    def clean(self):
        cleaned_data = super().clean()
        
        required_fields = {
            'bloodgroup': 'Blood group is required',
            'address': 'Address is required',
            'doctorname': 'Doctor name is required',
            'disease': 'Medical condition is required',
            'mobile': 'Mobile number is required',
            'age': 'Age is required'
        }
        
        for field, message in required_fields.items():
            if not cleaned_data.get(field):
                self.add_error(field, message)
                
        if cleaned_data.get('bloodgroup') == '':
            self.add_error('bloodgroup', 'Please select a blood group')
            
        return cleaned_data

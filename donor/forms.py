from django import forms
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from . import models


class DonorUserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'password']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'required': True, 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'required': True, 'placeholder': 'Last Name'}),
            'username': forms.TextInput(attrs={'class': 'form-control', 'required': True, 'placeholder': 'Username'})
        }

    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Password',
        'required': True
    }), validators=[
        RegexValidator(
            regex=r'^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{8,}$',
            message='Password must be at least 8 characters long and contain both letters and numbers'
        )
    ])
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Confirm Password',
        'required': True
    }))

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        username = cleaned_data.get('username')
        first_name = cleaned_data.get('first_name')
        last_name = cleaned_data.get('last_name')

        if not first_name:
            self.add_error('first_name', 'First name is required')
        elif not first_name.isalpha():
            self.add_error('first_name', 'First name should only contain letters')

        if not last_name:
            self.add_error('last_name', 'Last name is required')
        elif not last_name.isalpha():
            self.add_error('last_name', 'Last name should only contain letters')

        if username:
            if len(username) < 4:
                self.add_error('username', 'Username must be at least 4 characters long')
            if User.objects.filter(username=username).exists() and not User.objects.filter(username=username, id=self.instance.id).exists():
                self.add_error('username', 'Username already exists')
        else:
            self.add_error('username', 'Username is required')

        if not self.instance.pk:  # Only validate passwords for new users
            if password and confirm_password:
                if password != confirm_password:
                    self.add_error('confirm_password', 'Passwords do not match')
            else:
                if not password:
                    self.add_error('password', 'Password is required')
                if not confirm_password:
                    self.add_error('confirm_password', 'Please confirm your password')

        return cleaned_data

class DonorUserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'required': True, 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'required': True, 'placeholder': 'Last Name'}),
            'username': forms.TextInput(attrs={'class': 'form-control', 'required': True, 'placeholder': 'Username'})
        }

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        first_name = cleaned_data.get('first_name')
        last_name = cleaned_data.get('last_name')

        if not first_name:
            self.add_error('first_name', 'First name is required')
        elif not first_name.isalpha():
            self.add_error('first_name', 'First name should only contain letters')

        if not last_name:
            self.add_error('last_name', 'Last name is required')
        elif not last_name.isalpha():
            self.add_error('last_name', 'Last name should only contain letters')

        if username:
            if len(username) < 4:
                self.add_error('username', 'Username must be at least 4 characters long')
            if User.objects.filter(username=username).exists() and not User.objects.filter(username=username, id=self.instance.id).exists():
                self.add_error('username', 'Username already exists')
        else:
            self.add_error('username', 'Username is required')

        return cleaned_data

class DonorForm(forms.ModelForm):
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
        widget=forms.Select(attrs={
            'class': 'form-control',
            'required': True
        })
    )

    mobile = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+919876543210',
            'required': True
        }),
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message='Enter a valid phone number (e.g., +919876543210)'
            )
        ],
        help_text='Enter a valid phone number with country code'
    )

    address = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'required': True,
            'placeholder': 'Enter your complete address'
        }),
        help_text='Please provide your full address'
    )

    profile_pic = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control'
        }),
        help_text='Upload your profile picture (optional)'
    )

    class Meta:
        model = models.Donor
        fields = ['bloodgroup', 'address', 'mobile', 'profile_pic']

    def clean(self):
        cleaned_data = super().clean()
        
        # Validate bloodgroup
        bloodgroup = cleaned_data.get('bloodgroup')
        if not bloodgroup:
            self.add_error('bloodgroup', 'Please select a blood group')

        # Validate address
        address = cleaned_data.get('address')
        if not address:
            self.add_error('address', 'Address is required')
        elif len(address.strip()) < 10:
            self.add_error('address', 'Please provide a complete address (at least 10 characters)')

        # Validate mobile
        mobile = cleaned_data.get('mobile')
        if not mobile:
            self.add_error('mobile', 'Mobile number is required')

        return cleaned_data

class DonationForm(forms.ModelForm):
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
    
    age = forms.IntegerField(min_value=16, max_value=65)
    unit = forms.IntegerField(min_value=1, max_value=1000, 
                            help_text='Blood units in ml (1-1000)')
    disease = forms.CharField(required=False)
    bloodgroup = forms.ChoiceField(choices=BLOOD_GROUPS)
    
    class Meta:
        model = models.BloodDonate
        fields = ['age', 'bloodgroup', 'disease', 'unit']
        
    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('bloodgroup'):
            raise forms.ValidationError('Blood group is required')
        return cleaned_data

from django import forms
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from . import models

class AdminLoginForm(forms.Form):
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}),
        validators=[
            RegexValidator(
                regex=r'^[\w.@+-]+$',
                message='Enter a valid username. This value may contain only letters, numbers, and @/./+/-/_ characters.'
            )
        ]
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}),
        validators=[
            RegexValidator(
                regex=r'^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{8,}$',
                message='Password must be at least 8 characters long and contain both letters and numbers'
            )
        ]
    )

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')
        
        if not username:
            raise forms.ValidationError('Username is required')
        if not password:
            raise forms.ValidationError('Password is required')
            
        return cleaned_data

class BloodForm(forms.ModelForm):
    class Meta:
        model = models.Stock
        fields = ['bloodgroup', 'unit', 'cost_per_unit']
        widgets = {
            'bloodgroup': forms.Select(attrs={
                'class': 'form-control',
                'placeholder': 'Select Blood Group'
            }),
            'unit': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter number of units',
                'min': '0'
            }),
            'cost_per_unit': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter cost per unit',
                'min': '0',
                'step': '0.01'
            })
        }
        labels = {
            'bloodgroup': 'Blood Group',
            'unit': 'Number of Units',
            'cost_per_unit': 'Cost per Unit ($)'
        }
        help_texts = {
            'unit': 'Enter the total number of units available for this blood group',
            'cost_per_unit': 'Enter the cost per unit in dollars'
        }

    def clean_unit(self):
        unit = self.cleaned_data.get('unit')
        if unit < 0:
            raise forms.ValidationError("Number of units cannot be negative")
        return unit

    def clean_cost_per_unit(self):
        cost = self.cleaned_data.get('cost_per_unit')
        if cost < 0:
            raise forms.ValidationError("Cost per unit cannot be negative")
        return cost

class RequestForm(forms.ModelForm):
    patient_name = forms.CharField(
        validators=[
            RegexValidator(
                regex=r'^[A-Za-z\s]+$',
                message='Patient name must contain only alphabets and spaces.'
            )
        ]
    )
    
    reason = forms.CharField(
        validators=[
            RegexValidator(
                regex=r'^[A-Za-z\s.,]+$',
                message='Reason must contain only alphabets, spaces, periods, and commas.'
            )
        ]
    )
    
    class Meta:
        model = models.BloodRequest
        fields = ['patient_name', 'patient_age', 'reason', 'bloodgroup', 'unit']

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('patient_name'):
            raise forms.ValidationError('Patient name is required')
        if not cleaned_data.get('patient_age') or cleaned_data.get('patient_age') < 0:
            raise forms.ValidationError('Valid patient age is required')
        if not cleaned_data.get('bloodgroup'):
            raise forms.ValidationError('Blood group is required')
        if not cleaned_data.get('unit') or cleaned_data.get('unit') < 0:
            raise forms.ValidationError('Valid unit amount is required')
        if not cleaned_data.get('reason'):
            raise forms.ValidationError('Reason for blood request is required')
        return cleaned_data

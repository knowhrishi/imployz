from django import forms
from .models import JobListing, User

class JobListingForm(forms.ModelForm):
    class Meta:
        model = JobListing
        fields = ['title', 'description']

class UserForm(forms.ModelForm):
    job_listing = forms.ModelChoiceField(
        queryset=JobListing.objects.all(),
        label="Job Listing",
        required=True
    )
    class Meta:
        model = User
        fields = ['name', 'age', 'email', 'job_listing', 'resume']


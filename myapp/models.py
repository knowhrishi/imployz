# from django.contrib.auth.models import AbstractUser
# from django.db import models

# class User(AbstractUser):
#     USER_TYPE_CHOICES = (
#         ('CANDIDATE', 'Candidate'),
#         ('RECRUITER', 'Recruiter'),
#     )

#     user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES)
from django.db import models

class JobListing(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()

    def __str__(self):
        return self.title

class User(models.Model):
    name = models.CharField(max_length=255)
    age = models.PositiveIntegerField()
    email = models.EmailField()
    job_listing = models.ForeignKey(JobListing, on_delete=models.CASCADE)
    resume = models.FileField(upload_to='resumes/')

    def __str__(self):
        return self.name


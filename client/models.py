from django.db import models
from django.contrib.auth.models import User
from datetime import datetime
from cloudinary.models import CloudinaryField

# Create your models here.
class Profile(models.Model):
	phone_number = models.CharField(max_length=255, blank=True, null=True, db_index=True)
	profile_picture = CloudinaryField('image', folder='profile-pictures', blank=True, null=True)
	location = models.CharField(max_length=255, blank=True, null=True, db_index=True)
	timestamp = models.DateTimeField(default=datetime.now, db_index=True)
	last_modified = models.DateTimeField(default=datetime.now, db_index=True)
	verification_status = models.BooleanField(default=False, db_index=True)
	notification_status = models.BooleanField(default=False, db_index=True)
	user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile', db_index=True)

class Report(models.Model):
	location = models.CharField(max_length=225, blank=True, null=True)
	latitude = models.DecimalField(max_digits=9, decimal_places=6, db_index=True)
	longitude = models.DecimalField(max_digits=9, decimal_places=6, db_index=True)
	report_type = models.CharField(max_length=255, db_index=True) # e.g., traffic, noise, crowd level
	description = models.TextField(blank=True, null=True, db_index=True)
	timestamp = models.DateTimeField(default=datetime.now, db_index=True)
	status = models.CharField(max_length=255, db_index=True) # e.g., active, expired
	sensor_data = models.JSONField(default=dict, blank=True, null=True, db_index=True)
	verification_status = models.BooleanField(default=False, db_index=True)
	rating = models.FloatField(blank=True, null=True, db_index=True)
	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports', db_index=True)

class Prediction(models.Model):
	predicted_event = models.CharField(max_length=255, db_index=True)
	generated_text = models.TextField(db_index=True)
	confidence_score = models.FloatField(db_index=True) # 0-1 indicating AI confidence
	valid_until = models.DateTimeField(blank=True, null=True, db_index=True)
	ai_model_version = models.CharField(max_length=255, default='GPT-4', db_index=True)
	timestamp = models.DateTimeField(default=datetime.now, db_index=True)
	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='predictions', blank=True, null=True, db_index=True)
	report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='predictions', db_index=True)

class Feedback(models.Model):
	rating = models.IntegerField(null=True, blank=True, db_index=True)
	comment = models.TextField(null=True, blank=True, db_index=True)
	is_accurate = models.BooleanField(default=False, null=True, blank=True, db_index=True)
	timestamp = models.DateTimeField(default=datetime.now, db_index=True)
	parent_feedback = models.ForeignKey('self', on_delete=models.CASCADE, related_name='replies', blank=True, null=True, db_index=True)
	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='feedbacks', blank=True, null=True, db_index=True)
	prediction = models.ForeignKey(Prediction, on_delete=models.CASCADE, related_name='feedbacks', blank=True, null=True, db_index=True)
	report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='feedbacks', blank=True, null=True, db_index=True)

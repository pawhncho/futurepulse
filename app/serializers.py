from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Profile, Report, Prediction, Feedback

# Create your serializers here.
class UserSerializer(serializers.ModelSerializer):
	class Meta:
		model = User
		fields = ['username', 'first_name', 'last_name']

class ProfileSerializer(serializers.ModelSerializer):
	user = UserSerializer(read_only=True)
	class Meta:
		model = Profile
		fields = '__all__'

class ReportSerializer(serializers.ModelSerializer):
	class Meta:
		model = Report
		fields = '__all__'

class PredictionSerializer(serializers.ModelSerializer):
	class Meta:
		model = Prediction
		fields = '__all__'

class FeedbackSerializer(serializers.ModelSerializer):
	class Meta:
		model = Feedback
		fields = '__all__'

from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Profile, Report, Prediction, Feedback

# Create your serializers here.
class UserSerializer(serializers.ModelSerializer):
	class Meta:
		model = User
		fields = ['username', 'first_name', 'last_name', 'email']

class ProfileSerializer(serializers.ModelSerializer):
	user = UserSerializer(read_only=True)
	profile_picture = serializers.SerializerMethodField()

	def get_profile_picture(self, obj):
		if obj.profile_picture:
			return obj.profile_picture.url
		return None
		
	class Meta:
		model = Profile
		fields = ['user', 'phone_number', 'profile_picture', 'location', 'timestamp', 'last_modified', 'verification_status', 'notification_status']

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

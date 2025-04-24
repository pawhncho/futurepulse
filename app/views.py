from django.shortcuts import render
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core import signing
from django.core.mail import send_mail
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from datetime import datetime
from django.conf import settings
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import openai
from .models import Profile, Report, Prediction, Feedback
from .serializers import UserSerializer, ProfileSerializer, ReportSerializer, PredictionSerializer, FeedbackSerializer

# Create your views here.
@api_view(['GET', 'POST'])
def login(request):
	if request.method == 'POST':
		username = request.data.get('username')
		password = request.data.get('password')
		user = authenticate(username=username, password=password)
		if user:
			token = Token.objects.filter(user=user).first()
			if token:
				return Response({ 'data': token.key, 'status': 200 }, status=200)
			else:
				return Response({ 'data': 'Invalid credentials', 'status': 401 }, status=401)
		else:
			return Response({ 'data': 'Invalid credentials', 'status': 401 }, status=401)
	return Response({ 'data': 'Login API - Fields are required', 'status': 400 }, status=400)

@api_view(['GET', 'POST'])
def register(request):
	if request.method == 'POST':
		username = request.data.get('username')
		email = request.data.get('email')
		password = request.data.get('password')
		if User.objects.filter(username=username).exists():
			return Response({ 'data': 'Username already exists', 'status': 400 }, status=400)
		if User.objects.filter(email=email).exists():
			return Response({ 'data': 'Email already exists', 'status': 400 }, status=400)
		user = User.objects.create_user(username=username, email=email, password=password)
		profile = Profile(user=user)
		profile.save()
		token = Token(user=user)
		token.save()
		return Response({ 'data': token.key, 'status': 201 }, status=201)
	return Response({ 'data': 'Register API - Fields are required', 'status': 400 }, status=400)

@api_view(['GET', 'POST'])
def forgot_password(request):
	if request.method == 'POST':
		email = request.data.get('email')
		if not User.objects.filter(email=email).exists():
			return Response({ 'data': 'User not found', 'status': 404 }, status=404)
		user = User.objects.filter(email=email).first()
		token = signing.dumps({ 'identification': user.id })
		send_mail(
			'Reset Password',
			f'Reset your password: {request.get_host()}/reset-password/{token}/',
			'Future Pulse',
			[user.email],
		)
		return Response({ 'data': 'Email has been sent', 'status': 200 }, status=200)
	return Response({ 'data': 'Forgot Password API - Fields are required', 'status': 400 }, status=400)

@api_view(['GET', 'POST'])
def reset_password(request, token):
	if request.method == 'POST':
		new_password = request.data.get("new-password")
		if not new_password:
			return Response({ 'data': 'Fields are required', 'status': 400 }, status=400)
		try:
			token = signing.loads(token, max_age=3600)
		except:
			return Response({ 'data': 'Invalid token', 'status': 400 }, status=400)
		if not User.objects.filter(id=token['identification']).exists():
			return Response({ 'data': 'User not found', 'status': 400 }, status=400)
		user = User.objects.filter(id=token['identification']).first()
		user.set_password(new_password)
		user.save()
		return Response({ 'data': 'Password has been changed', 'status': 200 }, status=200)
	return Response({ 'data': 'Reset Password API - Fields are required', 'status': 400 }, status=400)

@api_view(['GET'])
def send_verification_email(request):
	token = request.GET.get('token')
	if not token:
		return Response({ 'data': 'Invalid token', 'status': 400 }, status=400)
	try:
		token = Token.objects.filter(key=token).first()
		user = token.user
		token = signing.dumps({ 'identification': user.id })
		send_mail(
			'Email Verification',
			f'Verify your email address: {request.get_host()}/api/verify-email/{token}/',
			'Future Pulse',
			[user.email],
		)
		return Response({ 'data': 'Email has been sent', 'status': 200 }, status=200)
	except:
		return Response({ 'data': 'Invalid token', 'status': 400 }, status=400)

@api_view(['GET'])
def verify_email(request, token):
	try:
		token = signing.loads(token, max_age=3600)
	except:
		return Response({ 'data': 'Invalid token', 'status': 400 }, status=400)
	if not User.objects.filter(id=token['identification']).exists():
		return Response({ 'data': 'User not found', 'status': 400 }, status=400)
	user = User.objects.filter(id=token['identification']).first()
	profile = Profile.objects.filter(user=user).first()
	profile.verification_status = True
	profile.save()
	return Response({ 'data': 'Email has been verified', 'status': 200 }, status=200)

@api_view(['GET'])
def profile(request):
	token = request.GET.get('token')
	if not token:
		return Response({ 'data': 'Invalid token', 'status': 400 }, status=400)
	try:
		token = Token.objects.filter(key=token).first()
		user = token.user
	except:
		return Response({ 'data': 'Invalid token', 'status': 400 }, status=400)
	profile = Profile.objects.filter(user=user).first()
	profile_serializer = ProfileSerializer(profile, read_only=True)
	return Response({ 'data': profile_serializer.data, 'status': 200 }, status=200)

@api_view(['GET'])
def turn_on_notifications(request):
	token = request.GET.get('token')
	if not token:
		return Response({ 'data': 'Invalid token', 'status': 400 }, status=400)
	try:
		token = Token.objects.filter(key=token).first()
		user = token.user
	except:
		return Response({ 'data': 'Invalid token', 'status': 400 }, status=400)
	profile = Profile.objects.filter(user=user).first()
	profile.notification_status = True
	profile.save()
	return Response({ 'data': 'Notifications are on', 'status': 200 }, status=200)

@api_view(['GET'])
def turn_off_notifications(request):
	token = request.GET.get('token')
	if not token:
		return Response({ 'data': 'Invalid token', 'status': 400 }, status=400)
	try:
		token = Token.objects.filter(key=token).first()
		user = token.user
	except:
		return Response({ 'data': 'Invalid token', 'status': 400 }, status=400)
	profile = Profile.objects.filter(user=user).first()
	profile.notification_status = False
	profile.save()
	return Response({ 'data': 'Notifications are off', 'status': 200 }, status=200)

@api_view(['GET', 'POST'])
def update_profile(request):
	token = request.GET.get('token')
	if not token:
		return Response({ 'data': 'Invalid token', 'status': 400 }, status=400)
	try:
		token = Token.objects.filter(key=token).first()
		user = token.user
	except:
		return Response({ 'data': 'Invalid token', 'status': 400 }, status=400)
	profile = Profile.objects.filter(user=user).first()
	if request.method == 'POST':
		if request.data.get('first_name'):
			user.first_name = request.data.get('first_name')
		if request.data.get('last_name'):
			user.last_name = request.data.get('last_name')
		if request.data.get('username'):
			user.username = request.data.get('username')
		if request.data.get('profile-picture'):
			profile.profile_picture = request.FILES.get('profile-picture')
		if request.data.get('phone-number'):
			profile.phone_number = request.data.get('phone-number')
		if request.data.get('location'):
			profile.location = request.data.get('location')
		profile.last_modified = datetime.now()
		user.save()
		profile.save()
		return Response({ 'data': 'Profile has been updated', 'status': 200 }, status=200)
	return Response({ 'data': 'Profile Update API - Fields are required', 'status': 400 }, status=400)

@api_view(['GET', 'POST'])
def submit_report(request):
	token = request.GET.get('token')
	if not token:
		return Response({ 'data': 'Invalid token', 'status': 400 }, status=400)
	try:
		token = Token.objects.filter(key=token).first()
		user = token.user
	except:
		return Response({ 'data': 'Invalid token', 'status': 400 }, status=400)
	if request.method == 'POST':
		latitude = request.data.get('latitude')
		longitude = request.data.get('longitude')
		report_type = request.data.get('report_type')
		description = request.data.get('description')
		sensor_data = request.data.get('sensor_data')
		rating = request.data.get('rating')
		Report.objects.create(latitude=latitude, longitude=longitude, report_type=report_type, description=description,
								sensor_data=sensor_data, status='pending', verification_status=False,
								rating=rating, user=user)
		return Response({ 'data': 'Report has been submitted', 'status': 200 }, status=200)
	return Response({ 'data': 'Report Submission API - Fields are required', 'status': 400 }, status=400)

@api_view(['GET'])
def reports(request):
	token = request.GET.get('token')
	if not token:
		return Response({ 'data': 'Invalid token', 'status': 400 }, status=400)
	try:
		token = Token.objects.filter(key=token).first()
	except:
		return Response({ 'data': 'Invalid token', 'status': 400 }, status=400)
	reports = Report.objects.all()[::-1]
	reports_serializer = ReportSerializer(reports, read_only=True, many=True)
	return Response({ 'data': reports_serializer.data, 'status': 200 }, status=200)

@api_view(['GET', 'POST'])
def submit_prediction(request):
	token = request.GET.get('token')
	report = request.GET.get('report')
	if not token:
		return Response({ 'data': 'Invalid token', 'status': 400 }, status=400)
	try:
		token = Token.objects.filter(key=token).first()
		user = token.user
	except:
		return Response({ 'data': 'User not found', 'status': 400 }, status=400)
	if not report:
		return Response({ 'data': 'Invalid report', 'status': 400 }, status=400)
	try:
		report = Report.objects.filter(id=report).first()
	except:
		return Response({ 'data': 'Report not found', 'status': 400 }, status=400)
	if request.method == 'POST':
		predicted_event = request.data.get('predicted_event')
		generated_text = request.data.get('generated_text')
		confidence_score = request.data.get('confidence_score')
		valid_until = request.data.get('valid_until')
		ai_model_version = request.data.get('ai_model_version')
		prediction = Prediction.objects.create(predicted_event=predicted_event, generated_text=generated_text,
									confidence_score=confidence_score, valid_until=valid_until if valid_until else None,
										ai_model_version=ai_model_version, user=user, report=report)
		prediction_serializer = PredictionSerializer(prediction, read_only=True)
		channel_layer = get_channel_layer()
		async_to_sync(channel_layer.group_send)(
			'notifications',
			{'type': 'send_notification', 'message': prediction_serializer.data}
		)
		return Response({ 'data': 'Prediction has been submitted', 'status': 200 }, status=200)
	return Response({ 'data': 'Prediction Submission API - Fields are required', 'status': 400 }, status=400)

@api_view(['GET'])
def predictions(request):
	token = request.GET.get('token')
	if not token:
		return Response({ 'data': 'Invalid token', 'status': 400 }, status=400)
	try:
		token = Token.objects.filter(key=token).first()
	except:
		return Response({ 'data': 'Invalid token', 'status': 400 }, status=400)
	predictions = Prediction.objects.all()[::-1]
	predictions_serializer = PredictionSerializer(predictions, read_only=True, many=True)
	return Response({ 'data': predictions_serializer.data, 'status': 200 }, status=200)
	
@api_view(['GET', 'POST'])
def submit_feedback(request):
	token = request.GET.get('token')
	prediction = request.GET.get('prediction')
	if not token:
		return Response({ 'data': 'Invalid token', 'status': 400 }, status=400)
	try:
		token = Token.objects.filter(key=token).first()
		user = token.user
	except:
		return Response({ 'data': 'Invalid token', 'status': 400 }, status=400)
	if request.method == 'POST':
		rating = request.data.get('rating')
		comment = request.data.get('comment')
		is_accurate = request.data.get('is_accurate')
		Feedback.objects.create(rating=rating, comment=comment, is_accurate=is_accurate, prediction=prediction)
		return Response({ 'data': 'Feedback has been submitted', 'status': 200 }, status=200)
	return Response({ 'data': 'Feedback Submission API - Fields are required', 'status': 400 }, status=400)

@api_view(['GET'])
def feedbacks(request):
	prediction = request.GET.get('prediction')
	if not prediction:
		return Response({ 'data': 'Invalid parameters', 'status': 400 }, status=400)
	try:
		prediction = Prediction.objects.filter(id=prediction).first()
		feedbacks = prediction.feedbacks
	except:
		return Response({ 'data': 'Prediction not found', 'status': 400 }, status=400)
	feedbacks_serializer = FeedbackSerializer(feedbacks, read_only=True, many=True)
	return Response({ 'data': feedbacks_serializer.data, 'status': 200 }, status=200)

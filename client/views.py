from django.shortcuts import render
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core import signing
from django.core.mail import send_mail
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.throttling import AnonRateThrottle
from rest_framework.exceptions import ValidationError
from rest_framework import status
from datetime import datetime
from django.conf import settings
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from PIL import Image
import io
import re
from .models import Profile, Report, Prediction, Feedback
from .serializers import UserSerializer, ProfileSerializer, ReportSerializer, PredictionSerializer, FeedbackSerializer

# Custom throttle classes
class AuthRateThrottle(AnonRateThrottle):
    rate = '5/min'

# Utility functions for validation
def validate_password(password):
    if len(password) < 8:
        raise ValidationError('Password must be at least 8 characters long')
    if not re.search(r'[A-Z]', password):
        raise ValidationError('Password must contain at least one uppercase letter')
    if not re.search(r'[a-z]', password):
        raise ValidationError('Password must contain at least one lowercase letter')
    if not re.search(r'\d', password):
        raise ValidationError('Password must contain at least one number')

def validate_email(email):
    if not re.match(r'[^@]+@[^@]+\.[^@]+', email):
        raise ValidationError('Invalid email format')

# def validate_image(image):
#     if image.size > 5 * 1024 * 1024:  # 5MB limit
#         raise ValidationError('Image size should not exceed 5MB')
#     try:
#         img = Image.open(image)
#         if img.format.upper() not in ['JPEG', 'PNG']:
#             raise ValidationError('Only JPEG and PNG images are allowed')
#         return img
#     except Exception as e:
#         raise ValidationError('Invalid image format')

# def optimize_image(image, max_size=(800, 800)):
#     img = Image.open(image)
#     img.thumbnail(max_size, Image.LANCZOS)
#     output = io.BytesIO()
#     img.save(output, format='JPEG', quality=85, optimize=True)
#     output.seek(0)
#     return output

def error_response(message, status_code):
    return Response({
        'status': 'error',
        'code': status_code,
        'data': str(message),
        'timestamp': datetime.now().isoformat()
    }, status=status_code)

def success_response(data, status_code=status.HTTP_200_OK):
    return Response({
        'status': 'success',
        'code': status_code,
        'data': data,
        'timestamp': datetime.now().isoformat()
    }, status=status_code)

# Create your views here.
@api_view(['POST'])
@throttle_classes([AuthRateThrottle])
def login(request):
    try:
        username = request.data.get('username')
        password = request.data.get('password')
        if not username or not password:
            return error_response('Username and password are required', status.HTTP_400_BAD_REQUEST)
        user = authenticate(username=username, password=password)
        if user:
            token = Token.objects.filter(user=user).first()
            if token:
                return success_response({'token': token.key})
            else:
                return error_response('Token generation failed', status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return error_response('Invalid credentials', status.HTTP_401_UNAUTHORIZED)
    except Exception as e:
        return error_response('An unexpected error occurred', status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET', 'POST'])
@throttle_classes([AuthRateThrottle])
def register(request):
    if request.method == 'POST':
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')
        try:
            validate_password(password)
            validate_email(email)
        except ValidationError as e:
            return error_response(e.detail, status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(username=username).exists():
            return error_response('Username already exists', status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(email=email).exists():
            return error_response('Email already exists', status.HTTP_400_BAD_REQUEST)
        user = User.objects.create_user(username=username, email=email, password=password)
        profile = Profile(user=user)
        profile.save()
        token = Token(user=user)
        token.save()
        return success_response({'token': token.key}, status.HTTP_201_CREATED)
    return error_response('Register API - Fields are required', status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'POST'])
def forgot_password(request):
    if request.method == 'POST':
        email = request.data.get('email')
        try:
            validate_email(email)
        except ValidationError as e:
            return error_response(e.detail, status.HTTP_400_BAD_REQUEST)
        if not User.objects.filter(email=email).exists():
            return error_response('User not found', status.HTTP_404_NOT_FOUND)
        user = User.objects.filter(email=email).first()
        token = signing.dumps({ 'identification': user.id })
        send_mail(
            'Reset Password',
            f'Reset your password: {request.get_host()}/reset-password/{token}/',
            'Future Pulse',
            [user.email],
        )
        return success_response('Email has been sent')
    return error_response('Forgot Password API - Fields are required', status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'POST'])
def reset_password(request, token):
    if request.method == 'POST':
        new_password = request.data.get('new-password')
        try:
            validate_password(new_password)
        except ValidationError as e:
            return error_response(e.detail, status.HTTP_400_BAD_REQUEST)
        try:
            token = signing.loads(token, max_age=3600)
        except:
            return error_response('Invalid token', status.HTTP_400_BAD_REQUEST)
        if not User.objects.filter(id=token['identification']).exists():
            return error_response('User not found', status.HTTP_400_BAD_REQUEST)
        user = User.objects.filter(id=token['identification']).first()
        user.set_password(new_password)
        user.save()
        return success_response('Password has been changed')
    return error_response('Reset Password API - Fields are required', status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def send_verification_email(request):
    token = request.GET.get('token')
    if not token:
        return error_response('Invalid token', status.HTTP_400_BAD_REQUEST)
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
        return success_response('Email has been sent')
    except:
        return error_response('Invalid token', status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def verify_email(request, token):
    try:
        token = signing.loads(token, max_age=3600)
    except:
        return error_response('Invalid token', status.HTTP_400_BAD_REQUEST)
    if not User.objects.filter(id=token['identification']).exists():
        return error_response('User not found', status.HTTP_400_BAD_REQUEST)
    user = User.objects.filter(id=token['identification']).first()
    profile = Profile.objects.filter(user=user).first()
    profile.verification_status = True
    profile.save()
    return success_response('Email has been verified')

@api_view(['GET'])
def profile(request):
    token = request.GET.get('token')
    if not token:
        return error_response('Invalid token', status.HTTP_400_BAD_REQUEST)
    try:
        token = Token.objects.filter(key=token).first()
        user = token.user
    except:
        return error_response('Invalid token', status.HTTP_400_BAD_REQUEST)
    profile = Profile.objects.filter(user=user).first()
    profile_serializer = ProfileSerializer(profile, read_only=True)
    return success_response(profile_serializer.data)

@api_view(['GET'])
def turn_on_notifications(request):
    token = request.GET.get('token')
    if not token:
        return error_response('Invalid token', status.HTTP_400_BAD_REQUEST)
    try:
        token = Token.objects.filter(key=token).first()
        user = token.user
    except:
        return error_response('Invalid token', status.HTTP_400_BAD_REQUEST)
    profile = Profile.objects.filter(user=user).first()
    profile.notification_status = True
    profile.save()
    return success_response('Notifications are on')

@api_view(['GET'])
def turn_off_notifications(request):
    token = request.GET.get('token')
    if not token:
        return error_response('Invalid token', status.HTTP_400_BAD_REQUEST)
    try:
        token = Token.objects.filter(key=token).first()
        user = token.user
    except:
        return error_response('Invalid token', status.HTTP_400_BAD_REQUEST)
    profile = Profile.objects.filter(user=user).first()
    profile.notification_status = False
    profile.save()
    return success_response('Notifications are off')

@api_view(['GET', 'POST'])
def update_profile(request):
    token = request.GET.get('token')
    if not token:
        return error_response('Invalid token', status.HTTP_400_BAD_REQUEST)
    try:
        token = Token.objects.filter(key=token).first()
        user = token.user
    except:
        return error_response('Invalid token', status.HTTP_400_BAD_REQUEST)
    profile = Profile.objects.filter(user=user).first()
    if request.method == 'POST':
        if request.data.get('first-name'):
            user.first_name = request.data.get('first-name')
        if request.data.get('last-name'):
            user.last_name = request.data.get('last-name')
        if request.data.get('email'):
            if User.objects.filter(email=request.data.get('email')).exists():
                return error_response('Email already exists', status.HTTP_400_BAD_REQUEST)
            else:
                try:
                    validate_email(request.data.get('email'))
                    user.email = request.data.get('email')
                except ValidationError as e:
                    return error_response(e.detail, status.HTTP_400_BAD_REQUEST)
        if request.data.get('username'):
            if User.objects.filter(username=request.data.get('username')).exists():
                return error_response('Username already exists', status.HTTP_400_BAD_REQUEST)
            else:
                user.username = request.data.get('username')
        if request.data.get('profile-picture'):
            try:
                # image = validate_image(request.FILES.get('profile-picture'))
                # image = optimize_image(image)
                profile.profile_picture = request.FILES.get('profile-picture')
            except ValidationError as e:
                return error_response(e.detail, status.HTTP_400_BAD_REQUEST)
        if request.data.get('phone-number'):
            profile.phone_number = request.data.get('phone-number')
        if request.data.get('location'):
            profile.location = request.data.get('location')
        profile.last_modified = datetime.now()
        user.save()
        profile.save()
        return success_response('Profile has been updated')
    return error_response('Profile Update API - Fields are required', status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'POST'])
def submit_report(request):
    token = request.GET.get('token')
    if not token:
        return error_response('Invalid token', status.HTTP_400_BAD_REQUEST)
    try:
        token = Token.objects.filter(key=token).first()
        user = token.user
    except:
        return error_response('Invalid token', status.HTTP_400_BAD_REQUEST)
    if request.method == 'POST':
        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')
        report_type = request.data.get('report_type')
        description = request.data.get('description')
        sensor_data = request.data.get('sensor_data')
        rating = request.data.get('rating')
        Report.objects.create(
            latitude=latitude,
            longitude=longitude,
            report_type=report_type,
            description=description,
            sensor_data=sensor_data,
            status='pending',
            verification_status=False,
            rating=rating, user=user)
        return success_response('Report has been submitted')
    return error_response('Report Submission API - Fields are required', status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def reports(request):
    token = request.GET.get('token')
    if not token:
        return error_response('Invalid token', status.HTTP_400_BAD_REQUEST)
    try:
        token = Token.objects.filter(key=token).first()
    except:
        return error_response('Invalid token', status.HTTP_400_BAD_REQUEST)
    reports = Report.objects.all()[::-1]
    reports_serializer = ReportSerializer(reports, read_only=True, many=True)
    return success_response(reports_serializer.data)

@api_view(['GET', 'POST'])
def submit_prediction(request):
    token = request.GET.get('token')
    report = request.GET.get('report')
    if not token:
        return error_response('Invalid token', status.HTTP_400_BAD_REQUEST)
    try:
        token = Token.objects.filter(key=token).first()
        user = token.user
    except:
        return error_response('Invalid token', status.HTTP_400_BAD_REQUEST)
    if not report:
        return error_response('Invalid report', status.HTTP_400_BAD_REQUEST)
    try:
        report = Report.objects.filter(id=report).first()
    except:
        return error_response('Report not found', status.HTTP_400_BAD_REQUEST)
    if request.method == 'POST':
        predicted_event = request.data.get('predicted_event')
        generated_text = request.data.get('generated_text')
        confidence_score = request.data.get('confidence_score')
        valid_until = request.data.get('valid_until')
        ai_model_version = request.data.get('ai_model_version')
        prediction = Prediction.objects.create(
            predicted_event=predicted_event,
            generated_text=generated_text,
            confidence_score=confidence_score,
            valid_until=valid_until if valid_until else None,
            ai_model_version=ai_model_version,
            user=user,
            report=report)
        prediction_serializer = PredictionSerializer(prediction, read_only=True)
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            'notifications',
            {'type': 'send_notification', 'message': prediction_serializer.data}
        )
        return success_response('Prediction has been submitted')
    return error_response('Prediction Submission API - Fields are required', status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def predictions(request):
    token = request.GET.get('token')
    if not token:
        return error_response('Invalid token', status.HTTP_400_BAD_REQUEST)
    try:
        token = Token.objects.filter(key=token).first()
    except:
        return error_response('Invalid token', status.HTTP_400_BAD_REQUEST)
    predictions = Prediction.objects.all()[::-1]
    predictions_serializer = PredictionSerializer(predictions, read_only=True, many=True)
    return success_response(predictions_serializer.data)

@api_view(['GET', 'POST'])
def submit_feedback(request):
    token = request.GET.get('token')
    prediction = request.GET.get('prediction')
    if not token:
        return error_response('Invalid token', status.HTTP_400_BAD_REQUEST)
    try:
        token = Token.objects.filter(key=token).first()
        user = token.user
    except:
        return error_response('Invalid token', status.HTTP_400_BAD_REQUEST)
    if request.method == 'POST':
        rating = request.data.get('rating')
        comment = request.data.get('comment')
        is_accurate = request.data.get('is_accurate')
        Feedback.objects.create(rating=rating, comment=comment, is_accurate=is_accurate, prediction=prediction)
        return success_response('Feedback has been submitted')
    return error_response('Feedback Submission API - Fields are required', status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def feedbacks(request):
    prediction = request.GET.get('prediction')
    if not prediction:
        return error_response('Invalid parameters', status.HTTP_400_BAD_REQUEST)
    try:
        prediction = Prediction.objects.filter(id=prediction).first()
        feedbacks = prediction.feedbacks
    except:
        return error_response('Prediction not found', status.HTTP_400_BAD_REQUEST)
    feedbacks_serializer = FeedbackSerializer(feedbacks, read_only=True, many=True)
    return success_response(feedbacks_serializer.data)

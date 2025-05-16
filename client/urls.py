from django.urls import path
from . import views

# Create your urls here.
urlpatterns = [
	path('login/', views.login),
	path('register/', views.register),
	path('forgot-password/', views.forgot_password),
	path('reset-password/', views.reset_password_page),
	path('reset-password/<token>/', views.reset_password),
	path('send-verification-email/', views.send_verification_email),
	path('verify-email/<token>/', views.verify_email),
	path('profile/', views.profile),
	path('turn-on-notifications/', views.turn_on_notifications),
	path('turn-off-notifications/', views.turn_off_notifications),
	path('update-profile/', views.update_profile),
	path('submit-report/', views.submit_report),
	path('reports/', views.reports),
	path('submit-prediction/', views.submit_prediction),
	path('predictions/', views.predictions),
	path('submit-feedback/', views.submit_feedback),
	path('feedbacks/', views.feedbacks),
]

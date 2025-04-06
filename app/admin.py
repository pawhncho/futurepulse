from django.contrib import admin
from .models import Profile, Report, Prediction, Feedback

# Register your models here.
admin.site.register(Profile)
admin.site.register(Report)
admin.site.register(Prediction)
admin.site.register(Feedback)

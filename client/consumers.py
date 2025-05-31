import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'futurepulse.settings')
django.setup()

import json
from channels.generic.websocket import WebsocketConsumer
from channels.generic.websocket import AsyncWebsocketConsumer
from datetime import datetime
from .models import Prediction, Report
from .serializers import ReportSerializer, PredictionSerializer, FeedbackSerializer

# Create your consumers here.
class ReportConsumer(WebsocketConsumer):
	def connect(self):
		self.accept()

	def disconnect(self, close_code):
		pass

	def receive(self, text_data):
		reports = Report.objects.all().order_by('-timestamp')
		reports_serializer = ReportSerializer(reports, read_only=True, many=True)
		self.send(text_data=reports_serializer.data)

class PredictionConsumer(WebsocketConsumer):
	def connect(self):
		self.accept()

	def disconnect(self, close_code):
		pass

	def receive(self, text_data):
		predictions = Prediction.objects.filter(valid_until__gte=datetime.now()).order_by('-timestamp')
		data = []
		for prediction in predictions:
			data.append({
				'predicted_event': prediction.predicted_event,
				'generated_text': prediction.generated_text,
				'confidence_score': prediction.confidence_score,
				'valid_until': prediction.valid_until.strftime("%Y-%m-%dT%H:%M:%SZ"),
				'ai_model_version': prediction.ai_model_version,
			})
		self.send(text_data=json.dumps(data))

class NotificationConsumer(AsyncWebsocketConsumer):
	async def connect(self):
		self.group_name = 'notifications'
		await self.channel_layer.group_add(self.group_name, self.channel_name)
		await self.accept()

	async def disconnect(self, close_code):
		await self.channel_layer.group_discard(self.group_name, self.channel_name)

	async def send_notification(self, event):
		message = event['message']
		await self.send(text_data=json.dumps({ 'notification': message }))

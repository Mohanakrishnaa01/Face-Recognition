from django.urls import path
from . import views

urlpatterns = [
    path('upload/', views.handle_upload, name='handle_upload'),
] 
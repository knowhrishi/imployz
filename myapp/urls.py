from django.urls import path
from . import views

app_name = 'myapp'

urlpatterns = [
    path('', views.index, name="index"),
    path('user/<str:user_id>/', views.user_detail, name='user_detail'),
    
]

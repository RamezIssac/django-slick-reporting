from django.urls import path
from . import views
urlpatterns = [
    path('report1/', views.MonthlyProductSales.as_view(), name='report1'),
]


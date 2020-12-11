from django.urls import path
from . import views
urlpatterns = [
    path('report1/', views.MonthlyProductSales.as_view(), name='report1'),
    path('product_crosstab_client/', views.ProductClientSalesMatrix.as_view(), name='product_crosstab_client'),
    path('crosstab-columns-on-fly/', views.CrossTabColumnOnFly.as_view(), name='crosstab-columns-on-fly'),
]


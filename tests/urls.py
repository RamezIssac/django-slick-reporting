from django.urls import path
from . import views

urlpatterns = [
    path('report1/', views.MonthlyProductSales.as_view(), name='report1'),
    path('report-to-field-set/', views.MonthlyProductSalesToFIeldSet.as_view(), name='report-to-field-set'),
    path('product_crosstab_client/', views.ProductClientSalesMatrix.as_view(), name='product_crosstab_client'),
    path('product_crosstab_client-to_field-set/', views.ProductClientSalesMatrixToFIeldSet.as_view(),
         name='product_crosstab_client_to_field_set'),
    path('crosstab-columns-on-fly/', views.CrossTabColumnOnFly.as_view(), name='crosstab-columns-on-fly'),
    path('crosstab-columns-on-fly-to-field-set/', views.CrossTabColumnOnFlyToFieldSet.as_view(),
         name='crosstab-columns-on-fly-to-field-set'),
    path('queryset-only/', views.MonthlyProductSalesWQS.as_view(), name='queryset-only'),
]

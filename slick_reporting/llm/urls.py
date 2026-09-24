from django.urls import path

from .views import AskLLMView

app_name = "slick_reporting_llm"

urlpatterns = [
    path("ask/", AskLLMView.as_view(), name="ask"),
]

from django.urls import path

from heatmaps import views

urlpatterns = [
    path("", views.index, name="index"),
]

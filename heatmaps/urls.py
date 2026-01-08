from django.urls import path

from heatmaps import views

urlpatterns = [
    path("", views.index, name="index"),
    path("api/scenarios/", views.ScenarioListCreateView.as_view(), name="scenario-create"),
    path(
        "api/scenarios/<int:scenario_id>/",
        views.ScenarioDetailView.as_view(),
        name="scenario-detail",
    ),
    path(
        "api/scenarios/<int:scenario_id>/run/",
        views.ScenarioRunView.as_view(),
        name="scenario-run",
    ),
    path(
        "api/scenarios/<int:scenario_id>/results/",
        views.ScenarioResultsView.as_view(),
        name="scenario-results",
    ),
]

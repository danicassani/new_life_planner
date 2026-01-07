from django.shortcuts import render


def index(request):
    return render(request, "heatmaps/index.html")

# Create your views here.

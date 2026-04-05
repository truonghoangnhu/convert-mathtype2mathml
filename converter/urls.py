from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard_view, name="dashboard"),
    path("register/", views.register_view, name="register"),
    path("upload/", views.upload_view, name="upload"),
    path("batch-upload/", views.batch_upload_view, name="batch_upload"),
    path("history/", views.history_view, name="history"),
    path("conversion/<uuid:pk>/", views.conversion_detail_view, name="conversion_detail"),
    path("conversion/<uuid:pk>/download/", views.download_view, name="download"),
]

from django.urls import path
from . import views

urlpatterns = [
    path('', views.search_view, name='search'),
    path('results/', views.search_results_view, name='search_results'),
    path('download/', views.download_csv, name='download_csv'),
    path('upload/', views.upload_csv_view, name='upload_csv'),
    path('process/', views.process_urls_view, name='process_urls'),
    path('contacts/', views.contact_results_view, name='contact_results'),
    path('download-contacts/', views.download_contact_csv, name='download_contact_csv'),
]

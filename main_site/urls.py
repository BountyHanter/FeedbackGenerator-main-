from django.urls import path, include

from FeedbackGenerator.get_csrf import get_csrf_token
from main_site.views.DGis.dgis_api.dgis_api_profile import trigger_2gis_stats_collection, sync_2gis_profile
from main_site.views.DGis.dgis_api.dgis_api_reviews import toggle_dgis_favorite, toggle_dgis_complaint, \
    toggle_dgis_reply_review
from main_site.views.DGis.dgis_profiles import list_2gis_profiles, render_2gis_profiles_selection, create_2gis_profile, \
    update_or_create_2gis_profile
from main_site.views.DGis.dgis_reviews import render_2gis_reviews_page, proxy_dgis_get_reviews, proxy_dgis_fetch_stats

# Внутренние маршруты (работают с БД и логикой внутри микросервиса)
internal_patterns = [
    path('csrf/', get_csrf_token, name='get_csrf'),
    path('2gis_accounts/', list_2gis_profiles, name='list_2gis_accounts'),
    path('2gis_reviews/', render_2gis_profiles_selection, name='2gis_accounts_list'),
    path('2gis_reviews/<int:profile_id>/', render_2gis_reviews_page, name='2gis_reviews'),
    path('create_2gis_profile/', create_2gis_profile, name='create_2gis_profile'),
    path('update_2gis_profile/<int:profile_id>/', sync_2gis_profile, name='update_2gis_profile'),
    path('link_2gis_profile/<int:profile_id>/', update_or_create_2gis_profile, name='update_or_create_2gis_profile'),
]

# Внешние маршруты (Django проксирует запросы к другим микросервисам)
external_patterns = [
    path('proxy_dgis_get_reviews/', proxy_dgis_get_reviews, name='proxy_dgis_get_reviews'),
    path('proxy_dgis_get_stats/', proxy_dgis_fetch_stats, name='proxy_dgis_get_stats'),
    path('favorite_dgis/<int:review_id>/', toggle_dgis_favorite, name='toggle_dgis_favorite'),
    path('proxy_dgis_complaint/<int:review_id>/', toggle_dgis_complaint, name='toggle_dgis_complaint'),
    path('proxy_dgis_reply_review/<int:review_id>/', toggle_dgis_reply_review, name='proxy_dgis_reply_review'),
    path('start_stats_collection_dgis/', trigger_2gis_stats_collection, name='start_stats_collection_dgis'),
]

# Основные маршруты
urlpatterns = [
    path('api/internal/', include(internal_patterns)),  # Внутренние (работают с БД и скриптами)
    path('api/external/', include(external_patterns)),  # Внешние (проксируют запросы)
]

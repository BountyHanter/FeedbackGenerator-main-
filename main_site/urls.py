from django.urls import path, include

from FeedbackGenerator.get_csrf import get_csrf_token
from main_site.views.DGis.dgis_api.dgis_api_profile import trigger_2gis_stats_collection, update_2gis_profile
from main_site.views.DGis.dgis_api.dgis_api_reviews import toggle_dgis_favorite, toggle_dgis_complaint, \
    toggle_dgis_reply_review
from main_site.views.DGis.dgis_profiles import list_2gis_profiles, create_2gis_profile, link_2gis_profile
from main_site.views.DGis.dgis_reviews import get_2gis_filials, proxy_dgis_get_reviews, proxy_dgis_fetch_stats

# Внутренние маршруты (работают с БД и логикой внутри микросервиса)
internal_patterns = [
    path('csrf/', get_csrf_token),  # +  +
    path('2gis_accounts/', list_2gis_profiles),  # + +
    # path('2gis_reviews/', render_2gis_profiles_selection, name='2gis_reviews_list'),
    path('2gis_filials/<int:profile_id>/', get_2gis_filials),  # +
    path('create_2gis_profile/', create_2gis_profile),  # + +
    path('update_2gis_profile/<int:profile_id>/', update_2gis_profile),  # + +
    path('link_2gis_profile/<int:profile_id>/', link_2gis_profile),  # + +
]

# Внешние маршруты (Django проксирует запросы к другим микросервисам)
external_patterns = [
    path('proxy_dgis_get_reviews/', proxy_dgis_get_reviews),  # + +
    path('proxy_dgis_get_stats/', proxy_dgis_fetch_stats, name='proxy_dgis_get_stats'),  # + +
    path('favorite_dgis/<int:review_id>/', toggle_dgis_favorite, name='toggle_dgis_favorite'),  # +
    path('proxy_dgis_complaint/<int:review_id>/', toggle_dgis_complaint, name='toggle_dgis_complaint'),  # +
    path('proxy_dgis_reply_review/<int:review_id>/', toggle_dgis_reply_review, name='proxy_dgis_reply_review'),  # +
    path('start_stats_collection_dgis/', trigger_2gis_stats_collection, name='start_stats_collection_dgis'),  # +
]

# Основные маршруты
urlpatterns = [
    path('api/internal/', include(internal_patterns)),  # Внутренние (работают с БД и скриптами)
    path('api/external/', include(external_patterns)),  # Внешние (проксируют запросы)
]

from django.urls import path

from main_site.views.DGis.dgis_api.dgis_api_profile import trigger_2gis_stats_collection, sync_2gis_profile
from main_site.views.DGis.dgis_api.dgis_api_reviews import toggle_dgis_favorite, toggle_dgis_complaint, \
    toggle_dgis_reply_review
from main_site.views.DGis.dgis_profiles import list_2gis_profiles, render_2gis_profiles_selection, create_2gis_profile, \
    update_or_create_2gis_profile
from main_site.views.DGis.dgis_reviews import render_2gis_reviews_page, proxy_dgis_get_reviews, proxy_dgis_fetch_stats

urlpatterns = [
    path('2gis_reviews/', render_2gis_profiles_selection, name='2gis_accounts_list'),
    path('2gis_reviews/<int:profile_id>/', render_2gis_reviews_page, name='2gis_reviews'),

    path('api/proxy_dgis_get_reviews/', proxy_dgis_get_reviews, name='proxy_dgis_get_reviews'),
    path('api/proxy_dgis_get_stats/', proxy_dgis_fetch_stats, name='proxy_dgis_get_stats'),
    path('api/favorite_dgis/<int:review_id>', toggle_dgis_favorite, name='sync_2gis_profile'),
    path('api/proxy_dgis_complaint/<int:review_id>', toggle_dgis_complaint, name='toggle_dgis_complaint'),
    path('api/proxy_dgis_reply_review/<int:review_id>', toggle_dgis_reply_review, name='toggle_dgis_reply_review'),

    path('api/start_stats_collection_dgis/', trigger_2gis_stats_collection, name='start_stats_collection_dgis'),

    path('2gis_accounts/', list_2gis_profiles, name='2gis_accounts'),
    path('create_2gis_profile/', create_2gis_profile, name='create_2gis_profile'),
    path('update_2gis_profile/<int:profile_id>/', sync_2gis_profile, name='update_2gis_profile'),
    path('link_2gis_profile/<int:profile_id>/', update_or_create_2gis_profile, name='update_or_create_2gis_profile'),


]

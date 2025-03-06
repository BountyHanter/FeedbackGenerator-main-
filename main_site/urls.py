from django.urls import path, include

from FeedbackGenerator.utils.get_csrf import get_csrf_token
from main_site.views.DGis.dgis_api.dgis_api_profiles import APIDGISProfiles
from main_site.views.DGis.dgis_api.dgis_api_reviews import APIDGISReviews
from main_site.views.DGis.dgis_profiles import DGISProfiles
from main_site.views.DGis.dgis_filials import DgisFilialAPIView
from main_site.views.Flamp.flamp_api.flamp_api_profiles import APIFlampProfiles
from main_site.views.Flamp.flamp_filials import FlampFilialAPIView
from main_site.views.Flamp.flamp_profiles import FlampProfiles

# Внутренние маршруты (работают с БД и логикой внутри текущего микросервиса)
internal_patterns = [
    path('csrf/', get_csrf_token),  # +  +

    # ПРОФИЛЬ 2ГИС
    # Список профилей и создание нового профиля
    path('2gis_profiles/', DGISProfiles.as_view()),
    # Действия с профилями, требующие указания действия (action)
    path('2gis_profiles/<str:action>/', DGISProfiles.as_view()),
    # Действия с конкретным профилем (action и profile_id)
    path('2gis_profiles/<str:action>/<int:profile_id>/', DGISProfiles.as_view()),

    # ФИЛИАЛЫ 2ГИС
    path('2gis_filials/<int:profile_id>/', DgisFilialAPIView.as_view()),

    # ПРОФИЛЬ Flamp
    # Список профилей и создание нового профиля
    path('flamp_profiles/', FlampProfiles.as_view()),
    # Действия с профилями, требующие указания действия (action)
    path('flamp_profiles/<str:action>/', FlampProfiles.as_view()),
    # Действия с конкретным профилем (action и profile_id)
    path('flamp_profiles/<str:action>/<int:profile_id>/', FlampProfiles.as_view()),

    # ФИЛИАЛЫ Flamp
    path('flamp_filials/<int:profile_id>/', FlampFilialAPIView.as_view()),
]

# Внешние маршруты (Django проксирует запросы к другим микросервисам)
external_patterns = [
    # 2ГИС
    # # Действия с профилем
    path('api_2gis_profiles/<str:action>/', APIDGISProfiles.as_view()),

    # # Действия с отзывами
    path('api_2gis_reviews/<str:action>/<int:review_id>/', APIDGISReviews.as_view()),


    # Flamp
    # # Действия с профилем
    path('api_flamp_profiles/<str:action>/', APIFlampProfiles.as_view()),

    # # Действия с отзывами
    path('api_flamp_reviews/<str:action>/<int:review_id>/', APIDGISReviews.as_view()),

]

# Основные маршруты
urlpatterns = [
    path('api/internal/', include(internal_patterns)),  # Внутренние (работают с БД и скриптами)
    path('api/external/', include(external_patterns)),  # Внешние (проксируют запросы)
]

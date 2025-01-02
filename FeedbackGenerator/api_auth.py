from django.http import JsonResponse


def api_login_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'detail': 'Not authenticated'}, status=401)
        return view_func(request, *args, **kwargs)
    return _wrapped_view

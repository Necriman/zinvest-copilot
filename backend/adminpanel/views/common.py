"""Small helpers shared by the admin views."""
import json

from django.core.paginator import Paginator
from django.http import JsonResponse


def body(request):
    """(data, error_response) for a JSON body."""
    try:
        data = json.loads(request.body or b"{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None, JsonResponse({"detail": "Malformed JSON body."}, status=400)
    if not isinstance(data, dict):
        return None, JsonResponse({"detail": "Expected a JSON object."}, status=400)
    return data, None


def paginate(request, queryset, serialize, *, per_page=25):
    try:
        number = max(1, int(request.GET.get("page", 1)))
    except ValueError:
        number = 1
    try:
        size = min(100, max(5, int(request.GET.get("per_page", per_page))))
    except ValueError:
        size = per_page
    pages = Paginator(queryset, size)
    page = pages.get_page(number)
    return {
        "results": [serialize(item) for item in page.object_list],
        "page": page.number,
        "pages": pages.num_pages,
        "total": pages.count,
    }


def iso(value):
    return value.isoformat() if value else None


def method_not_allowed():
    return JsonResponse({"detail": "Method not allowed."}, status=405)

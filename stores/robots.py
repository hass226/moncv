"""
Robots.txt generator pour MYMEDAGA
"""

from django.http import HttpResponse
from django.views.decorators.http import require_http_methods


@require_http_methods(["GET"])
def robots_txt(request):
    """Génère le fichier robots.txt"""
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /admin/",
        "Disallow: /api/",
        "Disallow: /dashboard/",
        "Disallow: /accounts/",
        "",
        "Sitemap: {scheme}://{host}/sitemap.xml".format(
            scheme=request.scheme,
            host=request.get_host()
        ),
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


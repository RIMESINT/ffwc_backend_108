from django.http import HttpResponseForbidden
from urllib.parse import urlparse

class DomainLockedMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # This is your private internal key
        self.SECRET_VAL = "FFWC-Project-2026-Secure-V1"

    def __call__(self, request):

        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')

        # Trust Localhost and Server IP
        trusted_ips = ['127.0.0.1', 'localhost', 'YOUR_OFFICE_IP']
        
        if ip in trusted_ips:
            return self.get_response(request)

        # assets/uploads    
        # 1. Exempt paths (Admin, Static, Assets/Media, Auth)
        # Added '/assets/' to ensure .tif and other media files load
        exempt = ['/admin/', '/static/', '/assets/', '/api/token/', '/user-auth/','/celery-progress/']
        
        path = request.path_info
        if any(path.startswith(p) for p in exempt) or path == '/':
            return self.get_response(request)

        # 2. Check for the Secret Header
        # Django automatically handles 'X-Ffwc-Internal-Key' as 'x-ffwc-internal-key'
        app_key = request.headers.get('x-ffwc-internal-key')
        if app_key != self.SECRET_VAL:
            return HttpResponseForbidden("Access Denied: Invalid Security Header")

        # 3. Check Origin or Referer (More robust than checking Referer alone)
        # Browsers send 'Origin' for CORS requests; 'Referer' can sometimes be stripped.
        origin_or_referer = request.headers.get('Origin') or request.headers.get('Referer')

        if origin_or_referer:
            # urlparse works for 'https://ffwc.gov.bd' (Origin) 
            # and 'https://ffwc.gov.bd/dashboard' (Referer)
            parsed_url = urlparse(origin_or_referer)
            domain = parsed_url.netloc
            
            # List of trusted domains including local dev ports
            allowed_domains = [
                'ffwc.gov.bd', 
                'www.ffwc.gov.bd', 
                'localhost:4200', 
                '127.0.0.1:4200'
            ]
            
            if domain not in allowed_domains:
                return HttpResponseForbidden(f"Access Denied: Unauthorized Origin ({domain})")
        else:
            # Fallback for cases where neither header is provided
            return HttpResponseForbidden("Access Denied: Origin/Referer missing")

        return self.get_response(request)
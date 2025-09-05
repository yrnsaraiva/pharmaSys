# pharmaSys/context_processors.py
def request_is_secure(request):
    return {'is_secure': request.is_secure()}

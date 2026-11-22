from rest_framework.views import exception_handler

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None
    data = response.data
    message = data.get("detail") if isinstance(data, dict) and "detail" in data else "Request failed"
    details = None if isinstance(data, dict) and "detail" in data else data
    response.data = {"error": {"code": response.status_code,
                               "message": str(message), "details": details}}
    return response
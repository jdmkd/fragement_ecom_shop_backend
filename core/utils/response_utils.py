from rest_framework.response import Response
from rest_framework import status as drf_status
from django.http import JsonResponse
import uuid
import time
from django.utils.timezone import now

def api_response(
        success=True, 
        message=None, 
        data=None, 
        errors=None,    
        meta=None, 
        special_code=None,
        status=drf_status.HTTP_200_OK, 
    ):
    """Standardized API response structure.
    meta: dict -> request_id, timestamp, pagination
    """
    if meta is None:
        meta = {}
    if 'request_id' not in meta:
        meta['request_id'] = str(uuid.uuid4())
    if 'timestamp' not in meta:
        meta['timestamp'] = now().isoformat()


    return Response({
        "success": success,
        "message": message or ("OK" if success else "Error"),
        "special_code": special_code,
        "data": data,
        "errors": errors,
        "meta": meta,
    }, status=status)

def error_response(
        message="An error occurred", 
        error="", 
        status=drf_status.HTTP_400_BAD_REQUEST
    ):
    return JsonResponse(
        {
            "success": False,
            "message": message,
            "data": None,
            "error": error,
        },
        status=status,
        safe=False
    )

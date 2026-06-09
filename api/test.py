# test.py

from http.server import BaseHTTPRequestHandler

def handler(request):
    return {
        "statusCode": 200,
        "body": "Endpoint funcionando 🔥"
    }
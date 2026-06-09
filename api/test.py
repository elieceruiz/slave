# test.py

def handler(request):
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "text/plain"
        },
        "body": "Endpoint funcionando 🔥"
    }
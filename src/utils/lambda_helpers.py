import json


def lambdaResponse(message: str, statusCode: int):
    return {
        "statusCode": statusCode,
        "body": json.dumps({"message": message}),
    }
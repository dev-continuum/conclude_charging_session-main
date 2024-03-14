from config import Settings
import boto3

settings = Settings()

def get_socket_client():
    return boto3.client('apigatewaymanagementapi', endpoint_url=settings.WEB_SOCKET_API)

def get_lambda():
    return boto3.client('lambda', region_name=settings.LAMBDA_REGION)

def get_s3():
    return boto3.client('s3', region_name=settings.LAMBDA_REGION)
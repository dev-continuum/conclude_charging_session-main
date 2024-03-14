import simplejson


def invoke_third_party_url_lambda(lambda_client, function_name, payload):
    result = lambda_client.invoke(FunctionName=function_name, Payload=simplejson.dumps(payload))
    result_to_return = simplejson.loads(result["Payload"].read().decode())
    return {"status_code": result_to_return["status_code"],
            "message": result_to_return["message"],
            "data": result_to_return["data"]}

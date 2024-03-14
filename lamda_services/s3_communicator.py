import simplejson

def get_data_from_s3_bucket(s3_client, bucket_name, file_name):
    s3_vendor_param_object = s3_client.get_object(Bucket=bucket_name, Key=file_name)
    return simplejson.loads(s3_vendor_param_object['Body'].read().decode('utf-8'))
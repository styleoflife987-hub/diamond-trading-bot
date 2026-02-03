#!/usr/bin/env python3
"""
Initialize S3 bucket structure
"""
import boto3
import os
from botocore.exceptions import ClientError

def init_s3_bucket():
    # Load environment variables
    bucket_name = os.getenv('AWS_BUCKET')
    
    if not bucket_name:
        print("❌ AWS_BUCKET environment variable not set")
        return False
    
    try:
        s3 = boto3.client('s3')
        
        # Check if bucket exists
        try:
            s3.head_bucket(Bucket=bucket_name)
            print(f"✅ Bucket '{bucket_name}' already exists")
        except ClientError:
            # Create bucket if it doesn't exist
            region = os.getenv('AWS_REGION', 'ap-south-1')
            if region == 'us-east-1':
                s3.create_bucket(Bucket=bucket_name)
            else:
                s3.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': region}
                )
            print(f"✅ Created bucket '{bucket_name}'")
        
        # Create folder structure
        folders = [
            'users/',
            'stock/',
            'stock/suppliers/',
            'stock/combined/',
            'activity_logs/',
            'deals/',
            'notifications/',
            'sessions/'
        ]
        
        for folder in folders:
            try:
                s3.put_object(Bucket=bucket_name, Key=folder)
                print(f"✅ Created folder: {folder}")
            except Exception as e:
                print(f"⚠️ Error creating folder {folder}: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error initializing S3: {e}")
        return False

if __name__ == '__main__':
    init_s3_bucket()

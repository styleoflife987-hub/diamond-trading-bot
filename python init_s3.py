import boto3
import pandas as pd
import os
from io import BytesIO

# Your AWS credentials (replace with actual values)
AWS_ACCESS_KEY_ID = "your_aws_key_here"
AWS_SECRET_ACCESS_KEY = "your_aws_secret_here"
AWS_BUCKET = "diamond-bucket-styleoflifes"
AWS_REGION = "ap-south-1"

# Initialize S3 client
s3 = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)

def initialize_s3():
    """Initialize S3 bucket with required structure"""
    
    print("🚀 Initializing S3 bucket for Diamond Trading Bot...")
    
    try:
        # 1. Create accounts.xlsx with default admin
        print("Creating accounts file...")
        accounts_data = {
            'USERNAME': ['admin'],
            'PASSWORD': ['admin123'],
            'ROLE': ['admin'],
            'APPROVED': ['YES']
        }
        accounts_df = pd.DataFrame(accounts_data)
        
        # Upload to S3
        excel_buffer = BytesIO()
        accounts_df.to_excel(excel_buffer, index=False)
        excel_buffer.seek(0)
        
        s3.put_object(
            Bucket=AWS_BUCKET,
            Key='users/accounts.xlsx',
            Body=excel_buffer.read(),
            ContentType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        print("✅ Created accounts.xlsx with default admin (admin/admin123)")
        
        # 2. Create empty stock file
        print("Creating stock file...")
        stock_columns = [
            'Stock #', 'Shape', 'Weight', 'Color', 'Clarity', 
            'Price Per Carat', 'Lab', 'Report #', 'Diamond Type', 
            'Description', 'CUT', 'Polish', 'Symmetry',
            'SUPPLIER', 'LOCKED', 'UPLOADED_AT'
        ]
        stock_df = pd.DataFrame(columns=stock_columns)
        
        excel_buffer = BytesIO()
        stock_df.to_excel(excel_buffer, index=False)
        excel_buffer.seek(0)
        
        s3.put_object(
            Bucket=AWS_BUCKET,
            Key='stock/combined/all_suppliers_stock.xlsx',
            Body=excel_buffer.read(),
            ContentType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        print("✅ Created empty stock file")
        
        # 3. Create folder structure (empty files)
        print("Creating folder structure...")
        folders = [
            'stock/suppliers/',
            'activity_logs/',
            'deals/',
            'notifications/',
            'sessions/'
        ]
        
        for folder in folders:
            s3.put_object(Bucket=AWS_BUCKET, Key=folder)
            print(f"✅ Created folder: {folder}")
        
        print("\n" + "="*60)
        print("🎉 S3 BUCKET INITIALIZED SUCCESSFULLY!")
        print("="*60)
        print(f"Bucket: {AWS_BUCKET}")
        print("Default Admin Credentials:")
        print("• Username: admin")
        print("• Password: admin123")
        print("• Role: admin")
        print("\n✅ Your bot is ready to use!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n⚠️ Make sure:")
        print("1. AWS credentials are correct")
        print("2. S3 bucket exists: diamond-bucket-styleoflifes")
        print("3. AWS user has proper permissions")

if __name__ == "__main__":
    initialize_s3()

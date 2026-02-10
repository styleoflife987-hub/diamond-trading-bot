"""
Diamond Trading Bot - S3 Setup Script
Creates all required files and directories in S3 bucket
"""

import boto3
import pandas as pd
import json
import os
from io import BytesIO
from datetime import datetime
import sys

def create_s3_structure():
    """Create complete S3 structure for Diamond Trading Bot"""
    
    # Configuration
    AWS_CONFIG = {
        "aws_access_key_id": os.getenv("AWS_ACCESS_KEY_ID"),
        "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
        "region_name": os.getenv("AWS_REGION", "ap-south-1")
    }
    
    BUCKET_NAME = os.getenv("AWS_BUCKET")
    
    # Validate credentials
    if not all([AWS_CONFIG["aws_access_key_id"], AWS_CONFIG["aws_secret_access_key"], BUCKET_NAME]):
        print("❌ Missing AWS credentials or bucket name")
        print("Please set these environment variables:")
        print("  - AWS_ACCESS_KEY_ID")
        print("  - AWS_SECRET_ACCESS_KEY")
        print("  - AWS_BUCKET")
        print("  - AWS_REGION (optional, defaults to ap-south-1)")
        return False
    
    try:
        # Initialize S3 client
        s3 = boto3.client("s3", **AWS_CONFIG)
        
        # Check if bucket exists, create if not
        try:
            s3.head_bucket(Bucket=BUCKET_NAME)
            print(f"✅ Bucket '{BUCKET_NAME}' exists")
        except:
            print(f"📦 Creating bucket '{BUCKET_NAME}'...")
            s3.create_bucket(
                Bucket=BUCKET_NAME,
                CreateBucketConfiguration={
                    'LocationConstraint': AWS_CONFIG["region_name"]
                }
            )
            print(f"✅ Bucket '{BUCKET_NAME}' created")
        
        print("\n" + "="*50)
        print("SETTING UP S3 STRUCTURE FOR DIAMOND TRADING BOT")
        print("="*50 + "\n")
        
        # ============ CREATE DIRECTORIES ============
        directories = [
            "users/",
            "stock/",
            "stock/suppliers/",
            "stock/combined/",
            "deals/",
            "activity_logs/",
            "activity_logs/" + datetime.now().strftime("%Y-%m-%d") + "/",
            "notifications/",
            "sessions/"
        ]
        
        for directory in directories:
            try:
                # Create directory by uploading empty object
                s3.put_object(Bucket=BUCKET_NAME, Key=directory)
                print(f"✅ Created directory: {directory}")
            except Exception as e:
                print(f"⚠️  Could not create {directory}: {e}")
        
        # ============ CREATE ACCOUNTS.XLSX ============
        print("\n📝 Creating accounts.xlsx...")
        
        # Create sample admin user (change password!)
        accounts_data = {
            'USERNAME': ['admin', 'supplier1', 'client1'],
            'PASSWORD': ['Admin@123', 'Supplier@123', 'Client@123'],
            'ROLE': ['admin', 'supplier', 'client'],
            'APPROVED': ['YES', 'YES', 'YES']
        }
        
        accounts_df = pd.DataFrame(accounts_data)
        
        # Save to buffer
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            accounts_df.to_excel(writer, index=False, sheet_name='Accounts')
            
            # Add instructions sheet
            instructions = pd.DataFrame({
                'Column': ['USERNAME', 'PASSWORD', 'ROLE', 'APPROVED'],
                'Required': ['YES', 'YES', 'YES', 'YES'],
                'Description': [
                    'Unique username for login',
                    'Password (plain text, will be cleaned)',
                    'Role: admin, supplier, or client',
                    'Approval status: YES or NO'
                ],
                'Example': ['john_doe', 'password123', 'supplier', 'YES']
            })
            instructions.to_excel(writer, index=False, sheet_name='Instructions')
        
        buffer.seek(0)
        
        # Upload to S3
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key='users/accounts.xlsx',
            Body=buffer.getvalue(),
            ContentType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        print("✅ Created users/accounts.xlsx")
        print("   Default users created:")
        print("   - admin / Admin@123 (ADMIN)")
        print("   - supplier1 / Supplier@123 (SUPPLIER)")
        print("   - client1 / Client@123 (CLIENT)")
        print("   ⚠️  CHANGE THESE PASSWORDS IMMEDIATELY!")
        
        # ============ CREATE EMPTY COMBINED STOCK ============
        print("\n📊 Creating empty stock files...")
        
        # Combined stock columns
        stock_columns = [
            'Stock #', 'Shape', 'Weight', 'Color', 'Clarity',
            'Price Per Carat', 'Lab', 'Report #', 'Diamond Type',
            'Description', 'CUT', 'Polish', 'Symmetry',
            'SUPPLIER', 'LOCKED', 'UPLOADED_AT'
        ]
        
        empty_stock_df = pd.DataFrame(columns=stock_columns)
        
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            empty_stock_df.to_excel(writer, index=False, sheet_name='Stock')
            
            # Add validation instructions
            validation_rules = pd.DataFrame({
                'Column': stock_columns[:10],  # Required columns
                'Required': ['YES'] * 10,
                'Data Type': [
                    'Text (Unique)',
                    'Text (Round, Oval, etc)',
                    'Number (Carats)',
                    'Text (D, E, F, etc)',
                    'Text (IF, VVS1, VS1, etc)',
                    'Number ($ per carat)',
                    'Text (GIA, IGI, HRD, etc)',
                    'Text',
                    'Text (Natural, Lab Grown)',
                    'Text'
                ]
            })
            validation_rules.to_excel(writer, index=False, sheet_name='Validation Rules')
        
        buffer.seek(0)
        
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key='stock/combined/all_suppliers_stock.xlsx',
            Body=buffer.getvalue(),
            ContentType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        print("✅ Created stock/combined/all_suppliers_stock.xlsx")
        
        # ============ CREATE EMPTY DEAL HISTORY ============
        print("\n🤝 Creating deal history file...")
        
        deal_columns = [
            'Deal ID', 'Stone ID', 'Supplier', 'Client',
            'Actual Price', 'Offer Price', 'Supplier Action',
            'Admin Action', 'Final Status', 'Created At'
        ]
        
        empty_deals_df = pd.DataFrame(columns=deal_columns)
        
        buffer = BytesIO()
        empty_deals_df.to_excel(buffer, index=False)
        buffer.seek(0)
        
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key='deals/deal_history.xlsx',
            Body=buffer.getvalue(),
            ContentType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        print("✅ Created deals/deal_history.xlsx")
        
        # ============ CREATE SESSION FILE ============
        print("\n🔐 Creating session file...")
        
        empty_sessions = {}
        
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key='sessions/logged_in_users.json',
            Body=json.dumps(empty_sessions, indent=2),
            ContentType='application/json'
        )
        print("✅ Created sessions/logged_in_users.json")
        
        # ============ CREATE SAMPLE EXCEL TEMPLATE ============
        print("\n📥 Creating sample Excel template...")
        
        sample_data = {
            'Stock #': ['DIA001', 'DIA002', 'DIA003'],
            'Shape': ['Round', 'Princess', 'Oval'],
            'Weight': [1.20, 0.90, 1.50],
            'Color': ['D', 'F', 'G'],
            'Clarity': ['IF', 'VVS1', 'VS1'],
            'Price Per Carat': [12000, 9500, 7500],
            'Lab': ['GIA', 'IGI', 'HRD'],
            'Report #': ['1234567890', '2345678901', '3456789012'],
            'Diamond Type': ['Natural', 'Natural', 'Lab Grown'],
            'Description': ['Eye clean round', 'Excellent princess', 'Nice oval'],
            'CUT': ['EX', 'VG', ''],
            'Polish': ['EX', '', 'VG'],
            'Symmetry': ['EX', 'VG', '']
        }
        
        sample_df = pd.DataFrame(sample_data)
        
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            # Sample data sheet
            sample_df.to_excel(writer, index=False, sheet_name='Sample Stock')
            
            # Instructions sheet
            instructions_data = {
                'Column Name': [
                    'Stock #', 'Shape', 'Weight', 'Color', 'Clarity',
                    'Price Per Carat', 'Lab', 'Report #', 'Diamond Type',
                    'Description', 'CUT', 'Polish', 'Symmetry'
                ],
                'Required?': [
                    'REQUIRED', 'REQUIRED', 'REQUIRED', 'REQUIRED', 'REQUIRED',
                    'REQUIRED', 'REQUIRED', 'REQUIRED', 'REQUIRED', 'REQUIRED',
                    'OPTIONAL', 'OPTIONAL', 'OPTIONAL'
                ],
                'Description': [
                    'Unique identifier for each diamond',
                    'Shape of the diamond (Round, Princess, Oval, etc.)',
                    'Weight in carats (e.g., 1.20)',
                    'Color grade (D, E, F, etc.)',
                    'Clarity grade (IF, VVS1, VS2, etc.)',
                    'Price per carat in USD',
                    'Certification lab (GIA, IGI, HRD, etc.)',
                    'Certificate/report number',
                    'Type of diamond (Natural, Lab Grown, etc.)',
                    'Description or comments about the diamond',
                    'Cut grade (EX, VG, G, F, P) - CAN BE BLANK',
                    'Polish grade (EX, VG, G, F, P) - CAN BE BLANK',
                    'Symmetry grade (EX, VG, G, F, P) - CAN BE BLANK'
                ],
                'Example': [
                    'DIA001, STK100, 12345',
                    'Round, Princess, Oval',
                    '1.20, 0.90, 1.50',
                    'D, F, G',
                    'IF, VVS1, VS2',
                    '12000, 9500, 7500',
                    'GIA, IGI, HRD',
                    '1234567890, G12345',
                    'Natural, Lab Grown',
                    'Eye clean, No fluorescence',
                    'EX, VG, G',
                    'EX, VG, G',
                    'EX, VG, G'
                ]
            }
            
            instructions_df = pd.DataFrame(instructions_data)
            instructions_df.to_excel(writer, index=False, sheet_name='Instructions')
            
            # Format columns
            workbook = writer.book
            worksheet = writer.sheets['Instructions']
            
            # Auto-adjust column widths
            for column in instructions_df:
                column_length = max(
                    instructions_df[column].astype(str).map(len).max(),
                    len(str(column))
                )
                col_idx = instructions_df.columns.get_loc(column)
                worksheet.column_dimensions[chr(65 + col_idx)].width = column_length + 2
        
        buffer.seek(0)
        
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key='stock/suppliers/SAMPLE_TEMPLATE.xlsx',
            Body=buffer.getvalue(),
            ContentType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        print("✅ Created stock/suppliers/SAMPLE_TEMPLATE.xlsx")
        print("   This file can be downloaded by suppliers as a template")
        
        # ============ VERIFY STRUCTURE ============
        print("\n" + "="*50)
        print("VERIFICATION")
        print("="*50)
        
        required_files = [
            'users/accounts.xlsx',
            'stock/combined/all_suppliers_stock.xlsx',
            'deals/deal_history.xlsx',
            'sessions/logged_in_users.json',
            'stock/suppliers/SAMPLE_TEMPLATE.xlsx'
        ]
        
        all_good = True
        for file_key in required_files:
            try:
                s3.head_object(Bucket=BUCKET_NAME, Key=file_key)
                print(f"✅ Verified: {file_key}")
            except:
                print(f"❌ Missing: {file_key}")
                all_good = False
        
        if all_good:
            print("\n🎉 S3 STRUCTURE SETUP COMPLETE!")
            print("\n📋 NEXT STEPS:")
            print("1. Change default passwords in users/accounts.xlsx")
            print("2. Add more users as needed")
            print("3. Deploy your Diamond Trading Bot")
            print("4. Test the setup by logging in with admin credentials")
            
            print("\n🔧 Quick Test Command:")
            print(f"aws s3 ls s3://{BUCKET_NAME}/ --recursive --human-readable")
            
            return True
        else:
            print("\n⚠️  Some files are missing. Please check the setup.")
            return False
        
    except Exception as e:
        print(f"\n❌ Error during setup: {e}")
        print("\n🔧 Troubleshooting Tips:")
        print("1. Check AWS credentials are correct")
        print("2. Ensure IAM user has S3 permissions")
        print("3. Verify bucket name is unique and accessible")
        print("4. Check network connectivity to AWS")
        return False

def print_bucket_policy(bucket_name):
    """Print bucket policy for easy setup"""
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": "*",
                "Action": [
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:DeleteObject",
                    "s3:ListBucket"
                ],
                "Resource": [
                    f"arn:aws:s3:::{bucket_name}",
                    f"arn:aws:s3:::{bucket_name}/*"
                ]
            }
        ]
    }
    
    print("\n" + "="*50)
    print("BUCKET POLICY (if needed)")
    print("="*50)
    print(json.dumps(policy, indent=2))
    print("\nTo apply this policy:")
    print(f"aws s3api put-bucket-policy --bucket {bucket_name} --policy '{json.dumps(policy)}'")

if __name__ == "__main__":
    print("🚀 Diamond Trading Bot - S3 Setup Utility")
    print("="*50)
    
    # Load environment from .env file if exists
    if os.path.exists(".env"):
        from dotenv import load_dotenv
        load_dotenv()
        print("✅ Loaded environment variables from .env file")
    
    # Run setup
    success = create_s3_structure()
    
    if success and os.getenv("AWS_BUCKET"):
        print_bucket_policy(os.getenv("AWS_BUCKET"))
    
    if not success:
        sys.exit(1)

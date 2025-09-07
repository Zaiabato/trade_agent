from dotenv import load_dotenv
import os

load_dotenv()
print(f"API Key: {os.getenv('API_KEY')}")
print(f"API Secret: {os.getenv('API_SECRET')}")
print(f"Environment: {os.getenv('ENVIRONMENT')}")


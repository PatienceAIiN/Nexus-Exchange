import os
import sys
import logging

# Add backend to path so we can import config and services
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import settings
from services.email_service import send_approval_email

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_mail():
    print("--- SMTP Configuration ---")
    print(f"Host: {settings.SMTP_HOST}")
    print(f"Port: {settings.SMTP_PORT}")
    print(f"User: {settings.SMTP_USER}")
    print(f"Secure: {settings.SMTP_SECURE}")
    print(f"Sender Name: {settings.SMTP_SENDER_NAME}")
    print("--------------------------")
    
    test_recipient = "growth@patienceai.in" # Testing with the sender email itself
    print(f"Attempting to send test approval email to: {test_recipient}")
    
    success = send_approval_email("TestUser", test_recipient)
    
    if success:
        print("\nSUCCESS: Email sent successfully!")
    else:
        print("\nFAILED: Email sending failed. Check the logs above for the error.")

if __name__ == "__main__":
    test_mail()

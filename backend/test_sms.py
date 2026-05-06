"""
Run this from the backend folder to debug Twilio SMS.
Usage: python test_sms.py
"""
from dotenv import load_dotenv
import os

load_dotenv(dotenv_path=".env")

sid   = os.getenv("TWILIO_ACCOUNT_SID", "")
token = os.getenv("TWILIO_AUTH_TOKEN", "")
from_ = os.getenv("TWILIO_PHONE_NUMBER", "")

print(f"SID   : {sid}")
print(f"Token : {token[:6]}{'*'*20}")
print(f"From  : {from_}")

if not sid or not token or not from_:
    print("\n❌ One or more Twilio env vars are empty! Check your .env file.")
    exit(1)

# Ask which number to send to
to = input("\nEnter the TO number to test (e.g. +919876543210): ").strip()

try:
    from twilio.rest import Client
    client = Client(sid, token)
    msg = client.messages.create(
        body="🚨 MindSense AI Test Alert: Twilio SMS is working correctly!",
        from_=from_,
        to=to
    )
    print(f"\n✅ SMS sent successfully! SID: {msg.sid}")
except Exception as e:
    print(f"\n❌ Twilio error: {e}")
    print("\nCommon fixes:")
    print("  1. Verify the TO number at: https://console.twilio.com/us1/develop/phone-numbers/manage/verified")
    print("  2. Enable geographic permissions for India at: https://console.twilio.com/us1/develop/sms/settings/geo-permissions")
    print("  3. Make sure FROM number is your Twilio-assigned number, not your personal number")

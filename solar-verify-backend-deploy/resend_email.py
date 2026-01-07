"""
Resend Email Helper Module for Solar Verify
Replaces SendGrid with Resend for email sending
"""
import os
import requests
import base64

RESEND_API_KEY = os.environ.get('RESEND_API_KEY')
RESEND_API_URL = 'https://api.resend.com/emails'
FROM_EMAIL = 'SolarVerify <noreply@solarverify.co.uk>'


def send_email(to_email, subject, html_content, attachments=None):
    """
    Send an email using Resend API
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        html_content: HTML content of the email
        attachments: List of dicts with 'filename', 'content' (base64), and 'type' keys
        
    Returns:
        Boolean indicating success
    """
    if not RESEND_API_KEY:
        print("Error: RESEND_API_KEY not configured")
        return False
    
    headers = {
        'Authorization': f'Bearer {RESEND_API_KEY}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        'from': FROM_EMAIL,
        'to': [to_email],
        'subject': subject,
        'html': html_content
    }
    
    if attachments:
        payload['attachments'] = attachments
    
    try:
        response = requests.post(RESEND_API_URL, headers=headers, json=payload)
        
        if response.status_code in [200, 201]:
            print(f"Email sent successfully to {to_email}")
            return True
        else:
            print(f"Error sending email: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"Exception sending email: {str(e)}")
        return False


def send_email_with_attachment(to_email, subject, html_content, attachment_data, attachment_filename, attachment_type='application/pdf'):
    """
    Send an email with a single attachment using Resend API
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        html_content: HTML content of the email
        attachment_data: Raw bytes of the attachment
        attachment_filename: Name of the attachment file
        attachment_type: MIME type of the attachment
        
    Returns:
        Boolean indicating success
    """
    # Encode attachment to base64
    encoded_attachment = base64.b64encode(attachment_data).decode('utf-8')
    
    attachments = [{
        'filename': attachment_filename,
        'content': encoded_attachment
    }]
    
    return send_email(to_email, subject, html_content, attachments)


# Alias for backward compatibility with main.py
def send_email_with_resend(to_email, subject, html_content, attachment_data, attachment_filename, attachment_type='application/pdf'):
    """
    Alias for send_email_with_attachment for backward compatibility
    Note: attachment_data should already be base64 encoded
    """
    attachments = [{
        'filename': attachment_filename,
        'content': attachment_data  # Already base64 encoded
    }]
    
    return send_email(to_email, subject, html_content, attachments)

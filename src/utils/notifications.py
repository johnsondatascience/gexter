"""
Notification system for GEX data collector

Supports Slack webhooks and email notifications for monitoring
and alerting on data collection status.
"""

import requests
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional

logger = logging.getLogger('gex_collector')


class NotificationManager:
    """Manages notifications for GEX data collection events"""
    
    def __init__(self, config):
        self.config = config
        self.slack_webhook_url = config.slack_webhook_url
        self.email_config = {
            'smtp_server': config.email_smtp_server,
            'smtp_port': config.email_smtp_port,
            'username': config.email_username,
            'password': config.email_password,
            'to_email': config.email_to
        }
    
    def send_slack_notification(self, message: str, color: str = "good") -> bool:
        """Send notification to Slack webhook"""
        if not self.slack_webhook_url:
            return True  # Skip if not configured
        
        try:
            payload = {
                "attachments": [
                    {
                        "color": color,
                        "title": "GEX Data Collector",
                        "text": message,
                        "ts": int(datetime.now().timestamp())
                    }
                ]
            }
            
            response = requests.post(self.slack_webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            
            logger.info("Slack notification sent successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
            return False
    
    def send_email_notification(self, subject: str, message: str) -> bool:
        """Send email notification"""
        if not all([self.email_config['smtp_server'], self.email_config['username'], 
                   self.email_config['password'], self.email_config['to_email']]):
            return True  # Skip if not configured
        
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.email_config['username']
            msg['To'] = self.email_config['to_email']
            msg['Subject'] = subject
            
            # Add body
            msg.attach(MIMEText(message, 'plain'))
            
            # Send email
            server = smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port'])
            server.starttls()
            server.login(self.email_config['username'], self.email_config['password'])
            
            text = msg.as_string()
            server.sendmail(self.email_config['username'], self.email_config['to_email'], text)
            server.quit()
            
            logger.info("Email notification sent successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            return False
    
    def notify_success(self, records_processed: int, duration: float):
        """Send success notification"""
        message = (f"✅ GEX data collection completed successfully\n"
                  f"Records processed: {records_processed:,}\n"
                  f"Duration: {duration:.2f} seconds\n"
                  f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        self.send_slack_notification(message, "good")
        
        subject = "GEX Data Collection - Success"
        self.send_email_notification(subject, message)
    
    def notify_failure(self, error_message: str):
        """Send failure notification"""
        message = (f"❌ GEX data collection failed\n"
                  f"Error: {error_message}\n"
                  f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                  f"Please check logs for more details.")
        
        self.send_slack_notification(message, "danger")
        
        subject = "GEX Data Collection - FAILURE"
        self.send_email_notification(subject, message)
    
    def notify_warning(self, warning_message: str):
        """Send warning notification"""
        message = (f"⚠️ GEX data collection warning\n"
                  f"Warning: {warning_message}\n"
                  f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        self.send_slack_notification(message, "warning")
        
        subject = "GEX Data Collection - Warning"
        self.send_email_notification(subject, message)
    
    def notify_rate_limit(self, reset_time: str):
        """Send rate limit notification"""
        message = (f"⏱️ API rate limit reached\n"
                  f"Rate limit resets in: {reset_time} seconds\n"
                  f"Data collection will retry automatically\n"
                  f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        self.send_slack_notification(message, "warning")
    
    def test_notifications(self) -> dict:
        """Test notification systems"""
        results = {}
        
        test_message = f"🧪 Test notification from GEX Data Collector\nTimestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # Test Slack
        if self.slack_webhook_url:
            results['slack'] = self.send_slack_notification(test_message)
        else:
            results['slack'] = None  # Not configured
        
        # Test Email
        if all([self.email_config['smtp_server'], self.email_config['username']]):
            results['email'] = self.send_email_notification("GEX Collector - Test Notification", test_message)
        else:
            results['email'] = None  # Not configured
        
        return results
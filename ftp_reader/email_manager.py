import os
import logging
from typing import List, Optional
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, HtmlContent
from db_manager import DBManager

logger = logging.getLogger()

class EmailManager:
    """Manages SendGrid email notifications for failures"""
    
    def __init__(self):
        self.api_key = os.environ.get('SENDGRID_API_KEY')
        self.from_email = os.environ.get('SENDGRID_FROM_EMAIL')
        self.from_name = os.environ.get('SENDGRID_FROM_NAME', 'FTP Reader System')
        
        if not self.api_key or not self.from_email:
            logger.warning("SendGrid configuration missing. Email notifications will be disabled.")
            self.enabled = False
        else:
            self.enabled = True
            self.client = SendGridAPIClient(api_key=self.api_key)
    
    def get_recipient_emails(self) -> List[str]:
        """Get list of recipient emails from database"""
        try:
            return DBManager.get_recipient_emails()
        except Exception as e:
            logger.error(f"Error getting emails from database: {str(e)}")
            return []
    
    def send_failure_notification(self, filename: str, error_message: str, 
                                unique_id: str, site_id: Optional[str] = None) -> bool:
        """Send failure notification email"""
        if not self.enabled:
            logger.info("Email notifications disabled. Skipping failure notification.")
            return False
        
        try:
            recipient_emails = self.get_recipient_emails()
            if not recipient_emails:
                logger.warning("No recipient emails found. Skipping failure notification.")
                return False
            
            # Create email content
            subject = f"FTP Reader Failure: {filename}"
            
            html_content = self._create_failure_email_html(
                filename, error_message, unique_id, site_id
            )
            
            # Send email to each recipient
            success_count = 0
            for recipient_email in recipient_emails:
                try:
                    mail = Mail(
                        from_email=Email(self.from_email, self.from_name),
                        to_emails=To(recipient_email),
                        subject=subject,
                        html_content=HtmlContent(html_content)
                    )
                    
                    response = self.client.send(mail)
                    
                    if response.status_code == 202:
                        logger.info(f"Failure notification sent successfully to {recipient_email}")
                        success_count += 1
                    else:
                        logger.error(f"Failed to send email to {recipient_email}. Status: {response.status_code}")
                        
                except Exception as e:
                    logger.error(f"Error sending email to {recipient_email}: {str(e)}")
            
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Error in send_failure_notification: {str(e)}")
            return False
    
    def _create_failure_email_html(self, filename: str, error_message: str, 
                                 unique_id: str, site_id: Optional[str] = None) -> str:
        """Create HTML content for failure notification email"""
        
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background-color: #dc3545; color: white; padding: 20px; border-radius: 5px 5px 0 0; }
                .content { background-color: #f8f9fa; padding: 20px; border-radius: 0 0 5px 5px; }
                .error-box { background-color: #fff; border-left: 4px solid #dc3545; padding: 15px; margin: 15px 0; }
                .info-row { margin: 10px 0; }
                .label { font-weight: bold; color: #495057; }
                .value { color: #6c757d; }
                .footer { margin-top: 20px; padding-top: 20px; border-top: 1px solid #dee2e6; font-size: 12px; color: #6c757d; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>🚨 FTP Reader Processing Failure</h2>
                </div>
                <div class="content">
                    <p>A file processing failure has occurred in the FTP Reader system.</p>
                    
                    <div class="info-row">
                        <span class="label">File Name:</span>
                        <span class="value">{filename}</span>
                    </div>
                    
                    <div class="info-row">
                        <span class="label">Process ID:</span>
                        <span class="value">{unique_id}</span>
                    </div>
                    
                    {site_id_row}
                    
                    <div class="info-row">
                        <span class="label">Timestamp:</span>
                        <span class="value">{timestamp}</span>
                    </div>
                    
                    <div class="error-box">
                        <strong>Error Details:</strong><br>
                        <pre>{error_message}</pre>
                    </div>
                    
                    <p><strong>Action Required:</strong> Please investigate the issue and take appropriate action to resolve the processing failure.</p>
                </div>
                
                <div class="footer">
                    <p>This is an automated notification from the FTP Reader system. Please do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        from datetime import datetime
        
        site_id_row = ""
        if site_id:
            site_id_row = f"""
            <div class="info-row">
                <span class="label">Site ID:</span>
                <span class="value">{site_id}</span>
            </div>
            """
        
        return html_template.format(
            filename=filename,
            unique_id=unique_id,
            site_id_row=site_id_row,
            timestamp=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
            error_message=error_message
        )
    
    def send_batch_failure_notification(self, failures: List[dict]) -> bool:
        """Send batch failure notification for multiple failures"""
        if not self.enabled:
            logger.info("Email notifications disabled. Skipping batch failure notification.")
            return False
        
        try:
            recipient_emails = self.get_recipient_emails()
            if not recipient_emails:
                logger.warning("No recipient emails found. Skipping batch failure notification.")
                return False
            
            # Create email content
            subject = f"FTP Reader Batch Failures: {len(failures)} files failed"
            
            html_content = self._create_batch_failure_email_html(failures)
            
            # Send email to each recipient
            success_count = 0
            for recipient_email in recipient_emails:
                try:
                    mail = Mail(
                        from_email=Email(self.from_email, self.from_name),
                        to_emails=To(recipient_email),
                        subject=subject,
                        html_content=HtmlContent(html_content)
                    )
                    
                    response = self.client.send(mail)
                    
                    if response.status_code == 202:
                        logger.info(f"Batch failure notification sent successfully to {recipient_email}")
                        success_count += 1
                    else:
                        logger.error(f"Failed to send batch email to {recipient_email}. Status: {response.status_code}")
                        
                except Exception as e:
                    logger.error(f"Error sending batch email to {recipient_email}: {str(e)}")
            
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Error in send_batch_failure_notification: {str(e)}")
            return False
    
    def _create_batch_failure_email_html(self, failures: List[dict]) -> str:
        """Create HTML content for batch failure notification email"""
        
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 800px; margin: 0 auto; padding: 20px; }
                .header { background-color: #dc3545; color: white; padding: 20px; border-radius: 5px 5px 0 0; }
                .content { background-color: #f8f9fa; padding: 20px; border-radius: 0 0 5px 5px; }
                .failure-table { width: 100%; border-collapse: collapse; margin: 15px 0; }
                .failure-table th, .failure-table td { border: 1px solid #dee2e6; padding: 8px; text-align: left; }
                .failure-table th { background-color: #e9ecef; font-weight: bold; }
                .failure-table tr:nth-child(even) { background-color: #f8f9fa; }
                .footer { margin-top: 20px; padding-top: 20px; border-top: 1px solid #dee2e6; font-size: 12px; color: #6c757d; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>🚨 FTP Reader Batch Processing Failures</h2>
                </div>
                <div class="content">
                    <p><strong>{failure_count}</strong> files failed during batch processing.</p>
                    
                    <table class="failure-table">
                        <thead>
                            <tr>
                                <th>File Name</th>
                                <th>Process ID</th>
                                <th>Site ID</th>
                                <th>Error Message</th>
                            </tr>
                        </thead>
                        <tbody>
                            {failure_rows}
                        </tbody>
                    </table>
                    
                    <p><strong>Action Required:</strong> Please investigate these failures and take appropriate action to resolve the processing issues.</p>
                </div>
                
                <div class="footer">
                    <p>This is an automated notification from the FTP Reader system. Please do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        failure_rows = ""
        for failure in failures:
            site_id = failure.get('site_id', 'N/A')
            failure_rows += f"""
            <tr>
                <td>{failure['filename']}</td>
                <td>{failure['unique_id']}</td>
                <td>{site_id}</td>
                <td><pre style="margin: 0; white-space: pre-wrap;">{failure['error_message']}</pre></td>
            </tr>
            """
        
        return html_template.format(
            failure_count=len(failures),
            failure_rows=failure_rows
        ) 
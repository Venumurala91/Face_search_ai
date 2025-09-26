import os
import io
import smtplib
import zipfile
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- SMTP Configuration ---
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", 465))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_SENDER_EMAIL = os.getenv("SMTP_SENDER_EMAIL")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

def send_photos_email(recipient_email: str, image_paths: list, guest_name: str):
    """
    Creates a zip of photos in-memory and emails it to the recipient using Gmail.
    """
    if not all([SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, SMTP_SENDER_EMAIL]):
        print("--- FATAL: SMTP environment variables are not fully configured. Cannot send email. ---")
        return False

    try:
        # 1. Create the ZIP file in-memory
        zip_io = io.BytesIO()
        with zipfile.ZipFile(zip_io, mode='w', compression=zipfile.ZIP_DEFLATED) as temp_zip:
            for original_path in image_paths:
                if os.path.exists(original_path):
                    temp_zip.write(original_path, arcname=os.path.basename(original_path))
        zip_io.seek(0)
        if len(zip_io.getvalue()) == 0:
            print(f"--- WARNING: Created empty ZIP for {recipient_email}. No valid image paths found. Aborting email. ---")
            return False

        # 2. Create the email message
        msg = MIMEMultipart()
        msg['Subject'] = "Your Park Memories Are Here!"
        msg['From'] = f"Your Park Memories <{SMTP_SENDER_EMAIL}>"
        msg['To'] = recipient_email

        # 3. Create the email body (HTML)
        html_body = f"""
        <html>
        <body>
            <h2>Hello {guest_name},</h2>
            <p>Thank you for visiting! We're excited to share your memories with you.</p>
            <p>Your photos are attached to this email as a ZIP file ({len(image_paths)} images). Please download and enjoy!</p>
            <br>
            <p>Best regards,</p>
            <p><b>The FaceSearch AI Team</b></p>
        </body>
        </html>
        """
        msg.attach(MIMEText(html_body, 'html'))

        # 4. Attach the ZIP file
        attachment = MIMEApplication(zip_io.read(), _subtype="zip")
        attachment.add_header('Content-Disposition', 'attachment', filename="FaceSearch_Memories.zip")
        msg.attach(attachment)

        # 5. Send the email using SMTP_SSL for Gmail
        print(f"--- Connecting to Gmail SMTP server {SMTP_SERVER} on port {SMTP_PORT}... ---")
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)

        print(f"--- Successfully sent email to {recipient_email} ---")
        return True

    except Exception as e:
        print(f"--- FAILED to send email to {recipient_email}: {e} ---")
        return False
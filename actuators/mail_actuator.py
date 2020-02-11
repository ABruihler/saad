import smtplib
import getpass

from email.message import EmailMessage

# should initialize the following on startup:

SMTP_SERVER = 'smtp.gmail.com'
SENDER_MAIL = ''
PORT = 465
PASSWORD = ''

def send_email(sender_mail, receiver_mail, message, smtp_server=SMTP_SERVER):
    password = getpass.getpass('Password: ') # temporary / for testing

    msg = EmailMessage()
    msg.set_content(message[1])

    msg['Subject'] = message[0]
    msg['From'] = sender_mail
    msg['To'] = receiver_mail

    server = smtplib.SMTP(smtp_server)
    server.starttls()
    server.login(sender_mail, password)
    server.sendmail(sender_mail, receiver_mail, msg.as_string())
    server.quit()

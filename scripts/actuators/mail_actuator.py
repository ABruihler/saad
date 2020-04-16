import getpass
import smtplib
import sys
from email.message import EmailMessage

# should initialize the following on startup / in config:

SMTP_SERVER = "smtp.gmail.com"
PORT = 465


def send_email(sender_mail, receiver_mail, message, smtp_server=SMTP_SERVER):
    password = getpass.getpass("Password: ")  # temporary / for testing

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


def main():
    sender_mail = sys.argv[1]
    receiver_mail = sys.argv[2]
    message = [sys.argv[3], sys.argv[4]]

    send_email(sender_mail, receiver_mail, message)


if __name__ == "__main__":
    if sys.argv[1] == '-h' or sys.argv[1] == '--help':
        pass
    if sys.argv.__len__() != 5:
        print(
            "Usage: mail_actuator.py [SENDER_EMAIL_ADDRESS] [RECEIVER_EMAIL_ADDRESS] [MESSAGE_SUBJECT] [MESSAGE_BODY]")
    else:
        main()

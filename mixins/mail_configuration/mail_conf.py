# FOR MAIL CONFIGURATION
from django.core.mail import (
    send_mail, EmailMessage, EmailMultiAlternatives
)










class MailSendForDissiminationEmail:
    
    def agromet_bulletin_mail2(mail_conf_dict): 
        subject = mail_conf_dict['subject']
        message = mail_conf_dict['message']
        email_from = mail_conf_dict['email_from']
        recipient_list = mail_conf_dict['recipient_list']
        attachment_path = mail_conf_dict['attachment_path']

        email = EmailMessage(subject, message, email_from, recipient_list)

        if attachment_path:
            # Attach PDF file
            with open(attachment_path, 'rb') as file:
                email.attach_file(attachment_path)

            # If you are sending HTML content, use attach_alternative
            # Example:
            # html_content = "<html><body>Your HTML content</body></html>"
            # email.attach_alternative(html_content, "text/html")

        email.send()

        return True
    
    def agromet_bulletin_mail(mail_conf_dict): 
        subject = mail_conf_dict['subject']
        # message = mail_conf_dict['message']
        context = mail_conf_dict['context']
        email_from = mail_conf_dict['email_from']
        recipient_list = mail_conf_dict['recipient_list']
        attachment_data = mail_conf_dict.get('attachment_data')
        attachment_filename = mail_conf_dict.get('attachment_filename')

        ###### MESSAGE EMAIL 
        # email = EmailMessage(subject, context, email_from, recipient_list)
        # if attachment_data and attachment_filename: 
        #     email.attach(attachment_filename, attachment_data, 'application/pdf')
        # email.send()
        
        ###### HTML EMAIL
        email = EmailMultiAlternatives(subject, "", email_from, recipient_list)
        email.attach_alternative(context, "text/html")
        if attachment_data and attachment_filename:
            email.attach(attachment_filename, attachment_data, 'application/pdf')
        email.send()
        
        return True
    
    

class MailSendToAdmin:
    
    def pending_user_mail(mail_conf_dict): 
        subject = mail_conf_dict['subject']
        message = mail_conf_dict['message']
        email_from = mail_conf_dict['email_from']
        recipient_list = mail_conf_dict['recipient_list']
        send_mail(subject, message, email_from, recipient_list) 

        return True
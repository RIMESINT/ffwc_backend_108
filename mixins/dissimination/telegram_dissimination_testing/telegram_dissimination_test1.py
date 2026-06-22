import telegram
# import asyncio

TELEGRAM_BOT_TOKEN = '7401483566:AAE_rYgXqimcnDAPtzbUZsTsQQ5ClA2NBks'
TELEGRAM_CHANNEL_ID = '-1002282246766'
# TELEGRAM_CHANNEL_ID = '@sesame_adss_test001'

async def send_telegram_message_test(msg, document_path):
    bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
    
    # Sending message
    await bot.send_message(
        chat_id=TELEGRAM_CHANNEL_ID, 
        text=msg
    )
    
    # Sending PDF as a document
    # with open('UCB_Bank.pdf', 'rb') as pdf_file:
    with open(document_path, 'rb') as pdf_file:
        await bot.send_document(
            chat_id=TELEGRAM_CHANNEL_ID, document=pdf_file
        )
    
    # Getting updates
    # updates = await bot.get_updates()
    # print("$$$$$$$$$updates: ", updates)
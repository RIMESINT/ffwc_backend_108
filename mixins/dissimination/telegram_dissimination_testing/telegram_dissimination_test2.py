import asyncio
import telegram

TOKEN = "7401483566:AAE_rYgXqimcnDAPtzbUZsTsQQ5ClA2NBks"
chat_id = '-1002282246766'
# Channel ID Sample: -1001829542722


bot = telegram.Bot(token=TOKEN)

async def send_message(text, chat_id):
    async with bot:
        await bot.send_message(text=text, chat_id=chat_id)


async def send_document(document, chat_id):
    async with bot:
        await bot.send_document(document=document, chat_id=chat_id)


async def send_photo(photo, chat_id):
    async with bot:
        await bot.send_photo(photo=photo, chat_id=chat_id)


async def send_video(video, chat_id):
    async with bot:
        await bot.send_video(video=video, chat_id=chat_id)


async def send_tg_msg_main(cus_msg, cus_pdf_path):
    # Sending a message
    await send_message(
        # text='Hi Raiyan!, How are you?', 
        text=cus_msg, 
        chat_id=chat_id
    )

    # Sending a document
    await send_document(
        # document=open('/home/shaif/Documents/UCB_Bank.pdf', 'rb'), 
        document=cus_pdf_path, 
        chat_id=chat_id
    )

    # Sending a photo
    # await send_photo(
    #     photo=open('/home/shaif/Documents/shaif.png', 'rb'), 
    #     chat_id=chat_id
    # )

    # # Sending a video
    # await send_video(video=open('path/to/video.mp4', 'rb'), chat_id=chat_id)


# if __name__ == '__main__':
#     asyncio.run(send_tg_msg_main(
#         cus_msg= 'Hi Raiyan!, How are you?',
#         cus_pdf_path= '/home/shaif/Documents/UCB_Bank.pdf'
#     ))
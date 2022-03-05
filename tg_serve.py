"""
Bot that prints telegram messages.
"""

import logging
from io import BytesIO
from typing import List, Optional

from PIL import Image
from telegram import Update, PhotoSize
from telegram.ext import CallbackContext, CommandHandler, MessageHandler, Filters, Updater

import db
from citizen_api import citizen_print_msg, NothingToPrint

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(name)s - %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)

MY_CHAT_ID = 143185162


def start(update: Update, context: CallbackContext):
    """ User Sign up. """
    logger.debug(f"{update}{context}")
    user_name = update.effective_user.username
    db.User.create(user_name)
    update.message.reply_text(f"Привет, @{user_name}!\nЗагляни в /help")


def help(update: Update, context: CallbackContext):
    """ Print help. """
    user_name = update.effective_user.username
    msgs_count = db.User.get_msg_count(user_name)
    msg = f"Отправь мне картинку с подписью!\nЯ умею печатать картинки и текст.\nБаланс: `{msgs_count}` сообщений."
    update.message.reply_text(msg)


def download_photo(photo: List[PhotoSize]) -> Optional[Image.Image]:
    """
    Download largest photo from telegram.
    Args:
        photo: photo object
    Returns:
        largest image
    """
    if not photo:
        return None
    target_photo = photo[-1]

    return Image.open(BytesIO(target_photo.get_file().download_as_bytearray()))


def save_and_print_msg(update: Update, context: CallbackContext) -> None:
    """ Save message to database and print it """
    img = download_photo(update.message.photo)
    text = update.message.text or update.message.caption
    user_name = update.effective_user.username
    # print
    citizen_print_msg(text, img, user_name)
    db.User.decrease_messages_count(user_name)
    # save
    db.Message.create(user_name, text, img)


class UnsupportedFormat(NothingToPrint):
    """ Unsupported message format (means bug) """
    pass


def check_input(update: Update, context: CallbackContext):
    """
    Check user input.
    Raises:
        UnsupportedFormat - if anything goes wrong
    """
    user_name = update.effective_user.username
    msgs_count = db.User.get_msg_count(user_name)
    if update.message is None:
        if update.edited_message is not None:  # someone edited msg
            pass
        else:
            update.effective_message.reply_text("Нечего печатать. 😔",
                                                reply_to_message_id=update.effective_message.message_id)
            context.bot.send_message(MY_CHAT_ID, f"Нечего печатать {update}")
        raise UnsupportedFormat
    if msgs_count <= 0:
        logger.debug(f"{update}{context}")
        update.message.reply_text(f"У вас закончились попытки 😕, напишите @zeskbest",
                                  reply_to_message_id=update.message.message_id)
        raise UnsupportedFormat


def respond(update: Update, context: CallbackContext):
    """ Print and echo the user message.  """
    try:
        check_input(update, context)
    except NothingToPrint:
        return
    try:
        save_and_print_msg(update, context)
    except NothingToPrint:
        update.message.reply_text("Нечего печатать. 😔", reply_to_message_id=update.message.message_id)
    else:
        update.message.reply_text("Распечатал! 😃", reply_to_message_id=update.message.message_id)


def error(update: Update, context: CallbackContext):
    """ Log Errors caused by Updates."""
    msg = f"Update caused error\n\n{update}\n\n{context.error}"
    logger.warning(msg)
    context.bot.send_message(MY_CHAT_ID, msg)  # my chat id


def main():
    """
    Start the bot.
    Telegram token required in the "TOKEN" file.
    """
    with open("TOKEN") as f:
        token = f.read().rstrip('\n')
    updater = Updater(token, workers=1, use_context=True)

    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(MessageHandler(Filters.text | Filters.photo, respond))

    dp.add_error_handler(error)
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()

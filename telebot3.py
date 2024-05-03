from telebot import TeleBot
from telebot.types import ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton

import tweepy

import asyncio

# from typing import Final

import logging

from decouple import config


# Configuration for the root logger with a file handler
logging.basicConfig(
    level=logging.INFO,
    filename='logs/logs.log',
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)


# Telegram bot token
# TOKEN: Final = ''
bot = TeleBot(config('TELEGRAM_BOT_TOKEN'))


# Twitter API keys and tokens
TWITTER_CONSUMER_KEY = ''
TWITTER_CONSUMER_SECRET = ''
TWITTER_ACCESS_TOKEN = ''
TWITTER_ACCESS_TOKEN_SECRET = ''


# Initialize Tweepy
client = tweepy.Client(
    consumer_key=TWITTER_CONSUMER_KEY,
    consumer_secret=TWITTER_CONSUMER_SECRET,
    access_token=TWITTER_ACCESS_TOKEN,
    access_token_secret=TWITTER_ACCESS_TOKEN_SECRET
)


# Raid Information Dictionary
raid_info = {}

# List of ids of messages to be deleted
messages_list = []

# Ongoing information request: 'tweet link', 'likes', 'replies', 'retweets', 'bookmarks', 'task'


# Start command
@bot.message_handler(commands=['start'])
def start_command(message):
    bot.reply_to(message, 'Hello! Call me jpegdudebot. How can I be of service?')


# Raid command
@bot.message_handler(commands=['raid'])
def raid_command(message):
    chat_type = message.chat.type
    user_id = message.from_user.id

    if chat_type in ('group', 'supergroup'):
        # Check if the user is permitted to execute command
        chat_member = bot.get_chat_member(message.chat.id, user_id)

        if chat_member.status in ('administrator', 'creator'):
            group_id = message.chat.id

            raid_info[group_id] = {
                'status': 'in_progress',
                'tweet_link': None,
                'likes_threshold': 0,
                'replies_threshold': 0,
                'retweets_threshold': 0,
                'bookmarks_threshold': 0
            }

            # Restrict members from sending messages
            chat_permissions = ChatPermissions(can_send_messages=False)

            bot.set_chat_permissions(message.chat.id, chat_permissions)

            logger.info(f'Group {message.chat.title} is now set locked for /raid command')
            
            tweet_message = bot.send_message(message.chat.id, 'Group locked. Please provide the tweet link.')

            global ongoing 
            
            # Set ongoing as 'tweet link'
            ongoing = 'tweet_link'

            # Add id of tweet message to list so it can be deleted later after user has provided tweet link
            messages_list.append(tweet_message.id)
            
        else:
            logger.info(f'User {message.from_user.username} with {chat_member.status} tried to execute /raid command')

            bot.reply_to(message, 'You do not have permission to use this command.')

            return

    else:
        logger.info(f'User {message.from_user.username} tried to execute /raid command in {chat_type}')

        bot.reply_to(message, 'This command can only be used in a group.')


# Count members command
@bot.message_handler(commands=['count_members'])
def count_members_command(message):
    chat_id = message.chat.id
    
    members_count = bot.get_chat_members_count(chat_id)

    bot.reply_to(message, f'The number of members in this chat is {members_count}.')


# Unlock group
@bot.message_handler(commands=['unlock'])
def unlock_group_command(message):
    # Restrict members from sending messages
    chat_permissions = ChatPermissions(can_send_messages=True)

    bot.set_chat_permissions(message.chat.id, chat_permissions)

    logger.info(f'Group {message.chat.title} is now set unlocked for /raid command')

    bot.send_message(message.chat.id, 'Group has been unlocked!')


@bot.message_handler(commands=['try_callback'])
def send_inline_keyboard(message):
    # Create inline keyboard
    inline_keyboard = InlineKeyboardMarkup()
    button = InlineKeyboardButton("Try Callback", callback_data="try_callback")
    inline_keyboard.add(button)

    # Send message with inline keyboard
    message = bot.send_message(message.chat.id, "Press the button below to try callback:", reply_markup=inline_keyboard)


@bot.callback_query_handler(lambda call: call.data == 'try_callback')
def handle_callback_query(call):
    print ('Tries')

    if call.data == "try_callback":
        # Edit the previous message's inline keyboard
        updated_inline_keyboard = InlineKeyboardMarkup()
        button = InlineKeyboardButton("Try Callback Again", callback_data="try_callback_again")
        updated_inline_keyboard.add(button)

        bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=updated_inline_keyboard)
    elif call.data == "try_callback_again":
        bot.answer_callback_query(call.id, "You pressed Try Callback Again")


# Handling incoming text messages
@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_message(message):
    print ('Tries2')
    chat_type = message.chat.type
    
    text = message.text

    if chat_type in('group', 'supergroup'):
        group_id = message.chat.id

        if group_id in raid_info and raid_info[group_id]['status'] == 'in_progress':
            try:                
                if ongoing == 'tweet link':
                    if 'x.com' in text:
                        raid_info[group_id]['tweet_link'] = text

                        # Delete the tweet message and tweet link
                        bot.delete_message(message.chat.id, messages_list.pop())
                        bot.delete_message(message.chat.id, message.id)
                        
                        likes_message = bot.send_message(message.chat.id, 'Please provide the number of likes needed:')

                        ongoing = 'likes'

                        messages_list.append(likes_message.id)

                    else:
                        bot.send_message(message.chat.id, 'This appears to be a wrong link. Please enter the correct tweet link')

                        return

                elif ongoing == 'likes':
                    raid_info[group_id]['likes_threshold'] = int(text)

                    bot.delete_message(message.chat.id, messages_list.pop())
                    bot.delete_message(message.chat.id, message.id)

                    replies_message = bot.send_message(message.chat.id, 'Please provide number of replies needed:')

                    ongoing = 'replies'

                    messages_list.append(replies_message.id)

                elif ongoing == 'replies':
                    raid_info[group_id]['replies_threshold'] = int(text)

                    bot.delete_message(message.chat.id, messages_list.pop())
                    bot.delete_message(message.chat.id, message.id)

                    retweets_message = bot.send_message(message.chat.id, 'Please provide number of retweets needed:')

                    ongoing = 'retweets'

                    messages_list.append(retweets_message.id)

                elif ongoing == 'retweets':
                    raid_info[group_id]['retweets_threshold'] = int(text)

                    bot.delete_message(message.chat.id, messages_list.pop())
                    bot.delete_message(message.chat.id, message.id)

                    bookmarks_message = bot.send_message(message.chat.id, 'Please provide number of bookmarks needed:')

                    ongoing = 'bookmarks'

                    messages_list.append(bookmarks_message.id)

                elif ongoing == 'bookmarks':
                    raid_info[group_id]['bookmarks_threshold'] = int(text)

                    bot.delete_message(message.chat.id, messages_list.pop())
                    bot.delete_message(message.chat.id, message.id)

                    task_message = bot.send_message(message.chat.id, 'Twitter tasks will be performed. Please wait...')

                    ongoing = 'task'

                    messages_list.append(task_message.id)

                    asyncio.run(perform_twitter_tasks(message.chat.id))

                else:
                    return 
            
            except ValueError:
                bot.reply_to(message, 'It seems like you have entered an incorrect value. Please type the correct value to proceed.')

        else:
            return
        
    else:
        # TODO: Define handle_response function
        # response = handle_response(text)

        # print('Bot:', response)

        return



# Perform Twitter Tasks
async def perform_twitter_tasks(group_id):
    while True:
        try:
            # Get tweet details
            tweet_link = raid_info[group_id]['tweet_link']
            tweet_id = tweet_link.split('/')[-1].split('?')[0]
            tweet = client.get_tweet(tweet_id, tweet_fields='public_metrics')

            # Get metrics
            likes = tweet.public_metrics['like_count']
            replies = tweet.public_metrics['reply_count']
            retweets = tweet.public_metrics['retweet_count']
            bookmarks = tweet.public_metrics['bookmark_count']

            # Check if thresholds are reached
            if (
                likes >= raid_info[group_id]['likes_threshold'] and
                replies >= raid_info[group_id]['replies_threshold'] and
                retweets >= raid_info[group_id]['retweets_threshold'] and
                bookmarks >= raid_info[group_id]['bookmarks_threshold']
            ):
                raid_info[group_id]['status'] = 'completed'

                bot.send_message(group_id, 'Mission complete. Group unlocked.')

                break

            else:
                # Reply with processing status
                bot.send_message(
                    group_id,
                    f'Twitter tasks in progress - Likes: {likes}, Replies: {replies}, Retweets: {retweets}, Bookmarks: {bookmarks}'
                )
                
            # Continue running after 60 seconds
            await asyncio.sleep(60)

        except Exception as e:
            logger.error(f"Error performing Twitter tasks: {e}")

            bot.send_message(group_id, 'Error performing Twitter tasks. Please try again.')

            break

if __name__ == '__main__':
    bot.infinity_polling(restart_on_change=True, allowed_updates=['message', 'callback_query'])

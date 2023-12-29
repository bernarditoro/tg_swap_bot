from telebot import TeleBot as TB
from telebot.types import ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton

import tweepy

import asyncio

# from typing import Final

import logging

from decouple import config


# Configuration for the root logger with a file handler
logging.basicConfig(
    level=logging.INFO,
    filename='logs.log',
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)


# Telegram bot token
# TOKEN: Final = ''


class DemoTeleBot(TB):
    def __init__(self, token):
        super().__init__(token)

        # Register message handler
        self.register_message_handlers()

    
    # Twitter API keys and tokens
    TWITTER_BEARER_TOKEN = ''

    # Initialize Tweepy
    client = tweepy.Client(TWITTER_BEARER_TOKEN)

    # Raid Information Dictionary
    raid_info = {}

    # List of ids of messages to be deleted
    messages_list = []

    # Ongoing information request: 'tweet link', 'likes', 'replies', 'retweets', 'bookmarks', 'task'
    ongoing = ''

    def register_message_handlers(self):
        # Start command
        @self.message_handler(commands=['start'])
        def start_command(message):
            keyboard = InlineKeyboardMarkup()
            command_button = InlineKeyboardButton(text='Raid', callback_data='raid')
            keyboard.add(command_button)

            self.send_message(message.chat.id, "Hello! Call me jpegdudebot. How can I be of service?", reply_markup=keyboard)

        # Raid command
        @self.message_handler(commands=['raid'])
        @self.callback_query_handler(func=lambda call: call.data == 'raid')
        def raid_command(message):
            chat_type = message.chat.type
            user_id = message.from_user.id

            if chat_type in ('group', 'supergroup'):
                # Check if the user is permitted to execute command
                chat_member = self.get_chat_member(message.chat.id, user_id)

                if chat_member.status in ('administrator', 'creator'):
                    group_id = message.chat.id

                    self.raid_info[group_id] = {
                        'status': 'in_progress',
                        'tweet_link': None,
                        'likes_threshold': 0,
                        'replies_threshold': 0,
                        'retweets_threshold': 0,
                        'bookmarks_threshold': 0
                    }

                    # Restrict members from sending messages
                    chat_permissions = ChatPermissions(can_send_messages=False)

                    self.set_chat_permissions(message.chat.id, chat_permissions)

                    logger.info(f'User {message.from_user.username} with {chat_member.status} status executed /raid command')

                    logger.info(f'Group {message.chat.title} is now set locked for /raid command')
                    
                    tweet_message = self.send_message(message.chat.id, 'Group locked. Please provide the tweet link.')
                    
                    # Set ongoing as 'tweet link'
                    self.ongoing = 'tweet_link'

                    # Add id of tweet message to list so it can be deleted later after user has provided tweet link
                    self.messages_list.append(tweet_message.id)
                    
                else:
                    logger.info(f'User {message.from_user.username} with {chat_member.status} tried to execute /raid command')

                    self.reply_to(message, 'You do not have permission to use this command.')

                    return

            else:
                logger.info(f'User {message.from_user.username} tried to execute /raid command in {chat_type}')

                self.reply_to(message, 'This command can only be used in a group.')

        # Count members command
        @self.message_handler(commands=['count_members'])
        def count_members_command(message):
            chat_id = message.chat.id
            
            members_count = self.get_chat_members_count(chat_id)

            self.reply_to(message, f'The number of members in this chat is {members_count}.')

        # End raid and unlock group
        @self.message_handler(commands=['end'])
        def unlock_group_command(message):
            chat_permissions = ChatPermissions(can_send_messages=True,
                                               can_send_media_messages=True,
                                               can_send_other_messages=True,
                                               can_send_polls=True)

            self.set_chat_permissions(message.chat.id, chat_permissions)

            logger.info(f'Group {message.chat.title} is now set unlocked and /raid command exited')

            self.send_message(message.chat.id, 'Group has been unlocked!')

        # Handling incoming text messages
        @self.message_handler(func=lambda message: True, content_types=['text'])
        def handle_message(message):
            chat_type = message.chat.type
            
            text = message.text

            if chat_type in('group', 'supergroup'):
                group_id = message.chat.id

                if group_id in self.raid_info and self.raid_info[group_id]['status'] == 'in_progress':
                    try:
                        if self.ongoing == 'tweet_link':
                            if 'x.com' in text:
                                self.raid_info[group_id]['tweet_link'] = text

                                # Delete the tweet message and tweet link
                                self.delete_message(message.chat.id, message.id)
                                self.delete_message(message.chat.id, self.messages_list.pop())
                                
                                likes_message = self.send_message(message.chat.id, 'Please provide the number of likes needed:')

                                self.ongoing = 'likes'

                                self.messages_list.append(likes_message.id)

                            else:
                                self.send_message(message.chat.id, 'This appears to be a wrong link. Please enter the correct tweet link')

                                return

                        elif self.ongoing == 'likes':
                            self.raid_info[group_id]['likes_threshold'] = int(text)

                            self.delete_message(message.chat.id, message.id)
                            self.delete_message(message.chat.id, self.messages_list.pop())

                            replies_message = self.send_message(message.chat.id, 'Please provide number of replies needed:')

                            self.ongoing = 'replies'

                            self.messages_list.append(replies_message.id)

                        elif self.ongoing == 'replies':
                            self.raid_info[group_id]['replies_threshold'] = int(text)

                            self.delete_message(message.chat.id, message.id)
                            self.delete_message(message.chat.id, self.messages_list.pop())

                            retweets_message = self.send_message(message.chat.id, 'Please provide number of retweets needed:')

                            self.ongoing = 'retweets'

                            self.messages_list.append(retweets_message.id)

                        elif self.ongoing == 'retweets':
                            self.raid_info[group_id]['retweets_threshold'] = int(text)

                            self.delete_message(message.chat.id, message.id)
                            self.delete_message(message.chat.id, self.messages_list.pop())

                            bookmarks_message = self.send_message(message.chat.id, 'Please provide number of bookmarks needed:')

                            self.ongoing = 'bookmarks'

                            self.messages_list.append(bookmarks_message.id)

                        elif self.ongoing == 'bookmarks':
                            self.raid_info[group_id]['bookmarks_threshold'] = int(text)

                            self.delete_message(message.chat.id, message.id)
                            self.delete_message(message.chat.id, self.messages_list.pop())

                            task_message = self.send_message(message.chat.id, 'Twitter tasks will be performed. Please wait...')

                            self.ongoing = 'task'

                            self.messages_list.append(task_message.id)

                            asyncio.run(self.perform_twitter_tasks(message.chat.id))

                        else:
                            return 
                    
                    except ValueError:
                        self.reply_to(message, 'It seems like you have entered an incorrect value. Please type the correct value to proceed.')

                else:
                    return
                
            else:
                # TODO: Define handle_response function
                # response = handle_response(text)

                # print('Bot:', response)

                return

    # Perform Twitter Tasks
    async def perform_twitter_tasks(self, group_id):
        while True:
            try:
                # Get tweet details
                tweet_link = self.raid_info[group_id]['tweet_link']
                tweet_id = tweet_link.split('/')[-1].split('?')[0]
                tweet = self.client.get_tweet(tweet_id, tweet_fields='public_metrics')

                # Get metrics
                likes = tweet.public_metrics['like_count']
                replies = tweet.public_metrics['reply_count']
                retweets = tweet.public_metrics['retweet_count']
                bookmarks = tweet.public_metrics['bookmark_count']

                # Check if thresholds are reached
                if (
                    likes >= self.raid_info[group_id]['likes_threshold'] and
                    replies >= self.raid_info[group_id]['replies_threshold'] and
                    retweets >= self.raid_info[group_id]['retweets_threshold'] and
                    bookmarks >= self.raid_info[group_id]['bookmarks_threshold']
                ):
                    self.raid_info[group_id]['status'] = 'completed'

                    # Unlock group
                    chat_permissions = ChatPermissions(can_send_messages=True)
                    self.set_chat_permissions(group_id, chat_permissions)

                    self.send_message(group_id, 'Mission complete. Group unlocked.')

                    break

                else:
                    # Reply with processing status
                    self.send_message(
                        group_id,
                        f'Twitter tasks in progress - Likes: {likes}, Replies: {replies}, Retweets: {retweets}, Bookmarks: {bookmarks}'
                    )
                    
                # Continue running after 60 seconds
                await asyncio.sleep(60)

            except Exception as e:
                logger.error(f"Error performing Twitter tasks: {e}")

                self.send_message(group_id, 'Error performing Twitter tasks. Please try again.')

                break

if __name__ == '__main__':
    bot = DemoTeleBot(config('TELEGRAM_BOT_TOKEN'))

    bot.polling(none_stop=True, interval=0, timeout=20, allowed_updates=['message'])

from telebot import TeleBot as TB
from telebot.types import ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton
from telebot.util import quick_markup

import tweepy

import asyncio

# from typing import Final

import logging

from decouple import config

import requests


# Configuration for the root logger with a file handler
logging.basicConfig(
    level=logging.INFO,
    filename='logs.log',
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)


class DemoTeleBot(TB):
    def __init__(self, token):
        super().__init__(token)

        # Register message handler
        self.register_message_handlers()
    
    # Twitter API keys and tokens
    TWITTER_BEARER_TOKEN = config('TWITTER_BEARER_TOKEN')

    ETHERSCAN_KEY_TOKEN = config('ETHERSCAN_KEY_TOKEN')

    # Initialize Tweepy
    client = tweepy.Client(TWITTER_BEARER_TOKEN)

    etherscan_base_url = 'https://api.etherscan.io/api'

    # Raid Information Dictionary
    raid_info = {}

    # List of ids of messages to be deleted
    messages_list = []

    # Ongoing information request: 'tweet link', 'likes', 'replies', 'retweets', 'bookmarks', 'task', 'tnx_validation'
    ongoing = ''

    # This field tracks if the bot is currently on a raid or not
    is_raiding = False

    # Transaction details
    tnx_details = {}

    def register_message_handlers(self):
        # Start command
        @self.message_handler(commands=['start'])
        def start_command(message):
            keyboard = InlineKeyboardMarkup()
            command_button = InlineKeyboardButton(text='Perform Raid', callback_data='raid')
            keyboard.add(command_button)

            markup = quick_markup({
                'Advertise': {'callback_data': 'advertise'}
            }, row_width=1)

            text = """Hi there! I am jpegdude! Here is how you can utilise my functions:\n
1\u20e3 Add @a_demo_telebot to your Telegram group
2\u20e3 Make the bot an admin.
3\u20e3 Only admins can run the Bot
4\u20e3 To Start A Raid:
    - Enter /raid (the group is set locked until the raid is completed or ended)
    - Follow on-screen prompts
    - Enter /end to force stop current raid and unlock the group

5\u20e3 For advertisement packages, enter /advertise."""

            self.send_message(message.chat.id, text)

        # Raid command
        @self.message_handler(commands=['raid'])
        def raid_command(message):
            chat_type = message.chat.type
            user_id = message.from_user.id

            if chat_type in ('group', 'supergroup'):
                # Check if the user is permitted to execute command
                chat_member = self.get_chat_member(message.chat.id, user_id)

                if chat_member.status in ('administrator', 'creator'):
                    if not self.is_raiding:
                        self.is_raiding = True

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
                        self.send_message(message.chat.id, 'Raid currently ongoing. Please /end raid to start another raid.')
                    
                else:
                    logger.info(f'User {message.from_user.username} with {chat_member.status} status tried to execute /raid command')

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
            if self.is_raiding:
                # Clear all raid info
                self.raid_info.clear()

                self.is_raiding = False

                self.ongoing = ''

                chat_permissions = ChatPermissions(can_send_messages=True,
                                                   can_send_media_messages=True,
                                                   can_send_other_messages=True,
                                                   can_send_polls=True)

                self.set_chat_permissions(message.chat.id, chat_permissions)

                logger.info(f'User {message.from_user.username} executed the /end command')

                logger.info(f'Group {message.chat.title} is now set unlocked and /raid command exited')

                self.send_message(message.chat.id, 'Raid has been cancelled and group has been unlocked!')

            else:
                self.send_message(message.chat.id, 'There is no raid currently.')

        # Validate eth tnx
        @self.callback_query_handler(func=lambda call: True)
        def validate_transaction_command(call):
            print ('Executed!')

            if self.is_raiding and call.data == 'validate':
                message = call.message

                print('This is the message: ', message)

                self.ongoing = 'tnx_validation'

                self.send_message(message.chat.id, 'Please provide your transaction hash.')
            
        # Handling incoming text messages
        @self.message_handler(func=lambda message: True, content_types=['text'])
        def handle_message(message):
            chat_type = message.chat.type
            
            text = message.text

            if chat_type in('group', 'supergroup'):
                group_id = message.chat.id

                if self.is_raiding and group_id in self.raid_info and self.raid_info[group_id]['status'] == 'in_progress':
                    try:
                        if self.ongoing == 'tweet_link':
                            if text.strip().startswith('https://x.com') or text.strip().startswith('https://twitter.com'):
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

                            # markup = quick_markup({
                            #     'Validate': {'callback_data': 'validate'}
                            # }, row_width=1)

                            markup = InlineKeyboardMarkup().row(InlineKeyboardButton('Validate Payment', callback_data='validate'))

                            task_message = self.send_message(message.chat.id, 'Group locked. Please transfer a token of 0.13ETH to this ' +
                                           'address:\n\n *0x3fc91a3afd70395cd496c647d5a6cc9d4b2b7fad*\n\n After you\'re done, click validate ' +
                                           'or reply with the transaction hash to confirm the transfer and proceed with the raid.', parse_mode='Markdown', reply_markup=markup)

                            self.ongoing = 'tx_validation'

                            self.messages_list.append(task_message.id)

                            # asyncio.run(self.perform_twitter_tasks(message.chat.id))

                        elif self.ongoing == 'tx_validation':
                            self.send_message(message.chat.id, 'Please hold on while your transaction is confirmed.')

                            asyncio.run(self.validate_transaction_task(message.chat.id, text.strip()))

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
        while True and self.is_raiding:
            try:
                # Get tweet details
                tweet_link = self.raid_info[group_id]['tweet_link']
                tweet_id = tweet_link.split('/')[-1].split('?')[0]
                response = self.client.get_tweet(tweet_id, tweet_fields=['public_metrics'])
                tweet = response.data

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
                    chat_permissions = ChatPermissions(can_send_messages=True,
                                                       can_send_media_messages=True,
                                                       can_send_other_messages=True,
                                                       can_send_polls=True)
                    self.set_chat_permissions(group_id, chat_permissions)

                    self.is_raiding = False
                    
                    self.send_message(group_id, 'Raid complete. Group has been unlocked.')

                    break

                else:
                    text = f"""*RAID IN PROGRESS*\n
*Tweet link:* {self.raid_info[group_id]['tweet_link']}\n
*Current likes:* {likes} | \U0001f3af {self.raid_info[group_id]['likes_threshold']}
*Current replies:* {replies} | \U0001f3af {self.raid_info[group_id]['replies_threshold']}
*Current reposts:* {retweets} | \U0001f3af {self.raid_info[group_id]['retweets_threshold']}
*Current bookmarks:* {bookmarks} | \U0001f3af {self.raid_info[group_id]['bookmarks_threshold']}"""
                    
                    advertisement_markup = quick_markup({
                        'Sample Advertisement': {'url': 'sample.com'}
                    })

                    # Reply with processing status
                    self.send_message(group_id, text, parse_mode='Markdown', reply_markup=advertisement_markup, disable_web_page_preview=True)
                    
                # Continue running after 60 seconds
                await asyncio.sleep(60)

            except Exception as e:
                logger.error(f'Error performing Twitter tasks: {e}')

                self.is_raiding = False

                self.send_message(group_id, 'Error performing Twitter tasks. Please try again.')

                break

    # Validate eth tnx
    async def validate_transaction_task(self, group_id, tx_hash):
        # Connect to etherscan api and get transaction details
        params = {
            'module': 'proxy',
            'action': 'eth_getTransactionByHash',
            'txhash': tx_hash,
            'apikey': self.ETHERSCAN_KEY_TOKEN
        }

        try:
            response = requests.get(self.etherscan_base_url, params=params)
            result = response.json()

            if result.get('status', '1') == '1' or result.get('error', True):
                transaction = result['result']

                sender_address = transaction['from']
                recipient_address = transaction['to']
                eth_amount_wei = int(transaction['value'], 16)  # Amount in wei
                eth_amount = eth_amount_wei / 1e18  # Convert wei to ETH

                print (eth_amount, recipient_address)

                if eth_amount >= 0.13 and recipient_address == '0x3fc91a3afd70395cd496c647d5a6cc9d4b2b7fad':
                    logger.info(f'Transaction of {eth_amount} from {sender_address} to {recipient_address} was successfully validated.')

                    self.send_message(group_id, 'Payment has been validated. Twitter raid will now be performed.')

                    self.ongoing = 'task'

                    await self.perform_twitter_tasks(group_id)

                else:
                    logger.info(f'Transaction with hash {tx_hash} could not be validated.')

                    self.send_message(group_id, f'Transaction with hash {tx_hash} could not be validated. Please check your transaction hash and try again.')

            else:
                logger.info(f'Error retrieving transaction details with hash {tx_hash}')

                self.send_message(group_id, 'It seems the transaction hash is incorrect. Could you try again with a correct transaction hash?')

        except Exception as e:
            logger.info(f'Error retrieving transaction details of hash {tx_hash}: {e}')

            self.send_message(group_id, 'Transaction could not be verified! Please check your transaction hash and try again.')

if __name__ == '__main__':
    bot = DemoTeleBot(config('TELEGRAM_BOT_TOKEN'))

    bot.polling(none_stop=True, interval=0, allowed_updates=['message'])

from telebot import TeleBot as TB
from telebot.types import ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton
from telebot.util import quick_markup

import tweepy

import asyncio

from asgiref.sync import sync_to_async

# from typing import Final

import logging

from decouple import config

import requests

from web3 import Web3

import os

import django
from django.db import IntegrityError

# Set the DJANGO_SETTINGS_MODULE environment variable
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jpegdude.settings')

# Configure Django
django.setup()

from swaps.swap import swap_eth_for_tokens
from swaps.models import Swap


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

    WALLET_ADDRESS = config('WALLET_ADDRESS')

    # Initialize Tweepy
    client = tweepy.Client(TWITTER_BEARER_TOKEN)

    etherscan_base_url = 'https://api-goerli.etherscan.io/api' #TODO: Remove the -goerli before prod

    # Raid Information Dictionary
    raid_info = {}

    # List of ids of messages to be deleted
    messages_list = []

    # Ongoing information request: 'tweet link', 'likes', 'replies', 'retweets', 'bookmarks', 'task', 'tnx_validation'
    ongoing = ''

    # This field tracks if the bot is currently on a raid or not
    is_raiding = False

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
                            'bookmarks_threshold': 0,

                            'dev_wallet_address': '',
                            'token_address': '',
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
            if self.is_raiding and call.data == 'validate':
                message = call.message

                print('This is the message: ', message)

                self.ongoing = 'tnx_validation'

                self.send_message(message.chat.id, 'Please provide your transaction hash.')
            
        # Handling incoming text messages
        @self.message_handler(func=lambda message: True, content_types=['text'])
        def handle_message(message):
            chat_type = message.chat.type

            text = message.text.strip()

            # print(f'{message.from_user.username} said: {text}')

            if chat_type in ('group', 'supergroup'):
                group_id = message.chat.id

                if self.is_raiding and group_id in self.raid_info and self.raid_info[group_id]['status'] == 'in_progress':
                    try:
                        if self.ongoing == 'tweet_link':
                            if text.startswith('https://x.com') or text.startswith('https://twitter.com'):
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

                            self.delete_message(group_id, message.id)
                            self.delete_message(group_id, self.messages_list.pop())

                            self.send_message(group_id, 'Now to the details for the buyback')
                            self.send_message(group_id, 'Please provide your wallet address')

                            self.ongoing = 'wallet_address'

                        elif self.ongoing == 'wallet_address':
                            if text.startswith('0x'):
                                self.raid_info[group_id]['dev_wallet_address'] = text

                                self.send_message(group_id, 'Please provide the token address for the token you want to swap')

                                self.ongoing = 'token_address'

                            else:
                                self.reply_to(message, 'Please enter a correct address.')

                        elif self.ongoing == 'token_address':
                            if text.startswith('0x'):
                                self.raid_info[group_id]['token_address'] = text

                                reply = f"""Do you want to swap ETH from *{self.raid_info[group_id]['dev_wallet_address']}* to token with token address: *{text}*?
                            
Reply with _Yes_ to proceed, _Edit_ to edit your swap details, or /end to cancel the swap."""

                                self.send_message(group_id, reply, parse_mode='Markdown')

                                self.ongoing = 'swap_confirmation'
                            
                            else:
                                self.reply_to(message, 'Please enter a correct address.')
                        
                        elif self.ongoing == 'swap_confirmation':

                            text = text.lower()

                            if text == 'yes':

                                markup = InlineKeyboardMarkup().row(InlineKeyboardButton('Validate Payment', callback_data='validate'))

                                reply = f"""Please transfer the amount of ETH you want to swap to this address:

*{self.WALLET_ADDRESS}*

Please ensure that you send the amount from the wallet address you entered earlier. After sending, click validate or reply \
with the transaction hash to confirm the transfer and proceed with the raid."""

                                self.send_message(group_id, reply, parse_mode='Markdown', reply_markup=markup)
                                
                                self.ongoing = 'tx_validation'

                            elif text == 'edit':
                                self.send_message(group_id, 'Please provide your wallet address')

                                self.ongoing = 'wallet_address'

                            else:
                                self.send_message(group_id, 'Please reply with _Yes_ to proceed, _Edit_ to edit your swap details, or /end to cancel the swap.')

                        elif self.ongoing == 'tx_validation':
                            self.send_message(group_id, 'Please hold on while your transaction is confirmed.')

                            asyncio.run(self.validate_transaction_task(group_id, text))

                        else:
                            return 
                    
                    except ValueError:
                        self.reply_to(message, 'It seems like you have entered an incorrect value. Please type the correct value to proceed.')

                    # finally:
                        # unlock_group_command(message)
                        
                else:
                    return
                
            else:
                # TODO: Define handle_response function
                # response = handle_response(text)

                # print('Bot:', response)

                return

    # Perform Twitter Tasks
    async def perform_twitter_tasks(self, group_id):
        raid_group = self.raid_info[group_id]

        likes_required = raid_group['likes_threshold']
        replies_required = raid_group['replies_threshold']
        retweets_required = raid_group['retweets_threshold']
        bookmarks_required = raid_group['bookmarks_threshold']
        tweet_link = raid_group['tweet_link']

        # Send message to trends group
#         message = f"""*The jpegdude bot has been activated by --.* The target is {likes_required} likes,
# {replies_required} replies, {retweets_required} retweets, {bookmarks_required} bookmarks. Help them
# achieve their goal here:

# {tweet_link}"""
        
#         try:
#             self.send_message(config('TRENDS_GROUP_ID', cast=int), message, parse_mode='Markdown')

#         except Exception as e:
#             logger.error(f'Error while sending raid info to trends group: {e}')

        while self.is_raiding:
            try:
                # Get tweet details
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
                    likes >= likes_required and
                    replies >= replies_required and
                    retweets >= retweets_required and
                    bookmarks >= bookmarks_required
                ):
                    raid_group['status'] = 'completed'

                    # Unlock group
                    self.unlock_group_command(group_id)

                    break

                else:
                    text = f"""*RAID IN PROGRESS*\n
*Tweet link:* {tweet_link}\n
*Current likes:* {likes} | \U0001f3af {likes_required}
*Current replies:* {replies} | \U0001f3af {replies_required}
*Current reposts:* {retweets} | \U0001f3af {retweets_required}
*Current bookmarks:* {bookmarks} | \U0001f3af {bookmarks_required}

[Jpegdude Trending]({self.get_chat(config('TRENDS_GROUP_ID').invite_link)})"""
                    
                    advertisement_markup = quick_markup({
                        'Sample Advertisement': {'url': '#'}
                    })

                    # Reply with processing status
                    self.send_message(group_id, text, parse_mode='Markdown', reply_markup=advertisement_markup, disable_web_page_preview=True)
                    
                # Continue running after 60 seconds
                await asyncio.sleep(60)

            except Exception as e:
                logger.error(f'Error performing Twitter tasks: {e}')

                self.send_message(group_id, 'Error performing Twitter tasks. Please try again.')

                self.unlock_group_command(group_id)

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
                eth_amount = Web3.from_wei(eth_amount_wei, 'ether')  # Convert wei to ETH

                logger.info(f'Transaction of {eth_amount} from {sender_address} to {recipient_address} was successfully validated.')

                if (Web3.to_checksum_address(sender_address) == Web3.to_checksum_address(self.raid_info[group_id]['dev_wallet_address']) and
                    Web3.to_checksum_address(recipient_address) == Web3.to_checksum_address(self.WALLET_ADDRESS)):
                    # Create swap record 
                    self.swap = await Swap.objects.aget_or_create(destination_address=sender_address,
                                                                  token_address=self.raid_info[group_id]['token_address'],
                                                                  origin_hash=tx_hash,
                                                                  is_successful=False)
                    
                    self.send_message(group_id, 'Transfer has been validated. Please wait while the buyback is executed.')

                    hash, receipt_status = await self.perform_swap(tx_hash, group_id, eth_amount)

                    if receipt_status == 1:
                        # If transaction was successful
                        self.send_message(group_id, f'Swap with transaction hash *{hash}* was successful!\n\nTwitter raid will now be performed.', parse_mode='Markdown')

                        self.ongoing = 'task'

                        await self.perform_twitter_tasks(group_id)

                    else:
                        self.send_message(group_id, f'Swap with transaction hash *{hash}* could not be completed!', parse_mode='Markdown')

                else:
                    logger.info(f'Transaction with hash {tx_hash} could not be validated due to unmatching variables.')

                    self.send_message(group_id, f'Transaction with hash {tx_hash} could not be validated. Please check your transaction hash and try again.')

            else:
                logger.error(f'Error retrieving transaction details with hash {tx_hash}')

                self.send_message(group_id, 'It seems the transaction hash is incorrect. Could you try again with a correct transaction hash?')

        except IntegrityError as e:
            logger.error(f'Error creating a swap record: {e}')

            self.send_message(group_id, 'It seems this transaction hash has been used to process a swap before. Please reach out to an admin for further assistance.')

        except Exception as e:
            logger.error(f'Error retrieving transaction details of hash {tx_hash}: ({type(e)}, {e}')

            print(e)

            self.send_message(group_id, 'Transaction could not be verified! Please check your transaction hash and try again.')

    async def perform_swap(self, origin_hash, group_id, eth_amount):
        recipient_address = self.raid_info[group_id]['dev_wallet_address']
        token_address = self.raid_info[group_id]['token_address']

        hash, receipt_status = await sync_to_async(swap_eth_for_tokens)(origin_hash, recipient_address, token_address, eth_amount)

        return hash, receipt_status

    def unlock_group_command(self, group_id):
        if self.is_raiding:
            # Clear all raid info
            self.raid_info.clear()

            self.is_raiding = False

            self.ongoing = ''

            chat_permissions = ChatPermissions(can_send_messages=True,
                                               can_send_media_messages=True,
                                               can_send_other_messages=True,
                                               can_send_polls=True)

            self.set_chat_permissions(group_id, chat_permissions)

            self.send_message(group_id, 'Raid has been cancelled and group has been unlocked!')

        else:
            self.send_message(group_id, 'There is no raid currently.')


if __name__ == '__main__':
    bot = DemoTeleBot(config('TELEGRAM_BOT_TOKEN'))

    bot.polling(none_stop=True, interval=0, allowed_updates=['message'])

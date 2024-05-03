from telebot import TeleBot as TB
from telebot.types import ChatPermissions
from telebot.util import quick_markup

import tweepy

import asyncio

import logging

from decouple import config

import requests

from web3 import Web3

from datetime import datetime, timedelta

import validators


# Configuration for the root logger with a file handler
logging.basicConfig(
    level=logging.INFO,
    filename='logs/logs.log',
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

    etherscan_base_url = 'https://api-sepolia.etherscan.io/api' #TODO: Remove the -goerli before prod

    # Raid Information Dictionary
    raid_info = {}

    ad_info = {}

    ad_prices = {
        # 'number_of_days': 'price'
        '2': 0.3,
        '3': 0.5,
        '4': 0.65
    }

    # List of ids of messages to be deleted
    messages_list = []

    # Ongoing information request: 'tweet link', 'likes', 'replies', 'retweets', 'bookmarks', 'task', 'tnx_validation'
    ongoing = ''

    # This field tracks if the bot is currently on a raid or not
    is_raiding = False

    is_registering_ad = False

    backend_url = config('BACKEND_APP_URL', cast=str)

    def register_message_handlers(self):
        # Start command
        @self.message_handler(commands=['start'])
        def start_command(message):
            ad = requests.get(f'{self.backend_url}/ads/get-random/').json()
            
            markup = quick_markup({
                ad['ad_text']: {'url': ad['external_link']}
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

            self.send_message(message.chat.id, text, reply_markup=markup)

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
        
        # Cancel ad
        @self.message_handler(commands=['cancel'])
        def cancel_ad(message):
            if self.is_registering_ad:
                self.ad_info.clear()

                self.ongoing = ''

                self.is_registering_ad = False

                self.send_message(message.chat.id, 'Ad has been cancelled. Tap /advertise to start a new ad or continue with an uncompleted ad')

            else:
                self.send_message(message.chat.id, 'There is no ad to cancel')

        @self.message_handler(commands=['advertise'])
        def advertise(message):
            if message.chat.type.lower() == 'private':
                markup = quick_markup({
                    '2 Days: 0.3ETH': {'callback_data': '2_days_ad'},
                    '3 Days: 0.5ETH': {'callback_data': '3_days_ad'},
                    '4 Days: 0.65ETH': {'callback_data': '4_days_ad'},
                }, row_width=1)

                reply = """Get your project on Jpegdude bot Trending!

Your project will be displayed in the trending group for the selected duration:"""

                self.send_message(message.chat.id, reply, reply_markup=markup)

            else:
                self.send_message(message.chat.id, 'This command can only be used in a private chat')

        @self.callback_query_handler(func=lambda call: True)
        def handle_callback_queries(call):
            chat_id = call.message.chat.id

            text = call.data

            if 'days_ad' in text:
                self.ad_info[chat_id] = {
                    'number_of_days': None,
                    'username': None,
                    'ad_text': None,
                    'link': None
                }

                number_of_days = text[0]

                self.ad_info[chat_id]['number_of_days'] = int(number_of_days)

                message = self.send_message(chat_id, 'Please enter your username so we can contact you')
                self.messages_list.append(message.id)

                self.ongoing = 'ad_username'

                self.is_registering_ad = True

                return

                # updated_inline_keyboard = InlineKeyboardMarkup()
                # button = InlineKeyboardButton("Try Callback Again", callback_data="try_callback_again")
                # updated_inline_keyboard.add(button)

                # self.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=updated_inline_keyboard)
        
        # Handling incoming text messages
        @self.message_handler(func=lambda message: True, content_types=['text'])
        def handle_message(message):
            chat_type = message.chat.type

            text = message.text.strip()

            chat_id = message.chat.id

            def delete_messages(message):
                # Delete the tweet message and tweet link
                self.delete_message(chat_id, message.id)
                self.delete_message(chat_id, self.messages_list.pop())

            # print(f'{message.from_user.username} said: {text}')

            if chat_type in ('group', 'supergroup'):
                if self.is_raiding and chat_id in self.raid_info and self.raid_info[chat_id]['status'] == 'in_progress':
                    try:
                        if self.ongoing == 'tweet_link':
                            if text.startswith('https://x.com') or text.startswith('https://twitter.com'):
                                self.raid_info[chat_id]['tweet_link'] = text

                                delete_messages(message)
                                
                                likes_message = self.send_message(message.chat.id, 'Please provide the number of likes needed:')

                                self.ongoing = 'likes'

                                self.messages_list.append(likes_message.id)

                            else:
                                self.send_message(message.chat.id, 'This appears to be a wrong link. Please enter the correct tweet link')

                                return

                        elif self.ongoing == 'likes':
                            self.raid_info[chat_id]['likes_threshold'] = int(text)

                            delete_messages(message)

                            replies_message = self.send_message(message.chat.id, 'Please provide number of replies needed:')

                            self.ongoing = 'replies'

                            self.messages_list.append(replies_message.id)

                        elif self.ongoing == 'replies':
                            self.raid_info[chat_id]['replies_threshold'] = int(text)

                            delete_messages(message)

                            retweets_message = self.send_message(message.chat.id, 'Please provide number of retweets needed:')

                            self.ongoing = 'retweets'

                            self.messages_list.append(retweets_message.id)

                        elif self.ongoing == 'retweets':
                            self.raid_info[chat_id]['retweets_threshold'] = int(text)

                            delete_messages(message)

                            bookmarks_message = self.send_message(message.chat.id, 'Please provide number of bookmarks needed:')

                            self.ongoing = 'bookmarks'

                            self.messages_list.append(bookmarks_message.id)

                        elif self.ongoing == 'bookmarks':
                            self.raid_info[chat_id]['bookmarks_threshold'] = int(text)

                            delete_messages(message)

                            self.send_message(chat_id, 'Now to the details for the buyback')
                            self.send_message(chat_id, 'Please provide your wallet address')

                            self.ongoing = 'wallet_address'

                        elif self.ongoing == 'wallet_address':
                            if text.startswith('0x'):
                                self.raid_info[chat_id]['dev_wallet_address'] = text

                                self.send_message(chat_id, 'Please provide the token address for the token you want to swap')

                                self.ongoing = 'token_address'

                            else:
                                self.reply_to(message, 'Please enter a correct address.')

                        elif self.ongoing == 'token_address':
                            if text.startswith('0x'):
                                self.raid_info[chat_id]['token_address'] = text

                                reply = f"""Do you want to swap ETH from *{self.raid_info[chat_id]['dev_wallet_address']}* to token with token address: *{text}*?
                            
Reply with _Yes_ to proceed, _Edit_ to edit your swap details, or /end to end the swap."""

                                self.send_message(chat_id, reply, parse_mode='Markdown')

                                self.ongoing = 'swap_confirmation'
                            
                            else:
                                self.reply_to(message, 'Please enter a correct address.')
                        
                        elif self.ongoing == 'swap_confirmation':
                            text = text.lower()

                            if text == 'yes':
                                reply = f"""Please transfer the amount of ETH you want to swap to this address:

*{self.WALLET_ADDRESS}*

Please ensure that you send the amount from the wallet address you entered earlier. After sending, reply \
with the transaction hash to confirm the transfer and proceed with the raid."""

                                self.send_message(chat_id, reply, parse_mode='Markdown')
                                
                                self.ongoing = 'tx_validation'

                            elif text == 'edit':
                                self.send_message(chat_id, 'Please provide your wallet address')

                                self.ongoing = 'wallet_address'

                            else:
                                self.send_message(chat_id, 'Please reply with _Yes_ to proceed, _Edit_ to edit your swap details, or /end to end the swap.')

                        elif self.ongoing == 'tx_validation':
                            self.send_message(chat_id, 'Please hold on while your transaction is confirmed.')

                            asyncio.run(self.validate_swap_transaction_task(chat_id, text))

                        else:
                            return 
                    
                    except ValueError:
                        self.reply_to(message, 'It seems like you have entered an incorrect value. Please type the correct value to proceed.')

                    # finally:
                        # unlock_group_command(message)
                        
                else:
                    return
                
            elif chat_type in ('private'):
                if self.is_registering_ad:
                    if self.ongoing == 'ad_username':
                        self.ad_info[chat_id]['username'] = text

                        delete_messages(message)

                        ad_text_message = self.send_message(chat_id, 'Enter your ad text. It should be short and brief.')
                        self.messages_list.append(ad_text_message.id)

                        self.ongoing = 'ad_text'
                    
                    elif self.ongoing == 'ad_text':
                        self.ad_info[chat_id]['ad_text'] = text

                        delete_messages(message)

                        link_message = self.send_message(chat_id, 'Please enter the link your ad should redirect to')
                        self.messages_list.append(link_message.id)

                        self.ongoing = 'ad_link'

                    elif self.ongoing == 'ad_link':
                        if validators.url(text):
                            self.ad_info[chat_id]['link'] = text

                            delete_messages(message)

                            reply = f"""Okay. So if I'm getting this all right, these are your ad details:

        Telegram username: _{self.ad_info[chat_id]['username']}_
        Ad Text: _{self.ad_info[chat_id]['ad_text']}_
        Ad Link: _{self.ad_info[chat_id]['link']}_

        Attached below is how your ad should appear when it is running.

        Reply with _Proceed_ to proceed, or _Edit_ to edit your ad details. Tap /cancel to cancel ad."""
                            
                            markup = quick_markup({
                                f"{self.ad_info[chat_id]['ad_text']}": {'url': self.ad_info[chat_id]['link']}
                            })

                            self.send_message(chat_id, reply, reply_markup=markup, parse_mode='Markdown')

                            self.ongoing = 'ad_confirm'

                        else:
                            self.send_message(chat_id, 'It seems you have entered a wrong link. Note that links should look something like *https://your_url.com*', parse_mode='Markdown')

                    elif self.ongoing == 'ad_confirm':
                        if text.lower() == 'proceed':
                            reply = f"""Please transfer {self.ad_prices[str(self.ad_info[chat_id]['number_of_days'])]}ETH to this address:

    *{self.WALLET_ADDRESS}*

    After sending, reply with the transaction hash to confirm the transfer and proceed with the ad."""
                        
                            self.send_message(chat_id, reply, parse_mode='Markdown')

                            self.ongoing = 'ad_validation'

                        elif text.lower() == 'edit':
                            username_message = self.send_message(chat_id, 'Please enter your username so we can contact you')
                            self.messages_list.append(username_message.id)

                            self.ongoing = 'ad_username'

                        else:
                            self.send_message(chat_id, 'Your input is not recognised. Please enter _Proceed_ to proceed, or _Edit_ to edit the ad, or /cancel to cancel the ad', parse_mode='Markdown')
                    
                    elif self.ongoing == 'ad_validation':
                        if text.startswith('0x'):
                            asyncio.run(self.validate_ad_transaction_task(chat_id, text, self.ad_info))
                        
                        else:
                            self.send_message(chat_id, 'You have entered an incorrect hash. Please enter a correct hash')

    # Perform Twitter Tasks
    async def perform_twitter_tasks(self, group_id):
        raid_group = self.raid_info[group_id]

        likes_required = raid_group['likes_threshold']
        replies_required = raid_group['replies_threshold']
        retweets_required = raid_group['retweets_threshold']
        bookmarks_required = raid_group['bookmarks_threshold']
        tweet_link = raid_group['tweet_link']

        # Send message to trends group
        message = f"""*The jpegdude bot has been activated by --.* The target is {likes_required} likes, \
{replies_required} replies, {retweets_required} retweets, {bookmarks_required} bookmarks. Help them \
achieve their goal here:

{tweet_link}"""
        
        try:
            self.send_message(config('TRENDS_GROUP_ID', cast=int), message, parse_mode='Markdown')

        except Exception as e:
            logger.error(f'Error while sending raid info to trends group: {e}')

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
                    
                    ad = requests.get(f'{self.backend_url}/ads/get-random/').json()

                    advertisement_markup = quick_markup({
                        ad['ad_text']: {'url': ad['external_link']}
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
    async def validate_swap_transaction_task(self, group_id, tx_hash):
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

            if result.get('result', 'None') and result.get('error', True):
                transaction = result['result']

                sender_address = transaction['from']
                recipient_address = transaction['to']
                eth_amount_wei = int(transaction['value'], 16)  # Amount in wei
                eth_amount = Web3.from_wei(eth_amount_wei, 'ether')  # Convert wei to ETH

                logger.info(f'Transaction of {eth_amount} from {sender_address} to {recipient_address} was successfully validated.')

                if (Web3.to_checksum_address(sender_address) == Web3.to_checksum_address(self.raid_info[group_id]['dev_wallet_address']) and
                    Web3.to_checksum_address(recipient_address) == Web3.to_checksum_address(self.WALLET_ADDRESS)):

                    # Create swap record
                    data = {
                        'destination_address': sender_address,
                        'token_address': self.raid_info[group_id]['token_address'],
                        'origin_hash': tx_hash,
                    }

                    response = requests.post(f'{self.backend_url}/swaps/create/', data=data)

                    if response.status_code == 201:
                        self.swap = response.json()
                        
                        self.send_message(group_id, 'Transfer has been validated. Please wait while the buyback is executed.')

                        hash, receipt_status = await self.perform_swap(tx_hash, group_id, eth_amount)

                        if receipt_status == 1:
                            # If transaction was successful
                            self.send_message(group_id, f'Swap with transaction hash *{hash}* was successful!\n\nTwitter raid will now be performed.', parse_mode='Markdown')

                            self.ongoing = 'task'

                            await self.perform_twitter_tasks(group_id)

                        else:
                            self.send_message(group_id, f'Swap with transaction hash *{hash}* could not be completed because an error occurred during the swap.', parse_mode='Markdown')

                    else:
                        logger.info(f'Request to swap create api with origin hash {tx_hash} returned response with status {response.status_code}')

                        self.send_message(group_id, 'Swap could not completed because an error occurred while creating the swap')

                else:
                    logger.info(f'Transaction with hash {tx_hash} could not be validated due to unmatching variables.')

                    self.send_message(group_id, f'Transaction with hash {tx_hash} could not be validated. Please check your transaction hash and try again.')

            else:
                logger.error(f'Error retrieving transaction details with hash {tx_hash}')

                self.send_message(group_id, 'It seems the transaction hash is incorrect. Please try again with a correct transaction hash?')

        # except IntegrityError as e:
        #     logger.error(f'Error creating a swap record: {e}')

        #     self.send_message(group_id, 'It seems this transaction hash has been used to process a swap before. Please reach out to an admin for further assistance.')

        except Exception as e:
            logger.error(f'Error retrieving transaction details of hash {tx_hash}: ({type(e)}, {e}')

            self.send_message(group_id, 'Transaction could not be verified! Please check your transaction hash and try again.')

    async def perform_swap(self, origin_hash, group_id, eth_amount):
        recipient_address = self.raid_info[group_id]['dev_wallet_address']
        token_address = self.raid_info[group_id]['token_address']

        params = {
            'origin_hash': origin_hash,
            'recipient_address': recipient_address,
            'token_address': token_address,
            'amount_to_swap': eth_amount
        }

        response = requests.get(f'{self.backend_url}/swaps/swap/', params=params)

        if response.status_code == 200:
            response = response.json()

            return response['tx_hash'], response['receipt']
        
        return

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

    async def validate_ad_transaction_task(self, chat_id, tx_hash: str, ad_info: dict):
        # Connect to etherscan api and get transaction details
        params = {
            'module': 'transaction', # 'proxy',
            'action': 'gettxreceiptstatus', # 'eth_getTransactionByHash',
            'txhash': tx_hash,
            'apikey': self.ETHERSCAN_KEY_TOKEN
        }

        try:
            # Check the receipt if the transaction was successful
            response = requests.get(self.etherscan_base_url, params=params)
            receipt = response.json()

            result = receipt.get('result', None)

            if result and int(result.get('status', 0)) == 1:
                params['module'] = 'proxy'
                params['action'] = 'eth_getTransactionByHash'

                response = requests.get(self.etherscan_base_url, params=params)
                response = response.json()

                if response.get('result', None) or response.get('error', True):
                    transaction = response['result']

                    sender_address = transaction['from']
                    recipient_address = transaction['to']
                    eth_amount_wei = int(transaction['value'], 16)  # Amount in wei
                    eth_amount = Web3.from_wei(eth_amount_wei, 'ether')  # Convert wei to ETH
                    
                    logger.info(f'Transaction of {eth_amount} from {sender_address} to {recipient_address} was successfully validated.')
                    
                    # Check that the recipient address is the same as the supplied address
                    if Web3.to_checksum_address(recipient_address) == Web3.to_checksum_address(self.WALLET_ADDRESS):
                        # User is allowed to transfer more, or less. The algorithm judges the number of times it is shown daily automatically

                        # if eth_amount >= self.ad_prices[str(self.ad_info[chat_id]['number_of_days'])]:
                        #     ...
                            
                        # Check if the hash has been used for an ad or a swap
                        response = requests.get(f'{self.backend_url}/swaps/', params={'origin_hash': tx_hash})

                        if len(response.json()) >= 1:
                            self.send_message(chat_id, 'It seems this hash has been used to process a swap before. Please make a new transaction and enter hash to proceed with the ad')

                            return 
                        
                        else:
                            ad_info = self.ad_info[chat_id]

                            # Create ad
                            data = {
                                'telegram_username': ad_info['username'],
                                'ad_text': ad_info['ad_text'],
                                'external_link': ad_info['link'],
                                'amount_paid': eth_amount,
                                'showtime_duration': ad_info['number_of_days'],
                                'date_ending': datetime.now() + timedelta(days=ad_info['number_of_days']),
                                'is_paid': True,
                                'is_running': True,
                                'transaction_hash': tx_hash
                            }

                            response = requests.post(f'{self.backend_url}/ads/create/', data=data)
                            
                            ad = response.json()
                                                        
                            logger.info(f'New ad {ad["id"]} created successfully')
                            
                            self.send_message(chat_id, f'Your ad has been created and will start running shortly. Your ad\'s ID is {ad["id"]}. Tap /monitor to monitor ad.')

                            ad_info.clear()

                            self.ongoing = ''

                    else:
                        logger.error(f'Recipient address mismatch with transaction {tx_hash}')

                        self.send_message(chat_id, 'It seems you might have made this transaction to the wrong address. Please check the destination address and make the transaction again. You can tap /cancel to cancel the ad.')

                else:
                    logger.error(f'Error while retrieving transaction with hash {tx_hash}')

                    self.send_message(chat_id, 'An error occurred while retrieving the transaction details. Please try again.') 

            else:
                logger.error(f'Error while retrieving receipt of hash {tx_hash}')

                self.send_message(chat_id, 'An error occurred while retrieving the transaction details. Please try again.')

        except Exception as e:
            logger.error(f'Error creating ad: {e}')

            self.send_message(chat_id, 'It seems this hash has been used to process an ad before. Please make a new transaction and enter hash to proceed with the ad')


if __name__ == '__main__':
    bot = DemoTeleBot(config('TELEGRAM_BOT_TOKEN'))

    bot.polling(non_stop=True, interval=0, allowed_updates=['message', 'callback_query'])

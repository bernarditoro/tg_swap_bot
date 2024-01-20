import requests

from web3 import Web3

from decouple import config

import logging

import time


# Configuration for the root logger with a file handler
logging.basicConfig(
    level=logging.INFO,
    filename='logs.log',
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

    
def swap_eth_for_tokens(recipient_address, token_contract_address, amount_to_swap):
    private_key = config('WALLET_PRIVATE_KEY') # private key of wallet (for authorisation)
    wallet_address = config('WALLET_ADDRESS') # Where eth to be swapped is taken from
    infura_url = config('INFURA_URL')
    uniswap_router_address = config('UNISWAP_ROUTER_ADDRESS')

    web3 = Web3(Web3.HTTPProvider(infura_url)) # Connect to a remote Ethereum node

    wallet_balance_wei = web3.eth.get_balance(wallet_address)
    wallet_balance_eth = web3.from_wei(wallet_balance_wei, 'ether')
    logger.info(f'The balance of {wallet_address} is {wallet_balance_eth}ETH')

    nonce = web3.eth.get_transaction_count(wallet_address) # Equivalent of an id in a database
    gas_price = web3.eth.gas_price
    gas_limit = 200000

    etherscan_base_url = 'https://api.etherscan.io/api'
    abi_params = {
        'module': 'contract',
        'action': 'getabi',
        'address': uniswap_router_address,
        'apikey': config('ETHERSCAN_KEY_TOKEN')
    }
    uniswap_abi_response = requests.get(etherscan_base_url, params=abi_params)

    uniswap_abi = uniswap_abi_response.json()['result']

    uniswap_contract = web3.eth.contract(address=web3.to_checksum_address(uniswap_router_address), abi=uniswap_abi)

    # Convert amount to Wei
    amount_in_wei = web3.to_wei(amount_to_swap, 'ether') 

    # weth_address = uniswap_contract.functions.WETH().call()
    # print(weth_address)

    swap_transaction = uniswap_contract.functions.swapExactETHForTokens(
        0,
        [web3.to_checksum_address('0xB4FBF271143F4FBf7B91A5ded31805e42b2208d6'), web3.to_checksum_address(token_contract_address)],
        recipient_address,
        web3.eth.get_block('latest')['timestamp'] + 600, # Deadline for the transaction
    ).build_transaction({
        'from': wallet_address,
        'gas': gas_limit,
        'gasPrice': gas_price,
        'nonce': nonce,
        'value': amount_in_wei
    })

    signed_transaction = web3.eth.account.sign_transaction(swap_transaction, private_key)

    transaction_hash = web3.eth.send_raw_transaction(signed_transaction.rawTransaction) # Buy the token

    time.sleep(40) # Wait for 40 seconds 

    receipt = web3.eth.get_transaction_receipt(web3.to_hex(transaction_hash))

    logger.info(f'Swapped {amount_to_swap}ETH to tokens with contract_address {token_contract_address} with transaction hash {web3.to_hex(transaction_hash)} and receipt status {receipt.get("status", 0)}')

    return web3.to_hex(transaction_hash), receipt.get('status', 0)


if __name__ == '__main__':
    recipient_address = '0xf248bBa58551d1EB58e020C6c485DcEa46a92a54' # Where to send swapped tokens to
    token_contract_address = config('TOKEN_CONTRACT_ADDRESS')
    amount_to_swap = 0.000393479271386462 # In ether

    hash = swap_eth_for_tokens(recipient_address, token_contract_address, amount_to_swap)

    print (hash)

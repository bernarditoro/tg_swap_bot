import requests

from web3 import Web3

from decouple import config

import logging

import time

from swaps.models import Swap


# Configuration for the root logger with a file handler
logging.basicConfig(
    level=logging.INFO,
    filename='logs/logs.log',
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

    
def swap_eth_for_tokens(network, origin_hash, recipient_address, token_contract_address):
    swap = Swap.objects.get(origin_hash=origin_hash)

    amount_to_swap = swap.get_swap_amount()

    private_key = config('WALLET_PRIVATE_KEY') # private key of wallet (for authorisation)
    wallet_address = config('WALLET_ADDRESS') # Where eth to be swapped is taken from

    router_address = config('UNISWAP_ROUTER_ADDRESS_ETH') if network == 'eth' else config('UNISWAP_ROUTER_ADDRESS_BASE')

    web3 = Web3(Web3.HTTPProvider(config('INFURA_URL'))) if network == 'eth' else Web3(Web3.HTTPProvider(config('ALCHEMY_URL'))) # Connect to a remote Ethereum node

    wallet_balance_wei = web3.eth.get_balance(wallet_address)
    wallet_balance_eth = web3.from_wei(wallet_balance_wei, 'ether')

    swap.wallet_balance_before = wallet_balance_eth
    swap.save()

    logger.info(f'The balance of {wallet_address} before swap is {wallet_balance_eth}ETH')

    nonce = web3.eth.get_transaction_count(wallet_address) # Equivalent of an id in a database
    gas_price = web3.eth.gas_price
    gas_limit = 300000

    scan_base_url = config('ETHERSCAN_BASE_URL') if network == 'eth' else config('BASESCAN_BASE_URL')
    abi_params = {
        'module': 'contract',
        'action': 'getabi',
        'address': router_address,
        'apikey': config('ETHERSCAN_KEY_TOKEN') if network == 'eth' else config('BASESCAN_KEY_TOKEN')
    }
    uniswap_abi_response = requests.get(scan_base_url, params=abi_params)

    uniswap_abi = uniswap_abi_response.json()['result']

    uniswap_contract = web3.eth.contract(address=web3.to_checksum_address(router_address), abi=uniswap_abi)

    # Convert amount to Wei
    amount_in_wei = web3.to_wei(amount_to_swap, 'ether') 

    weth_address = uniswap_contract.functions.WETH().call()
    # print(weth_address)

    swap_transaction = uniswap_contract.functions.swapExactETHForTokens(
        0,
        [web3.to_checksum_address(weth_address), web3.to_checksum_address(token_contract_address)],
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
    
    time.sleep(50) # Wait for 50 seconds

    receipt = web3.eth.get_transaction_receipt(web3.to_hex(transaction_hash))

    wallet_balance_wei_after = web3.eth.get_balance(wallet_address)
    wallet_balance_eth_after = web3.from_wei(wallet_balance_wei_after, 'ether')

    swap.wallet_balance_after = wallet_balance_eth_after
    swap.swap_hash = web3.to_hex(transaction_hash)
    swap.is_successful = receipt.get('status', 0)
    swap.save()

    logger.info(f'Swapped {amount_to_swap}ETH on {"Ethereum" if network == "eth" else "Base"} network to tokens with contract_address {token_contract_address} with transaction hash {web3.to_hex(transaction_hash)} and receipt status {receipt.get("status", 0)}')

    return web3.to_hex(transaction_hash), receipt.get('status', 0)


if __name__ == '__main__':
    recipient_address = '0xf248bBa58551d1EB58e020C6c485DcEa46a92a54' # Where to send swapped tokens to
    token_contract_address = config('TOKEN_CONTRACT_ADDRESS')
    amount_to_swap = 0.000393479271386462 # In ether

    hash, _ = swap_eth_for_tokens('', recipient_address, token_contract_address, amount_to_swap)

    print (hash)

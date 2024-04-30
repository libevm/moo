import json
from web3 import Web3

# Note you'll need an RPC provider with eth_callMany
w3 = Web3(Web3.HTTPProvider('http://localhost:8545'))

def to_ethcall(moo_tx):
    return {
        'from': moo_tx['from'],
        'to': moo_tx['to'],
        'gasLimit': moo_tx['gasLimit'],
        'data': moo_tx['data'],
        'value': moo_tx['value'],
        'maxPriorityFeePerGas': moo_tx.get('maxPriorityFeePerGas', None),
        'maxFeePerGas': moo_tx.get('maxFeePerGas', None),
        'gasPrice': moo_tx.get('gasPrice', None)
    }


# multicall address
# 4d2301cc - getEthBalance(address)
def to_getbalance_tx(addr):
    addr = addr.replace('0x', '')
    return {
        'to': '0x9695FA23b27022c7DD752B7d64bB5900677ECC21',
        'data': '0x4d2301cc000000000000000000000000{}'.format(addr)
    }

# acc[userAddress][txHash] = eth owed
acc = {}

# random coinbase
coinbase = '0xb1C3bc7F56F66E724CC83305c4d4e4d1921Adaf1'

if __name__ == '__main__':
    with open('./dune_resp.json') as f:
        moo_data = json.load(f)
    moo_bundles = moo_data['result']['rows']

    for idx, bundle in enumerate(moo_bundles):
        print('progress {}/{}'.format(idx, len(moo_bundles)))

        block = bundle['blockNumber']
        transactions = json.loads(bundle['transactions'])

        # no backruns
        if len(transactions) <= 1:
            continue

        # opportunity tx
        opp_tx = transactions[0]
        backrun_tx = transactions[1]

        # aux data
        opp_tx_hash = opp_tx['hash']
        opp_tx_creator = opp_tx['from']

        # Check if bundle was include in block, if not ignore
        opp_tx_receipt = None
        try:
            opp_tx_receipt = w3.eth.get_transaction_receipt(opp_tx_hash)
        except:
            pass
        if opp_tx_receipt is None:
            continue

        # Replay the transaction, get the
        resp = w3.provider.make_request(
            'eth_callMany',
            [
                {
                    'transactions': [
                        to_ethcall(opp_tx),
                        to_getbalance_tx(coinbase),
                        to_ethcall(backrun_tx),
                        to_getbalance_tx(coinbase),
                    ],
                    'blockOverride': {
                        'coinbase': coinbase,
                    }
                },
                {
                    'blockNumber': hex(block),
                    'transactionIndex': 0,
                }
            ]
        )

        # Make sure txs are successful
        try:
            results = resp['result']
            before_eth = int(results[1]['value'], 16)
            after_eth = int(results[3]['value'], 16)

            # no profit
            if after_eth <= before_eth:
                continue
            
            delta_eth = after_eth - before_eth
            
            if opp_tx_creator not in acc:
                acc[opp_tx_creator] = {}

            # only save the largest profit for the opp tx
            if opp_tx_hash not in acc[opp_tx_creator]:
                acc[opp_tx_creator][opp_tx_hash] = delta_eth
            elif delta_eth > acc[opp_tx_creator][opp_tx_hash]:
                acc[opp_tx_creator][opp_tx_hash] = delta_eth

        except:
            pass
    
    print('results', acc)
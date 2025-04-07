from flask import Flask, request, jsonify, render_template
from web3 import Web3
import json
import sys

app = Flask(__name__)

def analyze_token(rpc_url, token_address):
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    try:
        checksum_address = w3.to_checksum_address(token_address)
    except:
        return {"error": "Invalid token address"}

    # Load minimal ABI for name and symbol
    token_abi = json.loads('[{"constant":true,"inputs":[],"name":"name","outputs":[{"name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"}]')
    token_contract = w3.eth.contract(address=checksum_address, abi=token_abi)

    try:
        token_name = token_contract.functions.name().call()
        token_symbol = token_contract.functions.symbol().call()
    except:
        return {"error": "Cannot fetch token info"}

    result = {
        "token_name": token_name,
        "token_symbol": token_symbol,
        "bridge_related": False,
        "details": []
    }

    # Heuristic 1: ERC-677 support
    try:
        erc677_abi = json.loads('[{"constant":false,"inputs":[{"name":"_to","type":"address"},{"name":"_value","type":"uint256"},{"name":"_data","type":"bytes"}],"name":"transferAndCall","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"}]')
        erc677_contract = w3.eth.contract(address=checksum_address, abi=erc677_abi)
        if hasattr(erc677_contract.functions, "transferAndCall"):
            result["bridge_related"] = True
            result["details"].append("Heuristic: Token supports ERC-677 (transferAndCall), which facilitates bridge integrations.")
    except:
        pass

    # Heuristic 2: Proxy detection
    try:
        bytecode = w3.eth.get_code(checksum_address).hex()
        if "363d3d373d3d3d363d73" in bytecode:
            result["bridge_related"] = True
            result["details"].append("Heuristic: Contract bytecode matches EIP-1167 minimal proxy pattern, common in bridge wrappers.")
    except:
        pass

    # Heuristic 3: Mint/Burn detection
    try:
        transfer_event_hash = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
        logs = w3.eth.get_logs({"address": checksum_address, "topics": [transfer_event_hash], "fromBlock": "earliest", "toBlock": "latest"})
        zero_address = "0x0000000000000000000000000000000000000000"
        for log in logs:
            topics = log["topics"]
            if len(topics) > 2:
                to_addr = "0x" + topics[2].hex()[-40:]
                from_addr = "0x" + topics[1].hex()[-40:]
                if from_addr == zero_address:
                    result["bridge_related"] = True
                    result["details"].append(f"Heuristic: Mint detected (from zero address) in tx {log['transactionHash'].hex()}")
                elif to_addr == zero_address:
                    result["bridge_related"] = True
                    result["details"].append(f"Heuristic: Burn detected (to zero address) in tx {log['transactionHash'].hex()}")
    except:
        pass

    return result

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.get_json()
    rpc_url = data.get('rpc_url')
    token_address = data.get('token_address')
    if not rpc_url or not token_address:
        return jsonify({"error": "Missing rpc_url or token_address"}), 400
    result = analyze_token(rpc_url, token_address)
    return jsonify(result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
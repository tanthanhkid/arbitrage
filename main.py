from web3 import Web3
import json

# Cài đặt RPC node
rpc_url = "https://ethereum-rpc.publicnode.com"
w3 = Web3(Web3.HTTPProvider(rpc_url))

# Danh sách các tiền tố token đặc biệt
# Các tiền tố hoặc từ khóa liên quan đến bridge, wrapped, cross-chain
bridge_keywords = [
    "axl", "any", "wormhole", "portal", "poly", "multi", "bridged", "layerzero", "lz", "stargate",
    "celer", "debridge", "synapse", "orbit", "gravity", "chainport", "allbridge", "octus", "relay",
    "router", "cross", "xc", "ibc", "interchain", "omnichain", "teleport", "wrapped", "w"
]

special_prefixes = ["axl-", "any-", "wormhole-"]

# Danh sách tên các đồng coin gốc của các blockchain khác (để phát hiện token bridge)
native_chain_coins = [
    "BNB",    # Binance Smart Chain
    "MATIC",  # Polygon
    "AVAX",   # Avalanche
    "FTM",    # Fantom
    "CRO",    # Cronos
    "KLAY",   # Klaytn
    "HT",     # Huobi Token
    "OKB",    # OKEx
    "TRX",    # TRON
    "SOL",    # Solana
    # Có thể mở rộng thêm
]

def get_token_info(token_address):
    # ABI của token (để đọc thông tin token)
    token_abi = json.loads('[{"constant":true,"inputs":[],"name":"name","outputs":[{"name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"}]')
    token_contract = w3.eth.contract(address=token_address, abi=token_abi)
    try:
        token_name = token_contract.functions.name().call()
        token_symbol = token_contract.functions.symbol().call()
        return token_name, token_symbol
    except Exception as e:
        print(f"Lỗi khi lấy thông tin token: {e}")
        return None, None

def check_mint_burn_transactions(token_address):
    # ABI của event Transfer
    transfer_event_hash = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
    logs = w3.eth.get_logs({"address": token_address, "topics": [transfer_event_hash]})
    
    mint_burn_addresses = ["0x0000000000000000000000000000000000000000"]  # Địa chỉ 0 thường được sử dụng cho mint hoặc burn
    
    found_bridge_related = False

    for log in logs:
        tx_hash = log["transactionHash"].hex()
        to_address = Web3.to_checksum_address("0x" + log["topics"][2].hex()[-40:]) if len(log["topics"]) > 2 else None
        from_address = Web3.to_checksum_address("0x" + log["topics"][1].hex()[-40:]) if len(log["topics"]) > 1 else None

        reason = None
        if from_address in mint_burn_addresses:
            reason = "Mint từ địa chỉ 0 (tạo token mới)"
        elif to_address in mint_burn_addresses:
            reason = "Burn về địa chỉ 0 (hủy token)"
        
        if reason:
            print(f"Giao dịch liên quan đến bridge:")
            print(f"  Tx Hash: {tx_hash}")
            print(f"  From: {from_address}")
            print(f"  To: {to_address}")
            print(f"  Lý do: {reason}")
            found_bridge_related = True

    return found_bridge_related

def check_token_name(token_name, token_symbol):
    # Kiểm tra tiền tố đặc biệt
    for prefix in special_prefixes:
        if token_name.startswith(prefix) or token_symbol.startswith(prefix):
            print(f"Token có tiền tố đặc biệt: {prefix}")
            return True

    # Kiểm tra nếu tên hoặc ký hiệu trùng với coin gốc của chain khác (không phân biệt hoa thường)
    for native_coin in native_chain_coins:
        if token_name.upper() == native_coin or token_symbol.upper() == native_coin:
            print(f"Token có tên hoặc ký hiệu trùng với coin gốc của chain khác: {native_coin}")
            return True

    # Kiểm tra các từ khóa liên quan đến bridge trong tên hoặc ký hiệu (không phân biệt hoa thường)
    for keyword in bridge_keywords:
        if keyword.lower() in token_name.lower() or keyword.lower() in token_symbol.lower():
            print(f"Token có chứa từ khóa liên quan đến bridge: {keyword}")
            return True

def check_bridge_related_functions(token_address):
    # Một số hàm phổ biến trong các contract bridge
    bridge_function_names = ["deposit", "withdraw", "lock", "unlock", "mint", "burn"]

    # Tạo contract object với ABI rỗng để gọi các hàm
    contract = w3.eth.contract(address=token_address, abi=[])

    found = False
    try:
        functions = dir(contract.functions)
        for func_name in bridge_function_names:
            if func_name in functions:
                print(f"Contract có hàm liên quan đến bridge: {func_name}()")
                found = True
    except Exception as e:
        print(f"Lỗi khi kiểm tra hàm bridge: {e}")
def check_erc677(token_address):
    try:
        # Minimal ABI for ERC677 transferAndCall
        erc677_abi = json.loads('[{"constant":false,"inputs":[{"name":"_to","type":"address"},{"name":"_value","type":"uint256"},{"name":"_data","type":"bytes"}],"name":"transferAndCall","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"}]')
        contract = w3.eth.contract(address=token_address, abi=erc677_abi)
        # Check if function exists by calling function attribute
        if hasattr(contract.functions, "transferAndCall"):
            print(f"Token contract {token_address} hỗ trợ ERC-677 (có hàm transferAndCall), phù hợp cho tích hợp bridge.")
            return True
    except Exception as e:
        # If ABI incompatible, function likely not supported
        pass
    return False

    return found
    return False


    # Kiểm tra tiền tố đặc biệt
def is_proxy_contract(token_address):
    try:
        bytecode = w3.eth.get_code(token_address).hex()
        # EIP-1167 minimal proxy pattern
        if "363d3d373d3d3d363d73" in bytecode:
            print(f"Token contract {token_address} có dấu hiệu là proxy (EIP-1167 minimal proxy).")
            return True
    except Exception as e:
        print(f"Lỗi khi lấy bytecode contract: {e}")
    return False
    for prefix in special_prefixes:
        if token_name.startswith(prefix) or token_symbol.startswith(prefix):
            print(f"Token có tiền tố đặc biệt: {prefix}")
            return True

    # Kiểm tra nếu tên hoặc ký hiệu trùng với coin gốc của chain khác (case-insensitive)
    for native_coin in native_chain_coins:
        if token_name.upper() == native_coin or token_symbol.upper() == native_coin:
            print(f"Token có tên hoặc ký hiệu trùng với coin gốc của chain khác: {native_coin}")
            return True

    # Kiểm tra các từ khóa liên quan đến bridge trong tên hoặc ký hiệu (không phân biệt hoa thường)
    for keyword in bridge_keywords:
        if keyword.lower() in token_name.lower() or keyword.lower() in token_symbol.lower():
            print(f"Token có chứa từ khóa liên quan đến bridge: {keyword}")
            return True

    return False

def main(token_address):
    token_name, token_symbol = get_token_info(token_address)
    if token_name is None or token_symbol is None:
        print("Không thể lấy thông tin token.")
        return
    
    print(f"Token Name: {token_name}, Token Symbol: {token_symbol}")
    
    token_has_special_prefix = check_token_name(token_name, token_symbol)
    has_mint_burn = check_mint_burn_transactions(token_address)
    is_proxy = is_proxy_contract(token_address)
    has_bridge_functions = check_bridge_related_functions(token_address)

    supports_erc677 = check_erc677(token_address)

    if token_has_special_prefix or has_mint_burn or is_proxy or has_bridge_functions or supports_erc677:
        print(f"Token {token_address} có thể liên quan đến bridge.")
    else:
        print(f"Token {token_address} không có dấu hiệu rõ ràng liên quan đến bridge.")
        print(f"Token {token_address} không có dấu hiệu rõ ràng liên quan đến bridge.")

if __name__ == "__main__":
    token_address = input("Nhập địa chỉ token: ")
    try:
        checksum_address = w3.to_checksum_address(token_address)
    except Exception as e:
        print(f"Địa chỉ không hợp lệ: {e}")
        exit(1)
    main(checksum_address)

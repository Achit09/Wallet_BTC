import os
import ecdsa
import hashlib
import base58
import requests
import bitcoin
import time
import random
from datetime import datetime

# 高價值地址前綴
HIGH_VALUE_PREFIXES = [
    '1A1zP',     # 創世區塊地址前綴
    '3D2oe',     # Bitfinex前綴
    '1FzWL',     # Binance前綴
    '3LYJf',     # Binance前綴
    '34xp4',     # 未知大戶前綴
    'bc1qg',     # 未知大戶前綴
    '1P5ZE',     # 未知大戶前綴
    '1Feex',     # 大額交易前綴
    'bc1q',      # SegWit大戶前綴
    '385cR',     # 礦池地址前綴
    '3CxQo',     # 交易所熱錢包前綴
    'bc1qa',     # SegWit大戶前綴
    'bc1qc',     # SegWit大戶前綴
    'bc1qm',     # SegWit大戶前綴
    'bc1qp',     # SegWit大戶前綴
    'bc1qr',     # SegWit大戶前綴
    'bc1qt',     # SegWit大戶前綴
    'bc1qw',     # SegWit大戶前綴
    '1NDyJ',     # 早期礦工地址前綴
    '1GR9q',     # 大戶錢包前綴
    '1J6PY',     # 早期用戶地址前綴
    '1BitG',     # 知名地址前綴
    '1Ma1n',     # 早期礦工地址前綴
    '1CXN',      # 大額交易地址前綴
]

# User-Agent
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

def generate_wallet():
    """生成比特幣錢包"""
    try:
        private_key = os.urandom(32)
        extended_key = b"\x80" + private_key
        checksum = hashlib.sha256(hashlib.sha256(extended_key).digest()).digest()[:4]
        wif = base58.b58encode(extended_key + checksum).decode()
        
        signing_key = ecdsa.SigningKey.from_string(private_key, curve=ecdsa.SECP256k1)
        verifying_key = signing_key.get_verifying_key()
        public_key = bytes.fromhex("04") + verifying_key.to_string()
        
        address = bitcoin.pubkey_to_address(public_key.hex())
        return address, wif
    except Exception as e:
        print(f"生成錢包錯誤: {str(e)}")
        return None, None

def check_balance(address):
    """檢查地址餘額"""
    try:
        response = requests.get(
            "https://blockchain.info/balance",
            params={"active": address},
            headers={'User-Agent': USER_AGENT},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            return float(data[address]["final_balance"])
        elif response.status_code == 429:  # 請求過多
            time.sleep(60)
        return 0
    except:
        time.sleep(5)
        return 0

def get_address_type(address):
    """判斷地址類型"""
    if address.startswith('1A1zP1'):
        return "中本聰相關地址"
    elif address.startswith(('3D2oet', '1FzWLk', '3LYJfc')):
        return "交易所冷錢包"
    elif address.startswith(('34xp4v', 'bc1qgd', '1P5ZED')):
        return "大戶錢包"
    elif address.startswith(('1FeexV', '1CXN')):
        return "大額交易地址"
    elif address.startswith(('bc1qa', 'bc1qc', 'bc1qm', 'bc1qp', 'bc1qr', 'bc1qt', 'bc1qw')):
        return "SegWit大戶地址"
    elif address.startswith(('385cR5', '1NDyJ', '1Ma1n')):
        return "礦工地址"
    elif address.startswith('3CxQoE'):
        return "交易所熱錢包"
    elif address.startswith(('1GR9q', '1J6PY', '1BitG')):
        return "早期用戶地址"
    elif address.startswith('1FeexV'):
        return "大額交易地址"
    elif address.startswith('bc1qx'):
        return "SegWit大戶地址"
    elif address.startswith('385cR5'):
        return "礦池地址"
    elif address.startswith('3CxQoE'):
        return "交易所熱錢包"
    return "普通地址"

def save_found_address(address, wif, balance, address_type):
    """保存找到的地址"""
    try:
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 獲取當前腳本所在目錄
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 有餘額的地址保存到 found_with_balance.txt
        if balance > 0:
            balance_file = os.path.join(script_dir, 'found_with_balance.txt')
            try:
                with open(balance_file, 'a', encoding='utf-8') as f:
                    f.write("\n" + "!" * 50)
                    f.write(f"\n發現時間: {current_time}")
                    f.write(f"\n地址: {address}")
                    f.write(f"\n類型: {address_type}")
                    f.write(f"\n私鑰: {wif}")
                    f.write(f"\n餘額: {balance} BTC")
                    f.write("\n" + "!" * 50 + "\n")
            except PermissionError:
                print(f"無法寫入文件 {balance_file}，請檢查文件權限")
                # 嘗試在用戶目錄下保存
                user_dir = os.path.expanduser('~')
                balance_file = os.path.join(user_dir, 'found_with_balance.txt')
                with open(balance_file, 'a', encoding='utf-8') as f:
                    f.write(f"\n發現時間: {current_time}")
                    f.write(f"\n地址: {address}")
                    f.write(f"\n類型: {address_type}")
                    f.write(f"\n私鑰: {wif}")
                    f.write(f"\n餘額: {balance} BTC")
                    f.write("\n" + "!" * 50 + "\n")
        
        # 所有高價值地址都保存到 high_value_addresses.txt
        value_file = os.path.join(script_dir, 'high_value_addresses.txt')
        try:
            with open(value_file, 'a', encoding='utf-8') as f:
                f.write(f"\n發現時間: {current_time}")
                f.write(f"\n地址: {address}")
                f.write(f"\n類型: {address_type}")
                f.write(f"\n私鑰: {wif}")
                f.write(f"\n餘額: {balance} BTC")
                f.write("\n" + "-" * 50 + "\n")
        except PermissionError:
            print(f"無法寫入文件 {value_file}，請檢查文件權限")
            # 嘗試在用戶目錄下保存
            user_dir = os.path.expanduser('~')
            value_file = os.path.join(user_dir, 'high_value_addresses.txt')
            with open(value_file, 'a', encoding='utf-8') as f:
                f.write(f"\n發現時間: {current_time}")
                f.write(f"\n地址: {address}")
                f.write(f"\n類型: {address_type}")
                f.write(f"\n私鑰: {wif}")
                f.write(f"\n餘額: {balance} BTC")
                f.write("\n" + "-" * 50 + "\n")
            
    except Exception as e:
        print(f"保存錯誤: {str(e)}")
        # 如果出現錯誤，至少在控制台輸出重要信息
        print(f"重要發現！地址: {address}, 私鑰: {wif}, 餘額: {balance} BTC")

def main():
    total_checked = 0
    valuable_checked = 0
    start_time = datetime.now()
    
    print("\n開始搜索比特幣錢包...")
    
    while True:
        try:
            # 生成新錢包
            address, wif = generate_wallet()
            if not address or not wif:
                continue
            
            total_checked += 1
            
            # 檢查是否為高價值地址
            if any(address.startswith(prefix) for prefix in HIGH_VALUE_PREFIXES):
                valuable_checked += 1
                address_type = get_address_type(address)
                balance = check_balance(address)
                
                # 保存並顯示結果
                save_found_address(address, wif, balance, address_type)
                
                if balance > 0:
                    print(f"\n發現有餘額的錢包！")
                    print(f"地址: {address}")
                    print(f"類型: {address_type}")
                    print(f"私鑰: {wif}")
                    print(f"餘額: {balance} BTC")
                    print("=" * 50)
            
            # 顯示進度
            if total_checked % 100 == 0:
                elapsed = (datetime.now() - start_time).total_seconds()
                speed = total_checked / elapsed if elapsed > 0 else 0
                print(f"\r已檢查: {total_checked:,} 個地址 | "
                      f"找到高價值地址: {valuable_checked} 個 | "
                      f"速度: {speed:.2f} 地址/秒", end='', flush=True)
            
        except KeyboardInterrupt:
            print("\n\n程序已停止")
            break
        except Exception as e:
            time.sleep(5)
            continue

if __name__ == "__main__":
    main()
import os
import ecdsa
import hashlib
import base58
import requests
import bitcoin
import time
import random
from datetime import datetime
import threading
from concurrent.futures import ThreadPoolExecutor
from queue import Queue, Empty
import json
from bit import Key
import logging

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

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_wallets_batch(batch_size=5000):
    """批量生成比特幣錢包"""
    wallets = []
    
    # 預先生成所有私鑰
    private_keys = [os.urandom(32) for _ in range(batch_size)]
    
    # 批量處理私鑰
    for chunk in [private_keys[i:i + 100] for i in range(0, len(private_keys), 100)]:
        for private_key in chunk:
            try:
                # 使用更快的方式生成WIF
                extended_key = b"\x80" + private_key
                wif = base58.b58encode(extended_key + hashlib.sha256(hashlib.sha256(extended_key).digest()).digest()[:4]).decode()
                
                # 優化公鑰生成
                signing_key = ecdsa.SigningKey.from_string(private_key, curve=ecdsa.SECP256k1)
                public_key = b'\04' + signing_key.get_verifying_key().to_string()
                
                # 使用更快的方式生成地址
                ripemd160 = hashlib.new('ripemd160')
                ripemd160.update(hashlib.sha256(public_key).digest())
                version = b'\x00'
                vh160 = version + ripemd160.digest()
                double_sha256 = hashlib.sha256(hashlib.sha256(vh160).digest()).digest()
                address = base58.b58encode(vh160 + double_sha256[:4]).decode()
                
                # 快速檢查前綴
                if any(address.startswith(prefix) for prefix in HIGH_VALUE_PREFIXES):
                    wallets.append((address, wif))
                    
            except Exception:
                continue
    return wallets

def check_balances_batch(addresses):
    """批量檢查地址餘額"""
    if not addresses:
        return {}
        
    try:
        # 分批檢查，每次最多20個地址
        batch_size = 20
        results = {}
        
        for i in range(0, len(addresses), batch_size):
            batch = addresses[i:i + batch_size]
            addresses_str = '|'.join(batch)
            
            response = requests.get(
                "https://blockchain.info/balance",
                params={"active": addresses_str},
                headers={'User-Agent': USER_AGENT},
                timeout=10
            )
            
            if response.status_code == 200:
                results.update(response.json())
            elif response.status_code == 429:
                time.sleep(5)  # 減少等待時間
                
            time.sleep(0.1)  # 短暫延遲避免請求過快
            
        return results
    except:
        time.sleep(1)
        return {}

class WalletFinder(threading.Thread):
    def __init__(self, result_queue, batch_size=5000):
        super().__init__()
        self.result_queue = result_queue
        self.batch_size = batch_size
        self.running = True
        self._batch_counter = 0
        self._last_time = time.time()

    def run(self):
        while self.running:
            wallets = generate_wallets_batch(self.batch_size)
            if wallets:
                self.result_queue.put(wallets)
            
            self._batch_counter += self.batch_size
            current_time = time.time()
            if current_time - self._last_time >= 1:
                self._batch_counter = 0
                self._last_time = current_time

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
    """保存找到的地址（優化版）"""
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        if balance > 0:
            data = {
                "time": current_time,
                "address": address,
                "type": address_type,
                "private_key": wif,
                "balance": balance
            }
            
            balance_file = os.path.join(script_dir, 'found_with_balance.txt')
            with open(balance_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(data, ensure_ascii=False) + "\n")
        
        # 高價值地址記錄
        value_file = os.path.join(script_dir, 'high_value_addresses.txt')
        with open(value_file, 'a', encoding='utf-8') as f:
            data = {
                "time": current_time,
                "address": address,
                "type": address_type,
                "private_key": wif,
                "balance": balance
            }
            f.write(json.dumps(data, ensure_ascii=False) + "\n")
            
    except Exception as e:
        print(f"保存錯誤: {str(e)}")
        print(f"重要發現！地址: {address}, 私鑰: {wif}, 餘額: {balance} BTC")

def print_status(total_checked, valuable_checked, speed, clear=True):
    """打印當前狀態"""
    if clear:
        # 清空終端機
        os.system('cls' if os.name == 'nt' else 'clear')
    
    print("\n=== 比特幣錢包搜索狀態 ===")
    print(f"總計檢查地址數: {total_checked:,}")
    print(f"發現高價值地址: {valuable_checked:,}")
    print(f"當前搜索速度: {speed:.2f} 地址/秒")
    print("=" * 25)

class BTCWalletSearcher:
    def __init__(self, thread_count=4):
        self.addresses_checked = 0
        self.valuable_found = 0
        self.start_time = time.time()
        self.thread_count = thread_count
        self.lock = threading.Lock()
    
    def check_wallet(self):
        while True:
            private_key = Key()
            address = private_key.address
            
            with self.lock:
                self.addresses_checked += 1
                
                # 每1000個地址顯示一次狀態
                if self.addresses_checked % 1000 == 0:
                    elapsed_time = time.time() - self.start_time
                    speed = self.addresses_checked / elapsed_time
                    print(f"\n=== 比特幣錢包搜索狀態 ===")
                    print(f"總計檢查地址數: {self.addresses_checked:,}")
                    print(f"發現高價值地址: {self.valuable_found}")
                    print(f"當前搜索速度: {speed:.2f} 地址/秒")
    
    def start_search(self):
        logger.info(f"開始使用 {self.thread_count} 個線程進行搜索...")
        with ThreadPoolExecutor(max_workers=self.thread_count) as executor:
            futures = [executor.submit(self.check_wallet) for _ in range(self.thread_count)]

def main():
    num_threads = os.cpu_count() * 2
    result_queue = Queue(maxsize=1000)
    total_checked = 0
    valuable_checked = 0
    start_time = datetime.now()
    last_status_update = time.time()
    
    print(f"\n初始化比特幣錢包搜索程序...")
    print(f"啟動 {num_threads} 個搜索線程")
    print("正在準備資源...\n")
    
    threads = []
    for i in range(num_threads):
        thread = WalletFinder(result_queue)
        thread.start()
        threads.append(thread)
        print(f"線程 {i+1}/{num_threads} 已啟動")
    
    print("\n所有線程已啟動，開始搜索...\n")
    time.sleep(1)
    
    try:
        while True:
            try:
                valuable_wallets = result_queue.get_nowait()
                addresses = [w[0] for w in valuable_wallets]
                balances = check_balances_batch(addresses)
                
                for address, wif in valuable_wallets:
                    valuable_checked += 1
                    balance = balances.get(address, {}).get('final_balance', 0)
                    
                    if balance > 0:
                        address_type = get_address_type(address)
                        print_status(total_checked, valuable_checked, 0, clear=True)
                        print("\n!!! 發現有餘額的錢包 !!!")
                        print(f"地址: {address}")
                        print(f"類型: {address_type}")
                        print(f"私鑰: {wif}")
                        print(f"餘額: {balance} BTC")
                        print("=" * 50)
                        save_found_address(address, wif, balance, address_type)
                
                total_checked += self.batch_size  # 更新檢查總數
                
            except Empty:
                current_time = time.time()
                if current_time - last_status_update >= 1:
                    elapsed = (datetime.now() - start_time).total_seconds()
                    speed = total_checked / elapsed if elapsed > 0 else 0
                    print_status(total_checked, valuable_checked, speed)
                    last_status_update = current_time
                time.sleep(0.001)  # 極短的睡眠時間
            
    except KeyboardInterrupt:
        print("\n\n正在停止程序...")
        for thread in threads:
            thread.running = False
        
        print("等待線程結束...")
        for i, thread in enumerate(threads, 1):
            thread.join()
            print(f"線程 {i}/{num_threads} 已停止")
        
        # 顯示最終統計
        elapsed = (datetime.now() - start_time).total_seconds()
        speed = total_checked / elapsed if elapsed > 0 else 0
        print("\n=== 搜索統計 ===")
        print(f"運行時間: {elapsed:.1f} 秒")
        print(f"檢查地址: {total_checked:,}")
        print(f"高價值地址: {valuable_checked:,}")
        print(f"平均速度: {speed:.2f} 地址/秒")
        print("=" * 25)
        print("\n程序已完全停止")

if __name__ == "__main__":
    searcher = BTCWalletSearcher(thread_count=8)  # 使用8個線程
    try:
        searcher.start_search()
    except KeyboardInterrupt:
        print("\n程序已停止")
import multiprocessing as mp
import time
from bit import Key
import logging
from datetime import datetime
import os
import json
from multiprocessing import Value, Lock

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BTCWalletSearcherMP:
    def __init__(self, process_count=None):
        self.process_count = process_count or mp.cpu_count()
        # 使用 Value 替代 Manager().dict()
        self.addresses_checked = Value('i', 0)
        self.valuable_found = Value('i', 0)
        self.start_time = time.time()
        self.lock = Lock()
        
    def check_wallet(self):
        while True:
            try:
                private_key = Key()
                address = private_key.address
                
                # 更新計數
                with self.lock:
                    self.addresses_checked.value += 1
                    current_count = self.addresses_checked.value
                
                # 每1000個地址顯示一次狀態
                if current_count % 1000 == 0:
                    self.print_status()
                    
                # 檢查是否為高價值地址
                if self.is_valuable_address(address):
                    self.save_valuable_wallet(address, private_key.to_wif())
                    with self.lock:
                        self.valuable_found.value += 1
                    
            except Exception as e:
                logger.error(f"處理錢包時發生錯誤: {str(e)}")
                continue
    
    def is_valuable_address(self, address):
        valuable_prefixes = [
            '1A1zP', '3D2oe', '1FzWL', '3LYJf', '34xp4',
            'bc1qg', '1P5ZE', '1Feex', 'bc1q', '385cR',
            '3CxQo', 'bc1qa', 'bc1qc', 'bc1qm', 'bc1qp',
            'bc1qr', 'bc1qt', 'bc1qw', '1NDyJ', '1GR9q',
            '1J6PY', '1BitG', '1Ma1n', '1CXN'
        ]
        return any(address.startswith(prefix) for prefix in valuable_prefixes)
    
    def save_valuable_wallet(self, address, wif):
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        data = {
            "time": current_time,
            "address": address,
            "private_key": wif
        }
        
        filename = os.path.join(os.path.dirname(__file__), 'valuable_wallets_mp.txt')
        try:
            with open(filename, 'a', encoding='utf-8') as f:
                f.write(json.dumps(data, ensure_ascii=False) + "\n")
            logger.info(f"發現高價值地址: {address}")
        except Exception as e:
            logger.error(f"保存錢包時發生錯誤: {str(e)}")
    
    def print_status(self):
        elapsed_time = time.time() - self.start_time
        speed = self.addresses_checked.value / elapsed_time if elapsed_time > 0 else 0
        
        status = f"""
=== 比特幣錢包搜索狀態（多進程版本）===
進程數: {self.process_count}
總計檢查地址數: {self.addresses_checked.value:,}
發現高價值地址: {self.valuable_found.value}
當前搜索速度: {speed:.2f} 地址/秒
運行時間: {elapsed_time:.1f} 秒
==========================================
"""
        print(status)
    
    def start_search(self):
        logger.info(f"啟動 {self.process_count} 個處理進程...")
        
        # 創建並啟動進程
        processes = []
        for _ in range(self.process_count):
            p = mp.Process(target=self.check_wallet)
            p.start()
            processes.append(p)
        
        try:
            # 等待所有進程完成
            for p in processes:
                p.join()
        except KeyboardInterrupt:
            logger.info("接收到停止信號，正在關閉進程...")
            for p in processes:
                p.terminate()
            logger.info("所有進程已停止")

if __name__ == "__main__":
    # 在 Windows 上需要這行
    mp.freeze_support()
    
    try:
        # 使用系統CPU核心數量的進程
        searcher = BTCWalletSearcherMP()
        print(f"使用 {searcher.process_count} 個CPU核心進行搜索")
        print("程序啟動中...")
        time.sleep(1)  # 給使用者時間閱讀信息
        searcher.start_search()
    except KeyboardInterrupt:
        print("\n程序已停止") 
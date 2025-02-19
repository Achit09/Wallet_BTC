import multiprocessing as mp
import time
from bit import Key
import logging
from datetime import datetime
import os
import json
from multiprocessing import Value, Lock
import psutil
import platform
import sys
import signal

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('btc_wallet_search.log')
    ]
)
logger = logging.getLogger(__name__)

class SystemInfo:
    @staticmethod
    def get_optimal_process_count():
        try:
            # 獲取CPU信息
            cpu_count = mp.cpu_count()
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            # 獲取系統平台
            system_platform = platform.system()
            
            logger.info(f"系統信息:")
            logger.info(f"平台: {system_platform}")
            logger.info(f"CPU核心數: {cpu_count}")
            logger.info(f"CPU使用率: {cpu_percent}%")
            logger.info(f"內存使用率: {memory.percent}%")
            
            # Windows 特別處理
            if system_platform == "Windows":
                # Windows下更保守的進程數設置
                optimal_count = max(1, min(cpu_count - 2, 4))
            else:
                optimal_count = max(1, cpu_count)
            
            # 系統負載調整
            if cpu_percent > 80:
                optimal_count = max(1, optimal_count - 1)
            if memory.percent > 80:
                optimal_count = max(1, optimal_count - 1)
                
            logger.info(f"建議進程數: {optimal_count}")
            return optimal_count
            
        except Exception as e:
            logger.warning(f"獲取系統信息時出錯: {e}")
            return 2

class BTCWalletSearcherMP:
    def __init__(self, process_count=None):
        self.process_count = process_count or SystemInfo.get_optimal_process_count()
        self.addresses_checked = Value('i', 0)
        self.valuable_found = Value('i', 0)
        self.start_time = Value('d', time.time())
        self.lock = Lock()
        self.stop_flag = Value('i', 0)
        
    def signal_handler(self, signum, frame):
        self.stop_flag.value = 1
        logger.info("接收到停止信號")
        
    def check_wallet(self):
        process_name = mp.current_process().name
        pid = os.getpid()
        logger.info(f"進程 {process_name} (PID: {pid}) 已啟動")
        
        # Windows下設置更低的進程優先級
        if platform.system() == "Windows":
            try:
                import win32api
                import win32process
                win32api.SetThreadPriority(win32api.GetCurrentThread(), 
                                         win32process.THREAD_PRIORITY_BELOW_NORMAL)
            except ImportError:
                pass
        
        while not self.stop_flag.value:
            try:
                private_key = Key()
                address = private_key.address
                
                with self.lock:
                    self.addresses_checked.value += 1
                    current_count = self.addresses_checked.value
                
                if current_count % 1000 == 0:
                    self.print_status()
                    
                if self.is_valuable_address(address):
                    self.save_valuable_wallet(address, private_key.to_wif())
                    with self.lock:
                        self.valuable_found.value += 1
                    
            except Exception as e:
                logger.error(f"進程 {process_name} 發生錯誤: {str(e)}")
                time.sleep(0.1)  # 錯誤發生時短暫暫停
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
        try:
            elapsed_time = time.time() - self.start_time.value
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
            sys.stdout.flush()  # 確保Windows下正確輸出
        except Exception as e:
            logger.error(f"顯示狀態時發生錯誤: {str(e)}")
    
    def start_search(self):
        # 設置信號處理
        signal.signal(signal.SIGINT, self.signal_handler)
        
        logger.info(f"正在使用 {self.process_count} 個進程開始搜索...")
        logger.info("初始化進程池...")
        
        processes = []
        try:
            for i in range(self.process_count):
                p = mp.Process(target=self.check_wallet, name=f"Searcher-{i+1}")
                p.daemon = True
                processes.append(p)
            
            for p in processes:
                p.start()
                time.sleep(0.5)
                if not p.is_alive():
                    logger.error(f"進程 {p.name} 啟動失敗")
                else:
                    logger.info(f"進程 {p.name} 啟動成功")
            
            # 主進程等待
            while not self.stop_flag.value:
                time.sleep(1)
                
        except Exception as e:
            logger.error(f"程序運行時發生錯誤: {str(e)}")
        finally:
            self.stop_flag.value = 1
            logger.info("正在關閉所有進程...")
            for p in processes:
                if p.is_alive():
                    p.terminate()
                    p.join(timeout=1)
            logger.info("所有進程已停止")

def main():
    if platform.system() == "Windows":
        # Windows特定設置
        import ctypes
        try:
            ctypes.windll.kernel32.SetProcessPriorityClass(
                ctypes.windll.kernel32.GetCurrentProcess(),
                0x00004000 #BELOW_NORMAL_PRIORITY_CLASS
            )
        except:
            pass
    
    mp.freeze_support()
    
    try:
        print("正在檢查系統資源...")
        time.sleep(1)
        searcher = BTCWalletSearcherMP()
        print(f"\n系統初始化完成，使用 {searcher.process_count} 個進程")
        print("程序啟動中...\n")
        time.sleep(2)
        searcher.start_search()
    except KeyboardInterrupt:
        print("\n程序已停止")
    except Exception as e:
        logger.error(f"程序發生致命錯誤: {str(e)}")

if __name__ == "__main__":
    main() 
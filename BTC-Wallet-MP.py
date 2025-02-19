import multiprocessing as mp
import time
from bit import Key
import logging
from datetime import datetime
import os
import json
from multiprocessing import Value, Lock, Process
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

# 全局變量，用於進程間共享
STOP_FLAG = Value('i', 0)
ADDRESSES_CHECKED = Value('i', 0)
VALUABLE_FOUND = Value('i', 0)
START_TIME = Value('d', time.time())
PROCESS_LOCK = Lock()

def get_optimal_process_count():
    """獲取最優進程數"""
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

def check_wallet(process_id):
    """獨立的進程函數，避免pickle問題"""
    process_name = f"Searcher-{process_id}"
    pid = os.getpid()
    logger.info(f"進程 {process_name} (PID: {pid}) 已啟動")
    
    # Windows下設置進程優先級
    if platform.system() == "Windows":
        try:
            import win32api
            import win32process
            win32api.SetThreadPriority(win32api.GetCurrentThread(), 
                                     win32process.THREAD_PRIORITY_BELOW_NORMAL)
        except ImportError:
            pass
    
    wallet_count = 0
    last_status_time = time.time()
    
    while not STOP_FLAG.value:
        try:
            private_key = Key()
            address = private_key.address
            
            with PROCESS_LOCK:
                ADDRESSES_CHECKED.value += 1
                wallet_count += 1
            
            # 每個進程獨立計數，減少鎖競爭
            if wallet_count % 100 == 0:
                current_time = time.time()
                if current_time - last_status_time >= 1:
                    print_status()
                    last_status_time = current_time
                
            if is_valuable_address(address):
                save_valuable_wallet(address, private_key.to_wif(), process_name)
                with PROCESS_LOCK:
                    VALUABLE_FOUND.value += 1
                    logger.info(f"進程 {process_name} 發現高價值地址")
            
        except Exception as e:
            logger.error(f"進程 {process_name} 發生錯誤: {str(e)}")
            time.sleep(0.1)

def is_valuable_address(address):
    """檢查是否為高價值地址"""
    valuable_prefixes = [
        '1A1zP', '3D2oe', '1FzWL', '3LYJf', '34xp4',
        'bc1qg', '1P5ZE', '1Feex', 'bc1q', '385cR',
        '3CxQo', 'bc1qa', 'bc1qc', 'bc1qm', 'bc1qp',
        'bc1qr', 'bc1qt', 'bc1qw', '1NDyJ', '1GR9q',
        '1J6PY', '1BitG', '1Ma1n', '1CXN'
    ]
    return any(address.startswith(prefix) for prefix in valuable_prefixes)

def save_valuable_wallet(address, wif, process_name):
    """保存高價值錢包"""
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    data = {
        "time": current_time,
        "address": address,
        "private_key": wif,
        "found_by": process_name
    }
    
    filename = os.path.join(os.path.dirname(__file__), 'valuable_wallets_mp.txt')
    try:
        with open(filename, 'a', encoding='utf-8') as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")
        logger.info(f"發現高價值地址: {address}")
    except Exception as e:
        logger.error(f"保存錢包時發生錯誤: {str(e)}")

def print_status():
    """打印當前狀態"""
    try:
        elapsed_time = time.time() - START_TIME.value
        speed = ADDRESSES_CHECKED.value / elapsed_time if elapsed_time > 0 else 0
        
        status = f"""
=== 比特幣錢包搜索狀態（多進程版本）===
總計檢查地址數: {ADDRESSES_CHECKED.value:,}
發現高價值地址: {VALUABLE_FOUND.value}
當前搜索速度: {speed:.2f} 地址/秒
運行時間: {elapsed_time:.1f} 秒
==========================================
"""
        print(status)
        sys.stdout.flush()
    except Exception as e:
        logger.error(f"顯示狀態時發生錯誤: {str(e)}")

def main():
    processes = []  # 移到函數開始處定義
    
    if platform.system() == "Windows":
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
        process_count = get_optimal_process_count()  # 使用新的函數
        
        print(f"\n系統初始化完成，使用 {process_count} 個進程")
        print("程序啟動中...\n")
        time.sleep(2)
        
        # 創建進程
        for i in range(process_count):
            p = Process(target=check_wallet, args=(i+1,))
            p.daemon = True
            processes.append(p)
        
        # 啟動進程
        for p in processes:
            p.start()
            time.sleep(0.5)
        
        # 監控進程
        while True:
            alive_count = sum(1 for p in processes if p.is_alive())
            if alive_count < process_count:
                logger.warning(f"檢測到進程異常退出，當前活動進程數: {alive_count}")
                # 重啟死亡的進程
                for i, p in enumerate(processes):
                    if not p.is_alive():
                        new_p = Process(target=check_wallet, args=(i+1,))
                        new_p.daemon = True
                        new_p.start()
                        processes[i] = new_p
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("接收到停止信號")
        STOP_FLAG.value = 1
        for p in processes:
            if p.is_alive():
                p.terminate()
        print("\n程序已停止")
    except Exception as e:
        logger.error(f"程序發生致命錯誤: {str(e)}")
        STOP_FLAG.value = 1
        for p in processes:
            if p.is_alive():
                p.terminate()

if __name__ == "__main__":
    main() 
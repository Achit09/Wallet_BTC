# 比特幣高價值錢包搜索程式 🔍

這是一個專門用於搜索比特幣高價值錢包的程式，通過特定前綴匹配來識別潛在的高價值地址。

## 🎯 搜索目標

### 中本聰相關
- `1A1zP1` - 創世區塊地址前綴

### 交易所錢包
- `3D2oet` - Bitfinex前綴
- `1FzWLk` - Binance前綴
- `3LYJfc` - Binance前綴
- `3CxQoE` - 交易所熱錢包前綴

### 大戶錢包
- `34xp4v` - 未知大戶前綴
- `bc1qgd` - 未知大戶前綴
- `1P5ZED` - 未知大戶前綴
- `1FeexV` - 大額交易前綴
- `bc1qx`  - SegWit大戶前綴
- `385cR5` - 礦池地址前綴

## 💡 工作流程

1. 生成隨機比特幣錢包
2. 檢查地址是否匹配高價值前綴
3. 對匹配的地址進行餘額查詢
4. 保存搜索結果

## 📊 輸出文件

- `high_value_addresses.txt`: 記錄所有匹配前綴的地址
- `found_with_balance.txt`: 記錄發現的有餘額錢包

## 🚀 使用方法

1. 安裝必要套件：
   ```bash
   pip install ecdsa
   pip install base58
   pip install bitcoin
   pip install requests
   ```

2. 運行程式：  
   ```bash
   python BTC-Wallet_FC.py
   ```

## 📝 運行顯示

程式運行時會顯示：
- 已檢查的地址數量
- 發現的高價值地址數量
- 當前處理速度（地址/秒）

## 📝 注意事項

- 本程式僅供學習和研究使用
- 請勿用於非法用途
- 建議使用代理服務器避免 IP 被限制
- 長時間運行時請注意 API 請求限制

## 🔄 程式特點

1. 高效的前綴匹配機制
2. 自動保存所有發現的高價值地址
3. 分開記錄有餘額和無餘額的地址
4. 實時顯示搜索進度
5. 自動錯誤處理和恢復機制

## 📈 搜索策略

- 使用已知的高價值地址前綴作為篩選條件
- 優先檢查特定模式的地址
- 自動跳過普通地址，提高效率

## 👨‍💻 作者

[Achit999]
<<<<<<< HEAD
Donate BTC Address: bc1qmvplzwalslgmeavt525ah6waygkrk99gpc22hj
=======
>>>>>>> 673a08467e56e1a2a3de7b294ca3b42edb75796f

## 📜 授權

MIT License

---

**免責聲明：** 本程式僅供教育和研究目的使用。使用者需自行承擔使用風險。


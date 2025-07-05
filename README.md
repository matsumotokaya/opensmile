# OpenSMILE Vault API連携サービス

OpenSMILEライブラリを使用したVault API連携による音声特徴量抽出サービスです。

## 概要

このAPIはVault APIから音声ファイル（WAV形式）を取得し、音響特徴量を抽出してVault APIに結果を保存します。

### 主要機能

- **Vault API連携**: EC2 Vault APIからWAVファイル自動取得
- **音声特徴量抽出**: OpenSMILEを使用したeGeMAPSv02特徴量抽出（88種類）
- **タイムライン出力**: 1秒ごとの詳細特徴量タイムライン
- **自動保存**: 処理結果をVault APIに自動アップロード

## API仕様

### エンドポイント

- `GET /` - API情報
- `GET /health` - ヘルスチェック
- `GET /docs` - Swagger UIドキュメント
- `POST /process/vault-data` - Vault API連携による音声特徴量抽出

## 使用方法

### サーバー起動

```bash
# 依存関係インストール（Python3を使用）
pip3 install -r requirements.txt

# サーバー起動（ポート8011を使用）
uvicorn main:app --host 0.0.0.0 --port 8011

# または開発モード（Python3で実行）
python3 main.py
```

**注意事項:**
- **このAPIはポート8011で動作します**
- **Python3を使用してください**（`python`ではなく`python3`コマンドを使用）

### Vault API連携エンドポイントの使用例

```bash
# EC2 Vault APIからWAVファイルを取得して特徴量タイムライン抽出
curl -X POST http://localhost:8011/process/vault-data \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "device123",
    "date": "2025-06-25"
  }'
```

**処理フロー:**
1. Vault APIから指定日付のWAVファイルを取得
2. OpenSMILEで1秒ごとの特徴量タイムライン抽出
3. `opensmile/09-00.json` 形式でVault APIに結果保存

**個別JSONファイル出力例 (09-00.json):**
```json
{
  "date": "2025-06-28",
  "slot": "09:00-09:30", 
  "filename": "09-00.wav",
  "duration_seconds": 50,
  "features_timeline": [
    {
      "timestamp": "09:00:00",
      "features": {
        "Loudness_sma3": 0.06019328162074089,
        "F0semitoneFrom27.5Hz_sma3nz": 0.0,
        "alphaRatio_sma3": -7.842461109161377,
        "hammarbergIndex_sma3": 16.497520446777344,
        "mfcc1_sma3": 8.365259170532227,
        "F1frequency_sma3nz": 788.834228515625,
        "F2frequency_sma3nz": 1727.9415283203125,
        "F3frequency_sma3nz": 2660.05126953125
      }
    }
  ],
  "processing_time": 0.94,
  "error": null
}
```

## リクエスト・レスポンス形式

### Vault API連携リクエスト

```json
{
  "device_id": "device123",
  "date": "2025-06-25"
}
```

### 特徴量タイムライン分析レスポンス例

```json
{
  "success": true,
  "feature_set": "eGeMAPSv02", 
  "processed_files": 1,
  "results": [
    {
      "date": "2025-06-28",
      "slot": "09:00-09:30",
      "filename": "09-00.wav",
      "duration_seconds": 51,
      "features_timeline": [
        {
          "timestamp": "09:00:00",
          "features": {
            "Loudness_sma3": 0.114,
            "F0semitoneFrom27.5Hz_sma3nz": 8.861,
            "alphaRatio_sma3": -12.275,
            "hammarbergIndex_sma3": 20.948,
            "mfcc1_sma3": 17.559,
            "F1frequency_sma3nz": 733.330,
            "F2frequency_sma3nz": 1745.846,
            "F3frequency_sma3nz": 2674.963
          }
        }
      ]
    }
  ],
  "total_processing_time": 1.2
}
```

## ディレクトリ構造

```
opensmile/
├── main.py              # FastAPIアプリケーション
├── models.py            # Pydanticモデル定義
├── services.py          # OpenSMILE・Vault APIサービス
├── requirements.txt     # 依存関係
├── Dockerfile          # Docker設定
└── README.md           # このファイル
```

## 技術仕様

### 依存関係

- **FastAPI 0.104.1** - WebAPIフレームワーク
- **OpenSMILE 2.5.1** - 音響特徴量抽出ライブラリ
- **Pandas 2.0.3** - データ処理
- **Pydantic 2.5.0** - データ検証・シリアライゼーション
- **aiohttp 3.9.1** - Vault API連携用

### 対応特徴量セット

- **eGeMAPSv02**: 88特徴量（固定）

### 特徴量タイムライン

1秒ごとのeGeMAPSv02特徴量を抽出：
- **Loudness_sma3**: 音声の音量
- **F0semitoneFrom27.5Hz_sma3nz**: 基本周波数（半音階）
- **alphaRatio_sma3**: アルファ比（スペクトル特性）
- **hammarbergIndex_sma3**: ハンマーバーグインデックス
- **mfcc1-4_sma3**: メル周波数ケプストラム係数
- **F1-F3frequency_sma3nz**: フォルマント周波数
- **その他**: jitter、shimmer、HNR等の音響特徴量

## 開発

### Docker使用

```bash
# イメージビルド
docker build -t opensmile-vault-api .

# コンテナ実行
docker run -p 8011:8011 opensmile-vault-api
```

## 注意事項

- WAVファイルは16kHz、16bit、モノラルを推奨
- 大きなファイルの処理には時間がかかる場合があります
- 特徴量セットはeGeMAPSv02に固定されています

## 変更履歴

### v3.0.0 (2025-07-05)
- **エンドポイント簡略化**: `/process/vault-data`のみに統一
- **特徴量セット固定**: eGeMAPSv02のみ対応  
- **user_id → device_id変更**: Whisper APIと統一したデバイスベース識別
- **不要機能削除**: ローカルファイル処理、感情分析、エクスポート機能を削除
- **Vault API特化**: Vault連携に機能を集約
- **動作確認完了**: device_id `d067d407-cf73-4174-a9c1-d91fb60d64d0` での実データ処理成功
# OpenSMILE感情分析API

OpenSMILEライブラリを使用した音声特徴量抽出と感情分析のためのFastAPIベースのAPIサービスです。

## 概要

このAPIは音声ファイル（WAV形式）から音響特徴量を抽出し、感情分析を行います。

### 主要機能

- **音声特徴量抽出**: OpenSMILEを使用した88種類の音響特徴量抽出（eGeMAPSv02）
- **感情分析**: ルールベースによる5感情分類（happy, sad, angry, neutral, excited）
- **複数の特徴量セット対応**: eGeMAPSv02, ComParE_2016, GeMAPSなど
- **バッチ処理**: 複数のWAVファイルを一括処理
- **JSON出力**: 分析結果をJSONファイルで保存・エクスポート

## API仕様

### 基本エンドポイント

- `GET /` - API情報
- `GET /health` - ヘルスチェック
- `GET /docs` - Swagger UIドキュメント

### ファイル・特徴量関連

- `GET /files` - カレントディレクトリのWAVファイル一覧
- `GET /features` - 利用可能な特徴量セット一覧
- `POST /extract` - 音声特徴量抽出
- `POST /analyze` - 感情分析

### エクスポート・ダウンロード

- `POST /export` - 分析結果のJSONエクスポート
- `GET /download/{filename}` - JSONファイルダウンロード
- `GET /results` - 分析結果ファイル一覧

### Vault API連携エンドポイント（NEW v4.0.0）

- `POST /process/vault-data` - EC2 Vault APIからWAVファイルを取得して特徴量タイムラインを抽出

### test-data専用エンドポイント

- `GET /test-data/files` - test-dataフォルダ内のファイル一覧

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
- **このAPIはポート8011で動作します**（ポート8000との競合を避けるため）
- **Python3を使用してください**（`python`ではなく`python3`コマンドを使用）

### Vault API連携エンドポイントの使用例（NEW）

```bash
# EC2 Vault APIからWAVファイルを取得して特徴量タイムライン抽出
curl -X POST http://localhost:8011/process/vault-data \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "date": "2025-06-25",
    "feature_set": "eGeMAPSv02",
    "include_raw_features": false
  }'

# test-dataフォルダ内のファイル確認
curl http://localhost:8011/test-data/files
```

**Vault API連携の特徴:**
- EC2 Vault APIから自動でWAVファイルを取得
- 個別ファイル保存: `20-30.wav` → `20-30.json`
- 複数ファイル対応: 各WAVファイルごとに対応するJSONファイルを作成
- 完全なeGeMAPS特徴量（25個）を1秒ごとのタイムラインで出力

**個別JSONファイル出力例 (20-30.json):**
```json
{
  "date": "2025-06-28",
  "slot": "08:20-08:30", 
  "filename": "20-30.wav",
  "duration_seconds": 50,
  "features_timeline": [
    {
      "timestamp": "08:00:00",
      "features": {
        "Loudness_sma3": 0.06019328162074089,
        "F0semitoneFrom27.5Hz_sma3nz": 0.0,
        "alphaRatio_sma3": -7.842461109161377,
        "hammarbergIndex_sma3": 16.497520446777344,
        "mfcc1_sma3": 8.365259170532227,
        "F1frequency_sma3nz": 788.834228515625,
        "F2frequency_sma3nz": 1727.9415283203125,
        "F3frequency_sma3nz": 2660.05126953125,
        "(25個の完全なeGeMAPS特徴量)": "..."
      }
    }
  ],
  "processing_time": 0.94,
  "error": null
}
```

### 基本的な使用例

```bash
# ヘルスチェック
curl http://localhost:8011/health

# 利用可能な特徴量セット確認
curl http://localhost:8011/features

# カレントディレクトリのWAVファイル一覧
curl http://localhost:8011/files

# 感情分析実行
curl -X POST http://localhost:8011/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "feature_set": "eGeMAPSv02",
    "include_raw_features": false
  }'

# 特徴量抽出のみ
curl -X POST http://localhost:8011/extract \
  -H "Content-Type: application/json" \
  -d '{
    "feature_set": "eGeMAPSv02",
    "include_raw_features": true
  }'
```

## リクエスト・レスポンス形式

### 特徴量抽出リクエスト

```json
{
  "feature_set": "eGeMAPSv02",
  "include_raw_features": true
}
```

### Vault API連携リクエスト（NEW）

```json
{
  "user_id": "user123",
  "date": "2025-06-25",
  "feature_set": "eGeMAPSv02", 
  "include_raw_features": false
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
      "slot": "08:20-08:30",
      "filename": "20-30.wav",
      "duration_seconds": 51,
      "features_timeline": [
        {
          "timestamp": "08:00:00",
          "features": {
            "Loudness_sma3": 0.114,
            "F0semitoneFrom27.5Hz_sma3nz": 8.861,
            "alphaRatio_sma3": -12.275,
            "hammarbergIndex_sma3": 20.948,
            "mfcc1_sma3": 17.559,
            "F1frequency_sma3nz": 733.330,
            "F2frequency_sma3nz": 1745.846,
            "F3frequency_sma3nz": 2674.963,
            "(25個のeGeMAPS特徴量)": "..."
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
├── services.py          # OpenSMILE・感情分析サービス
├── test_api.py          # APIテスト
├── requirements.txt     # 依存関係
├── Dockerfile          # Docker設定
├── test-data/          # テストデータフォルダ
│   ├── 20-30.wav       # サンプル音声ファイル
│   └── *.json          # 分析結果ファイル（自動生成）
└── README.md           # このファイル
```

## 技術仕様

### 依存関係

- **FastAPI 0.104.1** - WebAPIフレームワーク
- **OpenSMILE 2.5.1** - 音響特徴量抽出ライブラリ
- **Pandas 2.0.3** - データ処理
- **Pydantic 2.5.0** - データ検証・シリアライゼーション

### 対応特徴量セット

- **eGeMAPSv02** (推奨): 88特徴量
- **ComParE_2016**: 6373特徴量
- **GeMAPS**: 62特徴量
- **eGeMAPS**: 88特徴量
- **emobase**: 感情分析特化特徴量セット

### 特徴量タイムライン（NEW v3.0.0）

1秒ごとのeGeMAPS特徴量を抽出：
- **Loudness_sma3**: 音声の音量
- **F0semitoneFrom27.5Hz_sma3nz**: 基本周波数（半音階）
- **alphaRatio_sma3**: アルファ比（スペクトル特性）
- **hammarbergIndex_sma3**: ハンマーバーグインデックス
- **mfcc1-4_sma3**: メル周波数ケプストラム係数
- **F1-F3frequency_sma3nz**: フォルマント周波数
- **その他**: jitter、shimmer、HNR等の音響特徴量

## 開発

### テスト実行

```bash
# Python3環境でテスト実行
python3 -m pytest test_api.py -v
```

### Docker使用

```bash
# イメージビルド
docker build -t opensmile-api .

# コンテナ実行
docker run -p 8011:8011 opensmile-api
```

## 注意事項

- WAVファイルは16kHz、16bit、モノラルを推奨
- 大きなファイルの処理には時間がかかる場合があります
- 感情分析は現在ルールベースの簡易実装です（将来的に機械学習モデルに置き換え予定）

## 変更履歴

### v3.0.0 (2025-06-28)
- **特徴量タイムライン機能**: 1秒ごとのeGeMAPS特徴量抽出
- **処理ステップ分離**: 特徴量抽出と感情分析を完全分離
- **新出力形式**: `features_timeline_*.json`で素データ出力
- **Plutchik8感情対応**: 感情分析モデル（将来実装用）
- **ポート変更**: 8000 → 8011（競合回避）

### v2.0.0 (2024-12-28)
- test-data専用エンドポイント追加（`/process/test-data`, `/test-data/files`）
- Flask版app.py削除、FastAPI完全移行
- Pydantic V2対応（`.dict()` → `.model_dump()`）
- test-dataフォルダへの自動JSONファイル保存機能

### v1.0.0
- 初回リリース
- OpenSMILE特徴量抽出機能
- 基本的な感情分析機能
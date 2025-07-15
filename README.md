# OpenSMILE Supabase統合サービス

OpenSMILEライブラリを使用したVault API連携による音声特徴量抽出サービスです。処理結果はSupabaseに直接保存されます。

## 概要

このAPIはVault APIから音声ファイル（WAV形式）を取得し、音響特徴量を抽出してSupabaseのemotion_opensmileテーブルに保存します。

### 主要機能

- **Vault API連携**: EC2 Vault APIからWAVファイル自動取得
- **音声特徴量抽出**: OpenSMILEを使用したeGeMAPSv02特徴量抽出（25種類）
- **タイムライン出力**: 1秒ごとの詳細特徴量タイムライン
- **Supabase統合**: 処理結果をSupabaseに直接保存（30分スロットごと）

## API仕様

### エンドポイント

- `GET /` - API情報
- `GET /health` - ヘルスチェック
- `GET /docs` - Swagger UIドキュメント
- `POST /process/vault-data` - Vault API連携による音声特徴量抽出

## 使用方法

### ローカル開発環境での起動

```bash
# 1. 依存関係のインストール (Python3を使用)
#    プロジェクトルートで実行してください
pip3 install -r requirements.txt

# 2. 環境変数の設定
#    プロジェクトルートに .env ファイルを作成し、Supabaseの接続情報を記述します。
#    例:
#    SUPABASE_URL=https://your-project.supabase.co
#    SUPABASE_KEY=your-supabase-anon-key

# 3. サーバー起動 (開発モード、ポート8011を使用)
#    コード変更時に自動でリロードされます
uvicorn main:app --host 0.0.0.0 --port 8011 --reload

# または、手動で起動する場合
# python3 main.py
```

**注意事項:**
- **このAPIはポート8011で動作します**
- **Python3を使用してください**（`python`ではなく`python3`コマンドを使用）
- `.env`ファイルはGit管理から除外されています。機密情報を含めるため、手動で作成・管理してください。

### 本番環境へのデプロイ (Docker & systemd)

本番環境では、Dockerコンテナとしてデプロイし、`systemd`で常時起動させることを推奨します。

#### 1. 本番サーバーでのDockerイメージのビルド

本番サーバー（EC2）にSSH接続してDockerイメージをビルドします。

```bash
# SSH接続
ssh -i ~/watchme-key.pem ubuntu@3.24.16.82

# プロジェクトディレクトリに移動
cd /home/ubuntu/opensmile

# requirements.txtの依存関係を確認・修正
# httpx==0.25.2 → httpx==0.26.0 に変更（supabaseとの互換性のため）
sudo sed -i 's/httpx==0.25.2/httpx==0.26.0/' requirements.txt

# Dockerイメージをビルド
sudo docker build -t watchme-opensmile-api:latest .
```

**注意事項:**
- httpxのバージョンは0.26.0以上が必要です（supabase 2.10.0との互換性のため）
- ビルドには数分かかる場合があります

#### 2. 環境変数の設定

サーバーの`/home/ubuntu/opensmile/`ディレクトリに`.env`ファイルを作成し、Supabaseの接続情報を記述します。

```bash
# .envファイルを作成
sudo tee /home/ubuntu/opensmile/.env > /dev/null << 'EOF'
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key
EOF

# パーミッションを安全に設定 (rootのみ読み書き可能)
sudo chmod 600 /home/ubuntu/opensmile/.env
```

**注意事項:**
- .envファイルには正しいSupabaseの認証情報を設定してください
- ファイルの最後に余分な行や重複した設定がないことを確認してください

#### 3. systemdサービスの設定

`/etc/systemd/system/opensmile-api.service`に以下の内容でサービスファイルを作成します。

```ini
[Unit]
Description=OpenSMILE API Docker Container
After=docker.service
Requires=docker.service

[Service]
TimeoutStartSec=0
Restart=always
RestartSec=5
# 既存のコンテナがあれば停止・削除してから起動
ExecStartPre=-/usr/bin/docker stop opensmile-api
ExecStartPre=-/usr/bin/docker rm opensmile-api
# Dockerコンテナを起動。ホストの8011ポートをコンテナの8000ポートにマッピング。
# --env-file で .env ファイルから環境変数を読み込みます。
ExecStart=/usr/bin/docker run --name opensmile-api -p 8011:8000 --env-file /home/ubuntu/opensmile/.env watchme-opensmile-api:latest
# EnvironmentFileで環境変数を読み込む
EnvironmentFile=/home/ubuntu/opensmile/.env

[Install]
WantedBy=multi-user.target
```

#### 4. systemdサービスの有効化と起動

サービスファイルを配置したら、`systemd`に設定を読み込ませ、サービスを有効化・起動します。

```bash
# systemdデーモンをリロード
sudo systemctl daemon-reload

# サービスを有効化 (サーバー起動時に自動で立ち上がるように)
sudo systemctl enable opensmile-api.service

# サービスを起動
sudo systemctl start opensmile-api.service

# サービスのステータスを確認
sudo systemctl status opensmile-api.service
```

#### 5. Nginxリバースプロキシの設定

外部からAPIにアクセスできるよう、Nginxの設定を行います。

```bash
# Nginx設定ファイルに emotion-features エンドポイントを追加
# /etc/nginx/sites-available/api.hey-watch.me に以下のlocationブロックを追加:

# OpenSMILE API (emotion-features)
location /emotion-features/ {
    proxy_pass http://localhost:8011/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    
    # CORS設定
    add_header "Access-Control-Allow-Origin" "*";
    add_header "Access-Control-Allow-Methods" "GET, POST, OPTIONS";
    add_header "Access-Control-Allow-Headers" "Content-Type, Authorization";
    
    # OPTIONSリクエストの処理
    if ($request_method = "OPTIONS") {
        return 204;
    }
}

# Nginx設定をテスト
sudo nginx -t

# Nginxをリロード
sudo systemctl reload nginx
```

### 本番環境でのAPIアクセス

本番環境のAPIは以下のURLでアクセス可能です：

- **エンドポイント**: https://api.hey-watch.me/emotion-features/
- **ヘルスチェック**: https://api.hey-watch.me/emotion-features/health
- **APIドキュメント**: https://api.hey-watch.me/emotion-features/docs

### Vault API連携エンドポイントの使用例

```bash
# ローカル環境から直接サーバーのAPIを呼び出す場合
curl -X POST http://3.24.16.82:8011/process/vault-data \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "d067d407-cf73-4174-a9c1-d91fb60d64d0",
    "date": "2025-07-15"
  }'

# 本番環境のAPIエンドポイントを使用する場合（推奨）
curl -X POST https://api.hey-watch.me/emotion-features/process/vault-data \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "d067d407-cf73-4174-a9c1-d91fb60d64d0",
    "date": "2025-07-15"
  }'
```

**処理フロー:**
1. Vault APIから指定日付のWAVファイルを取得
2. OpenSMILEで1秒ごとの特徴量タイムライン抽出
3. Supabaseのemotion_opensmileテーブルに30分スロットごとにUPSERT保存

**Supabaseテーブル構造 (emotion_opensmile):**
```sql
CREATE TABLE emotion_opensmile (
  device_id         text NOT NULL,
  date              date NOT NULL,
  time_block        text NOT NULL CHECK (time_block ~ '^[0-2][0-9]-[0-5][0-9]),
  filename          text,
  duration_seconds  integer,
  features_timeline jsonb NOT NULL,  -- timestamp + features のリスト
  processing_time   double precision,
  error             text,
  PRIMARY KEY (device_id, date, time_block)
);
```

**features_timeline JSONBフォーマット例:**
```json
[
  {
    "timestamp": "09:00:00",
    "features": {
      "Loudness_sma3": 0.06019328162074089,
      "F0semitoneFrom27.5Hz_sma3nz": 0.0,
      "alphaRatio_sma3": -7.842461109161377,
      "hammarbergIndex_sma3": 16.497520446777344,
      "mfcc1_sma3": 8.365259170532227,
      "F1frequency_sma3nz": 788.834228516,
      "F2frequency_sma3nz": 1727.94152832,
      "F3frequency_sma3nz": 2660.05126953
    }
  }
]
```

## リクエスト・レスポンス形式

### Vault API連携リクエスト

```json
{
  "device_id": "device123",
  "date": "2025-06-25"
}
```

### 処理結果レスポンス例

```json
{
  "success": true,
  "test_data_directory": "Supabase: emotion_opensmile table",
  "feature_set": "eGeMAPSv02",
  "processed_files": 2,
  "saved_files": ["00-00.json", "21-30.json"],
  "results": [
    {
      "date": "2025-07-08",
      "slot": "00-00",
      "filename": "00-00.wav",
      "duration_seconds": 67,
      "features_timeline": [
        {
          "timestamp": "00:00:00",
          "features": {
            "Loudness_sma3": 0.114,
            "F0semitoneFrom27.5Hz_sma3nz": 8.861,
            "alphaRatio_sma3": -12.275,
            "hammarbergIndex_sma3": 20.948,
            "mfcc1_sma3": 17.559
          }
        }
      ],
      "processing_time": 0.79,
      "error": null
    }
  ],
  "total_processing_time": 11.41,
  "message": "Vault APIから2個のWAVファイルを取得し、2個のレコードをSupabaseに保存しました"
}
```

## ディレクトリ構造

```
opensmile/
├── main.py                      # FastAPIアプリケーション
├── models.py                    # Pydanticモデル定義
├── services.py                  # OpenSMILE・Vault APIサービス
├── supabase_service.py          # Supabaseサービス
├── requirements.txt             # 依存関係
├── .env                         # 環境変数（Supabase接続情報）
├── test_supabase_integration.py # Supabase統合テスト
├── process_date.py              # 日付指定処理スクリプト
├── check_supabase_data.py       # Supabaseデータ確認スクリプト
├── Dockerfile                   # Docker設定
└── README.md                    # このファイル
```

## 技術仕様

### 依存関係

- **FastAPI 0.104.1** - WebAPIフレームワーク
- **OpenSMILE 2.5.1** - 音響特徴量抽出ライブラリ
- **Pandas 2.0.3** - データ処理
- **Pydantic 2.5.0** - データ検証・シリアライゼーション
- **aiohttp 3.9.1** - Vault API連携用
- **supabase 2.10.0** - Supabaseクライアント
- **python-dotenv 1.0.1** - 環境変数管理

### 対応特徴量セット

- **eGeMAPSv02**: 25特徴量（固定）

### 特徴量タイムライン

1秒ごとのeGeMAPSv02特徴量を抽出：
- **Loudness_sma3**: 音声の音量
- **F0semitoneFrom27.5Hz_sma3nz**: 基本周波数（半音階）
- **alphaRatio_sma3**: アルファ比（スペクトル特性）
- **hammarbergIndex_sma3**: ハンマーバーグインデックス
- **mfcc1-4_sma3**: メル周波数ケプストラム係数
- **F1-F3frequency_sma3nz**: フォルマント周波数
- **その他**: jitter、shimmer、HNR等の音響特徴量（全25種類）

### 環境変数設定

`.env`ファイルに以下を設定：
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key
```

## トラブルシューティング

### Dockerビルドエラー

httpxの依存関係エラーが発生する場合：
```bash
# requirements.txtを修正
sed -i 's/httpx==0.25.2/httpx==0.26.0/' requirements.txt
```

### Supabase接続エラー

"Invalid API key"エラーが発生する場合：
- .envファイルの内容を確認（余分な行や重複がないか）
- SUPABASE_URLとSUPABASE_KEYが正しく設定されているか確認

### systemdサービスの確認

```bash
# ログを確認
sudo journalctl -u opensmile-api.service -f

# サービスの再起動
sudo systemctl restart opensmile-api.service
```

## 開発

### Docker使用

```bash
# イメージビルド
docker build -t opensmile-vault-api .

# コンテナ実行
docker run -p 8011:8000 --env-file .env opensmile-vault-api
```

## 注意事項

- WAVファイルは16kHz、16bit、モノラルを推奨
- 大きなファイルの処理には時間がかかる場合があります
- 特徴量セットはeGeMAPSv02に固定されています

## 使用例

### 日付指定処理スクリプト

```bash
# 特定の日付のデータを処理
python3 process_date.py d067d407-cf73-4174-a9c1-d91fb60d64d0 2025-07-08

# または対話式
python3 process_date.py
```

### Supabaseデータ確認

```bash
# 保存されたデータの確認
python3 check_supabase_data.py d067d407-cf73-4174-a9c1-d91fb60d64d0 2025-07-08
```

### Supabase統合テスト

```bash
# 接続とUPSERT機能をテスト
python3 test_supabase_integration.py
```

## 変更履歴

### v4.1.0 (2025-07-15) - 本番環境デプロイ
- **本番環境への正式デプロイ**: EC2サーバー（3.24.16.82）にDocker + systemdで展開
- **HTTPSエンドポイント追加**: https://api.hey-watch.me/emotion-features/ でアクセス可能
- **依存関係の修正**: httpxを0.26.0にアップグレード（supabase 2.10.0との互換性確保）
- **Nginx設定追加**: リバースプロキシ設定でCORS対応も実装
- **動作確認完了**: 
  - `d067d407-cf73-4174-a9c1-d91fb60d64d0` (2025-07-15): 2スロット処理成功（14:00-14:30, 15:30-16:00）

### v4.0.0 (2025-07-09)
- **Supabase統合**: ローカルファイル保存・Vaultアップロード処理を削除
- **UPSERT機能**: emotion_opensmileテーブルに30分スロットごとに直接保存
- **バッチ処理**: 複数レコードの効率的な一括保存
- **動作確認完了**: 
  - `user123` (2025-06-21): 5スロット処理成功
  - `d067d407-cf73-4174-a9c1-d91fb60d64d0` (2025-07-08): 2スロット処理成功

### v3.0.0 (2025-07-05)
- **エンドポイント簡略化**: `/process/vault-data`のみに統一
- **特徴量セット固定**: eGeMAPSv02のみ対応  
- **user_id → device_id変更**: Whisper APIと統一したデバイスベース識別
- **不要機能削除**: ローカルファイル処理、感情分析、エクスポート機能を削除
- **Vault API特化**: Vault連携に機能を集約

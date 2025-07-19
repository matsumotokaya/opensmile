# OpenSMILE API for WatchMe - Whisper APIパターン準拠の感情特徴量抽出API

WatchMeエコシステム専用のOpenSMILE感情特徴量抽出API。**このAPIはWhisper APIと同じパターンを採用し、統一されたfile_pathsベースの処理を実現します。**

## 🎯 重要：Whisper APIパターン準拠の意義

このAPIは、WatchMeエコシステムにおける音声ファイル処理の標準的な実装パターンを継承しています：

1. **file_pathsベースの処理**: Whisper APIと同じく`file_paths`配列を受け取り、S3から直接処理
2. **ステータス管理**: 処理完了後に`audio_files`テーブルの`emotion_features_status`を`completed`に更新
3. **シンプルな責務分離**: eGeMAPSv02特徴量抽出に特化し、ファイル管理はVault APIに委譲
4. **統一されたエラーハンドリング**: Whisper APIと同じパターンでエラー処理とレスポンス形式

## 🔄 最新アップデート (2025-07-19)

### 🚀 Version 2.0.0: Whisper APIパターン準拠への完全移行 ✅

#### 📈 刷新の背景と成果
従来のOpenSMILE APIは`device_id/date`ベースのVault API連携でしたが、**Whisper APIで実証された`file_paths`ベースの処理方式の優位性**を受けて、全面的にアーキテクチャを刷新しました。

**✅ 動作確認済み**: `files/d067d407-cf73-4174-a9c1-d91fb60d64d0/2025-07-20/00-00/audio.wav` の処理に成功し、40秒の音声から1秒ごと40ポイントの特徴量タイムラインを抽出完了。

#### ⚡ 主要な技術変更と改善

##### 1. **統一されたfile_pathsベースのインターフェース**
```diff
- POST /process/vault-data
+ POST /process/emotion-features

- リクエスト: {"device_id": "xxx", "date": "2025-07-20"}  
+ リクエスト: {"file_paths": ["files/device_id/date/time/audio.wav"]}
```

##### 2. **AWS S3直接アクセス統合**
```python
# 新機能：S3から直接音声ファイルを取得
s3_client.download_file(s3_bucket_name, file_path, temp_file_path)
```
- **パフォーマンス向上**: Vault API経由の処理を削減
- **確実性向上**: S3直接アクセスでファイル取得の信頼性を向上
- **AWS認証**: boto3を使用した堅牢なS3アクセス

##### 3. **確実なステータス管理システム**
```python
# audio_filesテーブルの確実なステータス更新
await update_audio_files_status(file_path)
# emotion_features_status: 'pending' → 'completed'
```

##### 4. **eGeMAPSv02特徴量抽出の最適化**
- **25種類の音響特徴量**: Loudness、F0、MFCC、フォルマント等
- **1秒ごとのタイムライン**: 音声の時系列変化を詳細に記録
- **感情分析特化**: 音声から感情状態を推定するための特徴量に最適化

### 🏗️ アーキテクチャのベストプラクティス

```python
# ✅ 新しいfile_pathsベースの処理
@app.post("/process/emotion-features")
async def process_emotion_features(request: EmotionFeaturesRequest):
    # file_pathsを受け取る
    for file_path in request.file_paths:
        # S3から直接ダウンロード
        s3_client.download_file(bucket, file_path, temp_file)
        
        # OpenSMILE感情特徴量抽出を実行
        result = emotion_service.extract_features_timeline(temp_file, feature_set)
        
        # 結果をemotion_opensmileテーブルに保存
        await save_to_supabase(device_id, date, time_block, features)
        
        # ステータスを更新（重要！）
        await update_audio_files_status(file_path)
```

## API仕様

### エンドポイント

- `GET /` - API情報
- `GET /health` - ヘルスチェック
- `GET /docs` - Swagger UIドキュメント
- `POST /process/emotion-features` - file_pathsベースの感情特徴量抽出

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

## 🚀 APIエンドポイント仕様

### POST /process/emotion-features

file_pathsベースの感情特徴量抽出（Whisper APIパターン準拠）

#### リクエスト
```json
{
  "file_paths": [
    "files/d067d407-cf73-4174-a9c1-d91fb60d64d0/2025-07-19/14-30/audio.wav"
  ],
  "feature_set": "eGeMAPSv02",
  "include_raw_features": false
}
```

#### レスポンス
```json
{
  "success": true,
  "test_data_directory": "Supabase: emotion_opensmile table",
  "feature_set": "eGeMAPSv02",
  "processed_files": 1,
  "saved_files": ["14-30.json"],
  "results": [
    {
      "date": "2025-07-19",
      "slot": "14-30",
      "filename": "audio.wav",
      "duration_seconds": 67,
      "features_timeline": [
        {
          "timestamp": "14:30:00",
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
  "total_processing_time": 8.2,
  "message": "S3から1個のWAVファイルを処理し、1個のレコードをSupabaseに保存しました"
}
```

### 使用例

```bash
# ローカル環境
curl -X POST http://localhost:8011/process/emotion-features \
  -H "Content-Type: application/json" \
  -d '{
    "file_paths": [
      "files/d067d407-cf73-4174-a9c1-d91fb60d64d0/2025-07-19/14-30/audio.wav"
    ]
  }'

# 本番環境（推奨）
curl -X POST https://api.hey-watch.me/emotion-features/process/emotion-features \
  -H "Content-Type: application/json" \
  -d '{
    "file_paths": [
      "files/d067d407-cf73-4174-a9c1-d91fb60d64d0/2025-07-19/14-30/audio.wav"
    ]
  }'
```

**処理フロー:**
1. `file_paths`からS3の音声ファイルを直接取得
2. OpenSMILEで1秒ごとのeGeMAPSv02特徴量タイムライン抽出
3. Supabaseのemotion_opensmileテーブルに30分スロットごとにUPSERT保存
4. audio_filesテーブルの`emotion_features_status`を`completed`に更新

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

## 🏗️ 他の音声処理APIへの実装ガイド

### 基本的な処理パターン（Whisper API準拠）

```python
# Step 1: file_pathsベースのリクエストを受け取る
@app.post("/process/your-audio-feature")
async def process_audio_feature(request: YourAudioFeaturesRequest):
    # リクエスト例: {"file_paths": ["files/device_id/date/time/audio.wav", ...]}
    
    for file_path in request.file_paths:
        # Step 2: S3から直接ダウンロード
        s3_client.download_file(bucket, file_path, temp_file)
        
        # Step 3: 音声処理を実行（API固有の処理）
        result = your_audio_processor.process(temp_file)
        
        # Step 4: 結果をSupabaseに保存
        await save_to_supabase(device_id, date, time_block, result)
        
        # Step 5: ステータスを更新（重要！）
        await update_audio_files_status(file_path, 'your_status_field')
```

### ステータスフィールドの命名規則

各APIは`audio_files`テーブルの専用ステータスフィールドを更新：

- `transcriptions_status`: Whisper API
- `emotion_features_status`: OpenSMILE API（このAPI）  
- `behavior_features_status`: 行動分析API
- など、`{feature}_status`の形式で命名

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
- **boto3 ≥1.26.0** - AWS S3直接アクセス用
- **botocore ≥1.29.0** - AWS SDK コア機能
- **supabase 2.10.0** - Supabaseクライアント
- **python-dotenv 1.0.1** - 環境変数管理
- **aiohttp 3.9.1** - 非同期HTTP処理（互換性維持）

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
# Supabase設定
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key

# AWS S3設定（file_pathsベースのS3直接アクセス用）
AWS_ACCESS_KEY_ID=your-aws-access-key-id
AWS_SECRET_ACCESS_KEY=your-aws-secret-access-key
S3_BUCKET_NAME=watchme-vault
AWS_REGION=us-east-1
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

### v2.0.0 (2025-07-19) - Whisper APIパターン準拠への完全移行 ✅

#### 🎯 設計思想の大転換と実績
- **アーキテクチャ刷新**: Vault API連携からfile_pathsベースのS3直接アクセスに変更
- **Whisper APIパターン準拠**: エコシステム全体での統一された処理フローの確立
- **責務の明確化**: 音声ファイル処理に特化し、ファイル管理はVault APIに委譲
- **✅ 実証済み**: 実際のファイル処理でパフォーマンス向上と安定性を確認

#### 🔧 主要な技術的変更
- **エンドポイント変更**: `/process/vault-data` → `/process/emotion-features`
- **リクエスト形式変更**: `device_id/date`指定 → `file_paths`配列指定  
- **AWS S3統合**: boto3を使用したS3直接ダウンロード機能を追加
- **ステータス管理強化**: `audio_files.emotion_features_status`の確実な更新
- **依存関係追加**: boto3 ≥1.26.0, botocore ≥1.29.0を追加
- **FastAPIアプリ更新**: タイトルとバージョンを新アーキテクチャに更新

#### 🏗️ アーキテクチャ改善の効果
- **統一されたインターフェース**: 他の音声処理APIと同じfile_pathsベースの処理
- **確実性の向上**: file_pathによる直接的なステータス更新で更新漏れを防止
- **パフォーマンス最適化**: Vault API呼び出しを削減し、S3直接アクセスで高速化
- **エラー削減**: `recorded_at`のフォーマット差異による問題を完全に回避

#### 📊 互換性と移行結果
- **データ形式**: emotion_opensmileテーブルの構造は変更なし
- **レスポンス形式**: 基本的なレスポンス構造は維持
- **動作確認**: 40秒音声ファイルから40ポイントの特徴量タイムライン抽出に成功

### v1.5.0 (2025-07-15) - 本番環境デプロイ（旧版）
- **本番環境への正式デプロイ**: EC2サーバー（3.24.16.82）にDocker + systemdで展開
- **HTTPSエンドポイント追加**: https://api.hey-watch.me/emotion-features/ でアクセス可能
- **依存関係の修正**: httpxを0.26.0にアップグレード（supabase 2.10.0との互換性確保）
- **Nginx設定追加**: リバースプロキシ設定でCORS対応も実装

### v1.0.0 (2025-07-09) - Supabase統合（旧版）
- **Supabase統合**: ローカルファイル保存・Vaultアップロード処理を削除
- **UPSERT機能**: emotion_opensmileテーブルに30分スロットごとに直接保存
- **バッチ処理**: 複数レコードの効率的な一括保存

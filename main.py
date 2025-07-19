"""
FastAPI感情分析API
OpenSMILEを使用した音声特徴量抽出と感情分析
"""

import time
import os
import tempfile
from pathlib import Path
from typing import List
import aiohttp
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from supabase import create_client, Client

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import opensmile

from models import (
    HealthResponse,
    ErrorResponse,
    FeaturesTimelineResponse,
    EmotionFeaturesRequest
)
from services import EmotionAnalysisService, VaultAPIService
from supabase_service import SupabaseService

# FastAPIアプリケーションの初期化
app = FastAPI(
    title="OpenSMILE API - Whisper APIパターン準拠",
    description="OpenSMILEを使用したfile_pathsベースの感情特徴量抽出サービス（Whisper APIパターン準拠）",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORSミドルウェアの設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番環境では適切なオリジンを指定
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 環境変数の読み込み
load_dotenv()

# Supabaseクライアントの初期化
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
if supabase_url and supabase_key:
    supabase_client: Client = create_client(supabase_url, supabase_key)
    supabase_service = SupabaseService(supabase_client)
    print(f"Supabase接続設定完了: {supabase_url}")
else:
    supabase_service = None
    print("⚠️ Supabase環境変数が設定されていません")

# AWS S3クライアントの初期化
aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
s3_bucket_name = os.getenv('S3_BUCKET_NAME', 'watchme-vault')
aws_region = os.getenv('AWS_REGION', 'us-east-1')

if not aws_access_key_id or not aws_secret_access_key:
    raise ValueError("AWS_ACCESS_KEY_IDおよびAWS_SECRET_ACCESS_KEYが設定されていません")

s3_client = boto3.client(
    's3',
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key,
    region_name=aws_region
)
print(f"AWS S3接続設定完了: バケット={s3_bucket_name}, リージョン={aws_region}")

# サービスの初期化
emotion_service = EmotionAnalysisService()
vault_service = VaultAPIService()  # 互換性のため残しておく


def extract_info_from_file_path(file_path: str) -> dict:
    """ファイルパスからデバイス情報を抽出
    
    Args:
        file_path: 'files/device_id/date/time/audio.wav' 形式
        
    Returns:
        dict: {'device_id': str, 'date': str, 'time_block': str}
    """
    parts = file_path.split('/')
    if len(parts) >= 5:
        return {
            'device_id': parts[1],
            'date': parts[2], 
            'time_block': parts[3]
        }
    else:
        raise ValueError(f"不正なファイルパス形式: {file_path}")


async def update_audio_files_status(file_path: str) -> bool:
    """audio_filesテーブルのemotion_features_statusを更新
    
    Args:
        file_path: 処理完了したファイルのパス
        
    Returns:
        bool: 更新成功可否
    """
    try:
        update_response = supabase_client.table('audio_files') \
            .update({'emotion_features_status': 'completed'}) \
            .eq('file_path', file_path) \
            .execute()
        
        if update_response.data:
            print(f"✅ ステータス更新成功: {file_path}")
            return True
        else:
            print(f"⚠️ 対象レコードが見つかりません: {file_path}")
            return False
            
    except Exception as e:
        print(f"❌ ステータス更新エラー: {str(e)}")
        return False


@app.get("/", response_model=dict)
async def root():
    """ルートエンドポイント"""
    return {
        "message": "OpenSMILE API - Whisper APIパターン準拠",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """ヘルスチェックエンドポイント"""
    try:
        # OpenSMILEの動作確認
        opensmile_version = opensmile.__version__
        
        return HealthResponse(
            status="healthy",
            service="OpenSMILE API - Whisper APIパターン準拠",
            version="2.0.0",
            opensmile_version=opensmile_version
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service unhealthy: {str(e)}"
        )


@app.post("/process/emotion-features", response_model=FeaturesTimelineResponse)
async def process_emotion_features(request: EmotionFeaturesRequest):
    """file_pathsベースの感情特徴量抽出（Whisper APIパターン準拠）"""
    start_time = time.time()
    
    try:
        print(f"\n=== file_pathsベースによる感情特徴量抽出開始 ===")
        print(f"file_pathsパラメータ: {len(request.file_paths)}件のファイルを処理")
        print(f"特徴量セット: {request.feature_set.value}")
        print(f"=" * 50)
        
        if not supabase_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Supabaseサービスが利用できません。環境変数を確認してください。"
            )
        
        features_results = []
        processed_files = []
        processed_time_blocks = []
        error_files = []
        supabase_records = []
        
        # 一時ディレクトリを作成してWAVファイルを処理
        with tempfile.TemporaryDirectory() as temp_dir:
            for file_path in request.file_paths:
                try:
                    print(f"📥 S3からファイル取得開始: {file_path}")
                    
                    # ファイルパスから情報を抽出
                    path_info = extract_info_from_file_path(file_path)
                    device_id = path_info['device_id']
                    date = path_info['date']
                    time_block = path_info['time_block']
                    
                    # S3から一時ファイルにダウンロード
                    temp_file_path = os.path.join(temp_dir, f"{time_block}.wav")
                    
                    try:
                        s3_client.download_file(s3_bucket_name, file_path, temp_file_path)
                        print(f"✅ S3ダウンロード成功: {file_path}")
                    except ClientError as e:
                        error_code = e.response['Error']['Code']
                        if error_code == 'NoSuchKey':
                            print(f"⚠️ ファイルが見つかりません: {file_path}")
                            error_files.append(file_path)
                            continue
                        else:
                            raise e
                    
                    processed_files.append(file_path)
                    
                    print(f"🎵 特徴量タイムライン抽出開始: {file_path}")
                    
                    # 特徴量タイムライン抽出を実行
                    features_result = emotion_service.extract_features_timeline(
                        temp_file_path,
                        request.feature_set
                    )
                    
                    features_results.append(features_result)
                    processed_time_blocks.append(time_block)
                    
                    # Supabase用のレコードを準備
                    supabase_record = {
                        "device_id": device_id,
                        "date": date,
                        "time_block": time_block,
                        "filename": features_result.filename,
                        "duration_seconds": features_result.duration_seconds,
                        "features_timeline": [point.model_dump() for point in features_result.features_timeline],
                        "processing_time": features_result.processing_time,
                        "error": features_result.error
                    }
                    supabase_records.append(supabase_record)
                    
                    # audio_filesテーブルのステータスを更新
                    await update_audio_files_status(file_path)
                    
                    print(f"✅ 完了: {file_path} → 特徴量抽出成功 ({len(features_result.features_timeline)}秒のタイムライン)")
                    
                except Exception as e:
                    error_files.append(file_path)
                    print(f"❌ エラー: {file_path} - {str(e)}")
                    
                    # エラー結果を追加
                    from models import FeaturesTimelineResult
                    path_info = extract_info_from_file_path(file_path)
                    error_result = FeaturesTimelineResult(
                        date=path_info['date'],
                        slot=path_info['time_block'],
                        filename=os.path.basename(file_path),
                        duration_seconds=0,
                        features_timeline=[],
                        error=str(e)
                    )
                    features_results.append(error_result)
                    
                    # エラーレコードもSupabaseに保存
                    supabase_record = {
                        "device_id": path_info['device_id'],
                        "date": path_info['date'],
                        "time_block": path_info['time_block'],
                        "filename": error_result.filename,
                        "duration_seconds": 0,
                        "features_timeline": [],
                        "processing_time": 0,
                        "error": str(e)
                    }
                    supabase_records.append(supabase_record)
        
        # Supabaseにバッチで保存
        print(f"\n=== Supabase保存開始 ===")
        print(f"保存対象: {len(supabase_records)} レコード")
        print(f"=" * 50)
        
        saved_count = 0
        save_errors = []
        
        if supabase_records:
            try:
                # バッチでUPSERT実行
                await supabase_service.batch_upsert_emotion_data(supabase_records)
                saved_count = len(supabase_records)
                print(f"✅ Supabase保存成功: {saved_count} レコード")
            except Exception as e:
                print(f"❌ Supabaseバッチ保存エラー: {str(e)}")
                # 個別に保存を試みる
                for record in supabase_records:
                    try:
                        await supabase_service.upsert_emotion_data(
                            device_id=record["device_id"],
                            date=record["date"],
                            time_block=record["time_block"],
                            filename=record["filename"],
                            duration_seconds=record["duration_seconds"],
                            features_timeline=record["features_timeline"],
                            processing_time=record["processing_time"],
                            error=record.get("error")
                        )
                        saved_count += 1
                    except Exception as individual_error:
                        save_errors.append(f"{record['time_block']}: {str(individual_error)}")
                        print(f"❌ 個別保存エラー: {record['time_block']} - {str(individual_error)}")
        
        # レスポンス作成
        features_response = FeaturesTimelineResponse(
            success=True,
            test_data_directory=f"Supabase: emotion_opensmile table",
            feature_set=request.feature_set.value,
            processed_files=len(features_results),
            saved_files=[f"{record['time_block']}.json" for record in supabase_records[:saved_count]],
            results=features_results,
            total_processing_time=time.time() - start_time,
            message=f"S3から{len(processed_files)}個のWAVファイルを処理し、{saved_count}個のレコードをSupabaseに保存しました"
        )
        
        print(f"\n=== file_pathsベースによる感情特徴量抽出完了 ===")
        print(f"📥 S3取得成功: {len(processed_files)} ファイル")
        print(f"🎵 特徴量抽出完了: {len(features_results)} ファイル")
        print(f"💾 Supabase保存成功: {saved_count} レコード")
        print(f"❌ 処理エラー: {len(error_files)} ファイル")
        print(f"❌ 保存エラー: {len(save_errors)} 件")
        print(f"⏱️ 総処理時間: {time.time() - start_time:.2f}秒")
        print(f"=" * 50)
        
        return features_response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"感情特徴量抽出処理中にエラーが発生しました: {str(e)}"
        )




@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """グローバル例外ハンドラー"""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="Internal server error",
            detail=str(exc)
        ).dict()
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8011,
        reload=True,
        log_level="info"
    )
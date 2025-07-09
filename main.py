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
    VaultFetchRequest
)
from services import EmotionAnalysisService, VaultAPIService
from supabase_service import SupabaseService

# FastAPIアプリケーションの初期化
app = FastAPI(
    title="OpenSMILE Vault API連携サービス",
    description="OpenSMILEを使用したVault API連携による音声特徴量抽出サービス",
    version="3.0.0",
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

# サービスの初期化
emotion_service = EmotionAnalysisService()
vault_service = VaultAPIService()

# Supabaseクライアントの初期化
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
if supabase_url and supabase_key:
    supabase_client: Client = create_client(supabase_url, supabase_key)
    supabase_service = SupabaseService(supabase_client)
else:
    supabase_service = None
    print("⚠️ Supabase環境変数が設定されていません")


@app.get("/", response_model=dict)
async def root():
    """ルートエンドポイント"""
    return {
        "message": "OpenSMILE Vault API連携サービス",
        "version": "3.0.0",
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
            service="OpenSMILE Vault API連携サービス",
            version="3.0.0",
            opensmile_version=opensmile_version
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service unhealthy: {str(e)}"
        )


@app.post("/process/vault-data", response_model=FeaturesTimelineResponse)
async def process_vault_data(request: VaultFetchRequest):
    """Vault APIからWAVファイルを取得して1秒ごとの特徴量タイムラインを生成"""
    start_time = time.time()
    
    try:
        print(f"\n=== Vault API連携による特徴量タイムライン抽出開始 ===")
        print(f"デバイスID: {request.device_id}")
        print(f"対象日付: {request.date}")
        print(f"特徴量セット: {request.feature_set.value}")
        print(f"=" * 50)
        
        # 利用可能なWAVファイルを取得
        available_slots = await vault_service.get_available_wav_files(request.device_id, request.date)
        
        if not available_slots:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"デバイス {request.device_id} の {request.date} にWAVファイルが見つかりません。アクセスしたパス: {vault_service.base_url}/download?device_id={request.device_id}&date={request.date}&slot=XX-XX"
            )
        
        print(f"📄 利用可能なWAVファイル: {len(available_slots)}個")
        print(f"   - スロット: {', '.join(available_slots)}")
        print(f"=" * 50)
        
        features_results = []
        fetched_files = []
        error_files = []
        supabase_records = []  # Supabaseに保存するレコードのリスト
        
        if not supabase_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Supabaseサービスが利用できません。環境変数を確認してください。"
            )
        
        # 一時ディレクトリを作成してWAVファイルを処理
        with tempfile.TemporaryDirectory() as temp_dir:
            for time_slot in available_slots:
                try:
                    print(f"📥 WAVファイル取得開始: {time_slot}.wav")
                    
                    # Vault APIからWAVファイルを取得
                    temp_wav_path = await vault_service.fetch_wav_file(
                        request.device_id, 
                        request.date, 
                        time_slot, 
                        temp_dir
                    )
                    
                    if temp_wav_path:
                        fetched_files.append(f"{time_slot}.wav")
                        
                        print(f"🎵 特徴量タイムライン抽出開始: {time_slot}.wav")
                        
                        # 特徴量タイムライン抽出を実行
                        features_result = emotion_service.extract_features_timeline(
                            temp_wav_path,
                            request.feature_set
                        )
                        
                        # 注意: include_raw_features=falseでもOpenSMILEの場合は
                        # 特徴量タイムラインが主要データなので削除しない
                        # (Whisper APIとは異なる動作)
                        
                        features_results.append(features_result)
                        
                        # Supabase用のレコードを準備
                        supabase_record = {
                            "device_id": request.device_id,
                            "date": request.date,
                            "time_block": time_slot,
                            "filename": features_result.filename,
                            "duration_seconds": features_result.duration_seconds,
                            "features_timeline": [point.model_dump() for point in features_result.features_timeline],
                            "processing_time": features_result.processing_time,
                            "error": features_result.error
                        }
                        supabase_records.append(supabase_record)
                        
                        print(f"✅ 完了: {time_slot}.wav → 特徴量抽出成功 ({len(features_result.features_timeline)}秒のタイムライン)")
                        
                    else:
                        error_files.append(f"{time_slot}.wav")
                        # エラー結果を追加
                        from models import FeaturesTimelineResult
                        error_result = FeaturesTimelineResult(
                            date=request.date,
                            slot=time_slot,
                            filename=f"{time_slot}.wav",
                            duration_seconds=0,
                            features_timeline=[],
                            error=f"Vault APIからのファイル取得に失敗: {time_slot}.wav"
                        )
                        features_results.append(error_result)
                        
                        # エラーレコードもSupabaseに保存
                        supabase_record = {
                            "device_id": request.device_id,
                            "date": request.date,
                            "time_block": time_slot,
                            "filename": error_result.filename,
                            "duration_seconds": 0,
                            "features_timeline": [],
                            "processing_time": 0,
                            "error": error_result.error
                        }
                        supabase_records.append(supabase_record)
                        
                except Exception as e:
                    error_files.append(f"{time_slot}.wav")
                    print(f"❌ エラー: {time_slot}.wav - {str(e)}")
                    
                    # エラー結果を追加
                    from models import FeaturesTimelineResult
                    error_result = FeaturesTimelineResult(
                        date=request.date,
                        slot=time_slot,
                        filename=f"{time_slot}.wav",
                        duration_seconds=0,
                        features_timeline=[],
                        error=str(e)
                    )
                    features_results.append(error_result)
                    
                    # エラーレコードもSupabaseに保存
                    supabase_record = {
                        "device_id": request.device_id,
                        "date": request.date,
                        "time_block": time_slot,
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
            message=f"Vault APIから{len(fetched_files)}個のWAVファイルを取得し、{saved_count}個のレコードをSupabaseに保存しました"
        )
        
        print(f"\n=== Vault API連携による特徴量タイムライン抽出完了 ===")
        print(f"📥 WAV取得成功: {len(fetched_files)} ファイル")
        print(f"🎵 特徴量抽出完了: {len(features_results)} ファイル")
        print(f"💾 Supabase保存成功: {saved_count} レコード")
        print(f"❌ WAV取得エラー: {len(error_files)} ファイル")
        print(f"❌ 保存エラー: {len(save_errors)} 件")
        print(f"⏱️ 総処理時間: {time.time() - start_time:.2f}秒")
        print(f"=" * 50)
        
        return features_response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vault API連携処理中にエラーが発生しました: {str(e)}"
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
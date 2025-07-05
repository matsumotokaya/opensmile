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

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse, FileResponse
import opensmile

from models import (
    HealthResponse,
    ErrorResponse,
    FeaturesTimelineResponse,
    VaultFetchRequest
)
from services import EmotionAnalysisService, VaultAPIService

# FastAPIアプリケーションの初期化
app = FastAPI(
    title="OpenSMILE Vault API連携サービス",
    description="OpenSMILEを使用したVault API連携による音声特徴量抽出サービス",
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# サービスの初期化
emotion_service = EmotionAnalysisService()
vault_service = VaultAPIService()


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
        saved_files = []
        uploaded_files = []
        upload_errors = []
        
        # ローカル出力ディレクトリ作成（Whisper APIと同じ方式）
        local_output_dir = f"/Users/kaya.matsumoto/data/data_accounts/{request.device_id}/{request.date}/opensmile"
        os.makedirs(local_output_dir, exist_ok=True)
        print(f"📁 ローカル出力ディレクトリ: {local_output_dir}")
        
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
                        
                        # ローカルJSONファイルに保存（Whisper APIと同じ方式）
                        local_json_path = os.path.join(local_output_dir, f"{time_slot}.json")
                        with open(local_json_path, 'w', encoding='utf-8') as f:
                            import json
                            json.dump(features_result.model_dump(), f, ensure_ascii=False, indent=2)
                        
                        saved_files.append(f"{time_slot}.json")
                        print(f"💾 ローカルJSON保存: {local_json_path}")
                        print(f"✅ 完了: {time_slot}.wav → ローカル保存成功 ({len(features_result.features_timeline)}秒のタイムライン)")
                        
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
        
        # ローカルに保存された全てのJSONファイルをVault APIにアップロード（Whisper APIと同じ方式）
        local_json_files = [f for f in os.listdir(local_output_dir) if f.endswith('.json')]
        
        print(f"\n=== Vault APIアップロード開始 ===")
        print(f"アップロード対象: {len(local_json_files)} ファイル")
        print(f"=" * 50)
        
        if local_json_files:
            # SSL検証をスキップするコネクターを作成（Whisper APIと同じ）
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                for json_filename in local_json_files:
                    try:
                        json_path = os.path.join(local_output_dir, json_filename)
                        time_slot = json_filename.replace('.json', '')
                        
                        print(f"🚀 アップロード開始: {json_filename}")
                        print(f"📁 ローカルファイルパス: {json_path}")
                        print(f"📏 ファイルサイズ: {os.path.getsize(json_path)} bytes")
                        
                        with open(json_path, 'rb') as f:
                            data = aiohttp.FormData()
                            data.add_field(
                                "file", 
                                f, 
                                filename=json_filename,
                                content_type="application/json"
                            )
                            data.add_field("device_id", request.device_id)
                            data.add_field("date", request.date)
                            data.add_field("time_slot", time_slot)
                            
                            print(f"📤 POST送信先: {vault_service.base_url}/upload/analysis/opensmile-features")
                            
                            async with session.post(f"{vault_service.base_url}/upload/analysis/opensmile-features", data=data) as upload_response:
                                response_text = await upload_response.text()
                                print(f"📡 レスポンスステータス: {upload_response.status}")
                                
                                if upload_response.status == 200:
                                    uploaded_files.append(json_filename)
                                    print(f"✅ アップロード成功: {json_filename}")
                                else:
                                    upload_errors.append(json_filename)
                                    print(f"❌ アップロード失敗: {json_filename}")
                                    print(f"   - ステータスコード: {upload_response.status}")
                                    print(f"   - エラー詳細: {response_text}")
                    
                    except Exception as e:
                        upload_errors.append(json_filename)
                        print(f"❌ アップロード例外エラー: {json_filename}")
                        print(f"   - エラー詳細: {str(e)}")
        
        # レスポンス作成（統合ファイルは出力しない）
        features_response = FeaturesTimelineResponse(
            success=True,
            test_data_directory=f"Vault API: {vault_service.base_url}",
            feature_set=request.feature_set.value,
            processed_files=len(features_results),
            saved_files=uploaded_files,  # アップロード成功したファイルのみ
            results=features_results,
            total_processing_time=time.time() - start_time,
            message=f"Vault APIから{len(fetched_files)}個のWAVファイルを取得し、{len(uploaded_files)}個の個別JSONファイルをVault APIにアップロードしました"
        )
        
        print(f"\n=== Vault API連携による特徴量タイムライン抽出完了 ===")
        print(f"📥 WAV取得成功: {len(fetched_files)} ファイル")
        print(f"🎵 特徴量抽出完了: {len(features_results)} ファイル")
        print(f"💾 ローカル保存: {len(saved_files)} ファイル")
        print(f"🚀 Vault APIアップロード成功: {len(uploaded_files)} ファイル")
        print(f"❌ WAV取得エラー: {len(error_files)} ファイル")
        print(f"❌ アップロードエラー: {len(upload_errors)} ファイル")
        print(f"📁 ローカル出力ディレクトリ: {local_output_dir}")
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
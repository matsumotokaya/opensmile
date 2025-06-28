"""
FastAPI感情分析API
OpenSMILEを使用した音声特徴量抽出と感情分析
"""

import time
import os
import tempfile
from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse, FileResponse
import opensmile

from models import (
    FeatureSetEnum,
    FeatureExtractionRequest,
    FeatureExtractionResponse,
    EmotionAnalysisResponse,
    EmotionAnalysisResult,
    HealthResponse,
    AvailableFeaturesResponse,
    FileListResponse,
    ExportRequest,
    ExportResponse,
    ErrorResponse,
    VaultAnalysisRequest,
    VaultAnalysisResponse,
    VaultFileInfo,
    TestDataRequest,
    TestDataResponse
)
from services import OpenSMILEService, EmotionAnalysisService, VaultService

# FastAPIアプリケーションの初期化
app = FastAPI(
    title="OpenSMILE感情分析API",
    description="OpenSMILEを使用した音声特徴量抽出と感情分析のためのAPI",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# サービスの初期化
opensmile_service = OpenSMILEService()
emotion_service = EmotionAnalysisService()


@app.get("/", response_model=dict)
async def root():
    """ルートエンドポイント"""
    return {
        "message": "OpenSMILE感情分析API",
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
            service="OpenSMILE感情分析API",
            version="2.0.0",
            opensmile_version=opensmile_version
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service unhealthy: {str(e)}"
        )


@app.get("/features", response_model=AvailableFeaturesResponse)
async def get_available_features():
    """利用可能な特徴量セットを取得"""
    try:
        feature_sets = opensmile_service.get_available_feature_sets()
        descriptions = opensmile_service.get_feature_set_descriptions()
        
        return AvailableFeaturesResponse(
            available_feature_sets=feature_sets,
            default=FeatureSetEnum.EGEMAPS_V02.value,
            descriptions=descriptions
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/files", response_model=FileListResponse)
async def list_wav_files():
    """現在のディレクトリの.wavファイル一覧を取得"""
    try:
        current_dir = Path(".")
        wav_files = [f.name for f in current_dir.glob("*.wav")]
        
        return FileListResponse(
            directory=str(current_dir.absolute()),
            wav_files=wav_files,
            count=len(wav_files)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post("/extract", response_model=FeatureExtractionResponse)
async def extract_features(request: FeatureExtractionRequest = None):
    """音声ファイルから特徴量を抽出"""
    start_time = time.time()
    
    # リクエストがない場合はデフォルト値を使用
    if request is None:
        request = FeatureExtractionRequest()
    
    try:
        # 現在のディレクトリの.wavファイルを検索
        wav_files = list(Path(".").glob("*.wav"))
        
        if not wav_files:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="現在のディレクトリに.wavファイルが見つかりません"
            )
        
        # 各ファイルを処理
        results = []
        for wav_file in wav_files:
            result = opensmile_service.extract_features(
                str(wav_file), 
                request.feature_set
            )
            
            # 生の特徴量データを除外する場合
            if not request.include_raw_features:
                result.features = {}
            
            results.append(result)
        
        total_processing_time = time.time() - start_time
        
        return FeatureExtractionResponse(
            feature_set=request.feature_set.value,
            processed_files=len(results),
            results=results,
            total_processing_time=total_processing_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post("/analyze", response_model=EmotionAnalysisResponse)
async def analyze_emotions(request: FeatureExtractionRequest = None):
    """音声ファイルから感情を分析"""
    start_time = time.time()
    
    # リクエストがない場合はデフォルト値を使用
    if request is None:
        request = FeatureExtractionRequest()
    
    try:
        # 現在のディレクトリの.wavファイルを検索
        wav_files = list(Path(".").glob("*.wav"))
        
        if not wav_files:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="現在のディレクトリに.wavファイルが見つかりません"
            )
        
        # 各ファイルを処理
        results = []
        for wav_file in wav_files:
            try:
                emotion_prediction, feature_result = emotion_service.analyze_emotion(
                    str(wav_file),
                    request.feature_set
                )
                
                # 生の特徴量データを除外する場合
                if not request.include_raw_features:
                    feature_result.features = {}
                
                analysis_result = EmotionAnalysisResult(
                    filename=wav_file.name,
                    primary_emotion=emotion_prediction,
                    feature_extraction=feature_result
                )
                
                results.append(analysis_result)
                
            except Exception as e:
                # 個別ファイルでエラーが発生した場合
                error_result = EmotionAnalysisResult(
                    filename=wav_file.name,
                    primary_emotion=None,
                    error=str(e)
                )
                results.append(error_result)
        
        total_processing_time = time.time() - start_time
        
        return EmotionAnalysisResponse(
            feature_set=request.feature_set.value,
            processed_files=len(results),
            results=results,
            total_processing_time=total_processing_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post("/export", response_model=ExportResponse)
async def export_analysis_results(request: ExportRequest = None):
    """分析結果をJSONファイルにエクスポート"""
    start_time = time.time()
    
    # リクエストがない場合はデフォルト値を使用
    if request is None:
        request = ExportRequest()
    
    try:
        # 現在のディレクトリの.wavファイルを検索
        wav_files = list(Path(".").glob("*.wav"))
        
        if not wav_files:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="現在のディレクトリに.wavファイルが見つかりません"
            )
        
        output_files = []
        
        # 分析タイプに応じて処理
        if request.analysis_type in ["features", "both"]:
            # 特徴量抽出
            feature_results = []
            for wav_file in wav_files:
                result = opensmile_service.extract_features(
                    str(wav_file), 
                    request.feature_set
                )
                
                if not request.include_raw_features:
                    result.features = {}
                
                feature_results.append(result)
            
            # 特徴量抽出結果をファイルに保存
            features_filename = request.output_filename or f"features_analysis_{int(time.time())}.json"
            if not features_filename.endswith('.json'):
                features_filename += '.json'
            
            features_response = FeatureExtractionResponse(
                feature_set=request.feature_set.value,
                processed_files=len(feature_results),
                results=feature_results,
                total_processing_time=time.time() - start_time
            )
            
            with open(features_filename, 'w', encoding='utf-8') as f:
                import json
                json.dump(features_response.model_dump(), f, ensure_ascii=False, indent=2)
            
            output_files.append(features_filename)
        
        if request.analysis_type in ["emotions", "both"]:
            # 感情分析
            emotion_results = []
            for wav_file in wav_files:
                try:
                    emotion_prediction, feature_result = emotion_service.analyze_emotion(
                        str(wav_file),
                        request.feature_set
                    )
                    
                    if not request.include_raw_features:
                        feature_result.features = {}
                    
                    analysis_result = EmotionAnalysisResult(
                        filename=wav_file.name,
                        primary_emotion=emotion_prediction,
                        feature_extraction=feature_result
                    )
                    
                    emotion_results.append(analysis_result)
                    
                except Exception as e:
                    error_result = EmotionAnalysisResult(
                        filename=wav_file.name,
                        primary_emotion=None,
                        error=str(e)
                    )
                    emotion_results.append(error_result)
            
            # 感情分析結果をファイルに保存
            emotions_filename = request.output_filename or f"emotion_analysis_{int(time.time())}.json"
            if request.analysis_type == "both":
                emotions_filename = emotions_filename.replace(".json", "_emotions.json")
            elif not emotions_filename.endswith('.json'):
                emotions_filename += '.json'
            
            emotions_response = EmotionAnalysisResponse(
                feature_set=request.feature_set.value,
                processed_files=len(emotion_results),
                results=emotion_results,
                total_processing_time=time.time() - start_time
            )
            
            with open(emotions_filename, 'w', encoding='utf-8') as f:
                import json
                json.dump(emotions_response.model_dump(), f, ensure_ascii=False, indent=2)
            
            output_files.append(emotions_filename)
        
        return ExportResponse(
            success=True,
            output_files=output_files,
            message=f"分析結果を {len(output_files)} 個のファイルにエクスポートしました",
            total_files_processed=len(wav_files)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/download/{filename}")
async def download_file(filename: str):
    """分析結果ファイルをダウンロード"""
    try:
        file_path = Path(".") / filename
        
        # ファイルの存在確認
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"ファイル '{filename}' が見つかりません"
            )
        
        # セキュリティチェック（JSONファイルのみ許可）
        if not filename.endswith('.json'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="JSONファイルのみダウンロード可能です"
            )
        
        return FileResponse(
            path=str(file_path),
            filename=filename,
            media_type="application/json"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/results", response_model=FileListResponse)
async def list_result_files():
    """分析結果ファイル一覧を取得"""
    try:
        current_dir = Path(".")
        json_files = [f.name for f in current_dir.glob("*.json")]
        
        # 分析結果ファイルのみをフィルタリング
        analysis_files = [
            f for f in json_files 
            if any(keyword in f for keyword in ["analysis", "features", "emotions"])
        ]
        
        return FileListResponse(
            directory=str(current_dir.absolute()),
            wav_files=analysis_files,  # 実際はJSONファイルだが、既存のモデルを再利用
            count=len(analysis_files)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post("/analyze/vault", response_model=VaultAnalysisResponse)
async def analyze_vault_files(request: VaultAnalysisRequest):
    """
    Vaultから音声ファイルをダウンロードして感情分析を実行
    Streamlit連携用エンドポイント
    """
    start_time = time.time()
    
    try:
        # 一時ディレクトリを作成
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # VaultServiceを使用してファイルをダウンロード（正しいVault APIベースURLを使用）
            async with VaultService() as vault_service:
                # Vault APIからファイルリストを取得
                vault_files = await vault_service.get_wav_files_list(request.user_id, request.date)
                
                if not vault_files:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"指定された日付（{request.date}）とユーザーID（{request.user_id}）のWAVファイルが見つかりません"
                    )
                
                # すべてのWAVファイルをダウンロード
                downloaded_files = await vault_service.download_all_wav_files(
                    request.user_id, 
                    request.date, 
                    temp_path
                )
                
                if not downloaded_files:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="WAVファイルのダウンロードに失敗しました"
                    )
                
                # 各ファイルの感情分析を実行
                results = []
                processed_files = 0
                failed_files = 0
                
                for file_path in downloaded_files:
                    try:
                        emotion_prediction, feature_result = emotion_service.analyze_emotion(
                            str(file_path),
                            request.feature_set
                        )
                        
                        # 生の特徴量データを除外する場合
                        if not request.include_raw_features:
                            feature_result.features = {}
                        
                        analysis_result = EmotionAnalysisResult(
                            filename=file_path.name,
                            primary_emotion=emotion_prediction,
                            feature_extraction=feature_result
                        )
                        
                        results.append(analysis_result)
                        processed_files += 1
                        
                    except Exception as e:
                        # 個別ファイルでエラーが発生した場合
                        error_result = EmotionAnalysisResult(
                            filename=file_path.name,
                            primary_emotion=None,
                            error=str(e)
                        )
                        results.append(error_result)
                        failed_files += 1
                
                total_processing_time = time.time() - start_time
                
                return VaultAnalysisResponse(
                    user_id=request.user_id,
                    date=request.date,
                    feature_set=request.feature_set.value,
                    downloaded_files=len(downloaded_files),
                    processed_files=processed_files,
                    failed_files=failed_files,
                    results=results,
                    total_processing_time=total_processing_time,
                    vault_files=vault_files
                )
                
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vault分析処理中にエラーが発生しました: {str(e)}"
        )


@app.post("/process/test-data", response_model=TestDataResponse)
async def process_test_data(request: TestDataRequest = None):
    """test-dataフォルダ内のWAVファイルを処理してJSONで保存"""
    start_time = time.time()
    
    # リクエストがない場合はデフォルト値を使用
    if request is None:
        request = TestDataRequest()
    
    try:
        # test-dataディレクトリを指定
        test_data_dir = Path("test-data")
        
        if not test_data_dir.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="test-dataディレクトリが見つかりません"
            )
        
        # test-dataディレクトリの.wavファイルを検索
        wav_files = list(test_data_dir.glob("*.wav"))
        
        if not wav_files:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="test-dataディレクトリに.wavファイルが見つかりません"
            )
        
        saved_files = []
        results = []
        processed_files = 0
        
        # 分析タイプに応じて処理
        if request.analysis_type in ["features", "both"]:
            # 特徴量抽出
            feature_results = []
            for wav_file in wav_files:
                result = opensmile_service.extract_features(
                    str(wav_file), 
                    request.feature_set
                )
                
                if not request.include_raw_features:
                    result.features = {}
                
                feature_results.append(result)
                processed_files += 1
            
            # 特徴量抽出結果をJSONファイルに保存
            features_filename = f"features_analysis_{int(time.time())}.json"
            features_output_path = test_data_dir / features_filename
            
            features_response = FeatureExtractionResponse(
                feature_set=request.feature_set.value,
                processed_files=len(feature_results),
                results=feature_results,
                total_processing_time=time.time() - start_time
            )
            
            with open(features_output_path, 'w', encoding='utf-8') as f:
                import json
                json.dump(features_response.model_dump(), f, ensure_ascii=False, indent=2)
            
            saved_files.append(features_filename)
        
        if request.analysis_type in ["emotions", "both"]:
            # 感情分析
            emotion_results = []
            for wav_file in wav_files:
                try:
                    emotion_prediction, feature_result = emotion_service.analyze_emotion(
                        str(wav_file),
                        request.feature_set
                    )
                    
                    if not request.include_raw_features:
                        feature_result.features = {}
                    
                    analysis_result = EmotionAnalysisResult(
                        filename=wav_file.name,
                        primary_emotion=emotion_prediction,
                        feature_extraction=feature_result
                    )
                    
                    emotion_results.append(analysis_result)
                    
                except Exception as e:
                    error_result = EmotionAnalysisResult(
                        filename=wav_file.name,
                        primary_emotion=None,
                        error=str(e)
                    )
                    emotion_results.append(error_result)
            
            # 感情分析結果をJSONファイルに保存
            emotions_filename = f"emotion_analysis_{int(time.time())}.json"
            if request.analysis_type == "both":
                emotions_filename = emotions_filename.replace(".json", "_emotions.json")
            
            emotions_output_path = test_data_dir / emotions_filename
            
            emotions_response = EmotionAnalysisResponse(
                feature_set=request.feature_set.value,
                processed_files=len(emotion_results),
                results=emotion_results,
                total_processing_time=time.time() - start_time
            )
            
            with open(emotions_output_path, 'w', encoding='utf-8') as f:
                import json
                json.dump(emotions_response.model_dump(), f, ensure_ascii=False, indent=2)
            
            saved_files.append(emotions_filename)
            results = emotion_results
        
        total_processing_time = time.time() - start_time
        
        return TestDataResponse(
            success=True,
            test_data_directory=str(test_data_dir.absolute()),
            feature_set=request.feature_set.value,
            processed_files=processed_files if request.analysis_type == "features" else len(wav_files),
            saved_files=saved_files,
            results=results,
            total_processing_time=total_processing_time,
            message=f"test-dataフォルダの{len(wav_files)}個のWAVファイルを処理し、{len(saved_files)}個のJSONファイルを保存しました"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"test-data処理中にエラーが発生しました: {str(e)}"
        )


@app.get("/test-data/files", response_model=FileListResponse)
async def list_test_data_files():
    """test-dataフォルダ内のファイル一覧を取得"""
    try:
        test_data_dir = Path("test-data")
        
        if not test_data_dir.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="test-dataディレクトリが見つかりません"
            )
        
        wav_files = [f.name for f in test_data_dir.glob("*.wav")]
        json_files = [f.name for f in test_data_dir.glob("*.json")]
        all_files = wav_files + json_files
        
        return FileListResponse(
            directory=str(test_data_dir.absolute()),
            wav_files=all_files,  # 既存のモデルを再利用（WAV + JSONファイル）
            count=len(all_files)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
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
        port=8000,
        reload=True,
        log_level="info"
    )
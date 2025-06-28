"""
Pydanticモデル定義
感情分析API用のリクエスト・レスポンススキーマ
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime


class FeatureSetEnum(str, Enum):
    """利用可能な特徴量セット"""
    COMPARE_2016 = "ComParE_2016"
    GEMAPS = "GeMAPS"
    GEMAPS_V01B = "GeMAPSv01b"
    EGEMAPS = "eGeMAPS"
    EGEMAPS_V01B = "eGeMAPSv01b"
    EGEMAPS_V02 = "eGeMAPSv02"
    EMOBASE = "emobase"


class PlutchikEmotionEnum(str, Enum):
    """Plutchikの8基本感情"""
    ANGER = "anger"
    JOY = "joy" 
    SADNESS = "sadness"
    FEAR = "fear"
    DISGUST = "disgust"
    TRUST = "trust"
    SURPRISE = "surprise"
    ANTICIPATION = "anticipation"


class FeatureExtractionRequest(BaseModel):
    """特徴量抽出リクエスト"""
    feature_set: Optional[FeatureSetEnum] = Field(
        default=FeatureSetEnum.EGEMAPS_V02,
        description="使用する特徴量セット"
    )
    include_raw_features: Optional[bool] = Field(
        default=False,
        description="生の特徴量データを含めるかどうか"
    )


class AudioFileInfo(BaseModel):
    """音声ファイル情報"""
    filename: str = Field(description="ファイル名")
    duration: Optional[float] = Field(None, description="音声の長さ（秒）")
    sample_rate: Optional[int] = Field(None, description="サンプリングレート")


class FeatureExtractionResult(BaseModel):
    """特徴量抽出結果"""
    filename: str = Field(description="処理されたファイル名")
    feature_count: int = Field(description="抽出された特徴量の数")
    features: Dict[str, float] = Field(description="抽出された特徴量")
    error: Optional[str] = Field(None, description="エラーメッセージ（エラー時）")
    processing_time: Optional[float] = Field(None, description="処理時間（秒）")


class FeatureExtractionResponse(BaseModel):
    """特徴量抽出レスポンス"""
    feature_set: str = Field(description="使用された特徴量セット")
    processed_files: int = Field(description="処理されたファイル数")
    results: List[FeatureExtractionResult] = Field(description="抽出結果のリスト")
    total_processing_time: Optional[float] = Field(None, description="総処理時間（秒）")


class EmotionPrediction(BaseModel):
    """感情予測結果"""
    emotion: str = Field(description="予測された感情")
    confidence: float = Field(description="信頼度（0-1）", ge=0.0, le=1.0)
    raw_scores: Optional[Dict[str, float]] = Field(None, description="各感情の生スコア")


class EmotionAnalysisResult(BaseModel):
    """感情分析結果"""
    filename: str = Field(description="分析されたファイル名")
    primary_emotion: EmotionPrediction = Field(description="主要な感情")
    all_emotions: Optional[List[EmotionPrediction]] = Field(None, description="全感情の予測結果")
    feature_extraction: Optional[FeatureExtractionResult] = Field(None, description="特徴量抽出結果")
    error: Optional[str] = Field(None, description="エラーメッセージ（エラー時）")


class EmotionAnalysisResponse(BaseModel):
    """感情分析レスポンス"""
    feature_set: str = Field(description="使用された特徴量セット")
    processed_files: int = Field(description="処理されたファイル数")
    results: List[EmotionAnalysisResult] = Field(description="分析結果のリスト")
    total_processing_time: Optional[float] = Field(None, description="総処理時間（秒）")


class HealthResponse(BaseModel):
    """ヘルスチェックレスポンス"""
    status: str = Field(description="サービスステータス")
    service: str = Field(description="サービス名")
    version: str = Field(description="バージョン")
    opensmile_version: Optional[str] = Field(None, description="OpenSMILEバージョン")


class AvailableFeaturesResponse(BaseModel):
    """利用可能特徴量セットレスポンス"""
    available_feature_sets: List[str] = Field(description="利用可能な特徴量セット")
    default: str = Field(description="デフォルトの特徴量セット")
    descriptions: Optional[Dict[str, str]] = Field(None, description="各特徴量セットの説明")


class FileListResponse(BaseModel):
    """ファイル一覧レスポンス"""
    directory: str = Field(description="対象ディレクトリ")
    wav_files: List[str] = Field(description="見つかった.wavファイルのリスト")
    count: int = Field(description="ファイル数")


class ExportRequest(BaseModel):
    """エクスポートリクエスト"""
    feature_set: Optional[FeatureSetEnum] = Field(
        default=FeatureSetEnum.EGEMAPS_V02,
        description="使用する特徴量セット"
    )
    include_raw_features: Optional[bool] = Field(
        default=True,
        description="生の特徴量データを含めるかどうか"
    )
    output_filename: Optional[str] = Field(
        None,
        description="出力ファイル名（指定しない場合は自動生成）"
    )
    analysis_type: str = Field(
        default="both",
        description="分析タイプ: 'features', 'emotions', 'both'"
    )


class ExportResponse(BaseModel):
    """エクスポートレスポンス"""
    success: bool = Field(description="エクスポート成功フラグ")
    output_files: List[str] = Field(description="作成された出力ファイルのリスト")
    message: str = Field(description="処理結果メッセージ")
    total_files_processed: int = Field(description="処理されたファイル数")


class ErrorResponse(BaseModel):
    """エラーレスポンス"""
    error: str = Field(description="エラーメッセージ")
    detail: Optional[str] = Field(None, description="詳細なエラー情報")
    error_code: Optional[str] = Field(None, description="エラーコード")



class TestDataRequest(BaseModel):
    """テストデータ処理リクエスト"""
    feature_set: Optional[FeatureSetEnum] = Field(
        default=FeatureSetEnum.EGEMAPS_V02,
        description="使用する特徴量セット"
    )
    include_raw_features: Optional[bool] = Field(
        default=True,
        description="生の特徴量データを含めるかどうか"
    )
    analysis_type: str = Field(
        default="both",
        description="分析タイプ: 'features', 'emotions', 'both'"
    )


class FeatureTimelinePoint(BaseModel):
    """1秒ごとの特徴量抽出ポイント"""
    timestamp: str = Field(description="時刻 (HH:MM:SS形式)")
    features: Dict[str, float] = Field(description="eGeMAPS特徴量（88個）")


class FeaturesTimelineResult(BaseModel):
    """特徴量タイムライン抽出結果"""
    date: str = Field(description="分析対象日 (YYYY-MM-DD形式)")
    slot: str = Field(description="30分スロット (HH:MM-HH:MM形式)")
    filename: str = Field(description="分析されたファイル名")
    duration_seconds: int = Field(description="音声の長さ（秒）")
    features_timeline: List[FeatureTimelinePoint] = Field(description="1秒ごとの特徴量タイムライン")
    processing_time: Optional[float] = Field(None, description="処理時間（秒）")
    error: Optional[str] = Field(None, description="エラーメッセージ（エラー時）")


class EmotionTimelinePoint(BaseModel):
    """1秒ごとの感情分析ポイント"""
    timestamp: str = Field(description="時刻 (HH:MM:SS形式)")
    emotion: PlutchikEmotionEnum = Field(description="予測された感情")
    scores: Dict[str, float] = Field(description="Plutchikの8感情に対するスコア")


class EmotionTimelineResult(BaseModel):
    """感情タイムライン分析結果"""
    date: str = Field(description="分析対象日 (YYYY-MM-DD形式)")
    slot: str = Field(description="30分スロット (HH:MM-HH:MM形式)")
    filename: str = Field(description="分析されたファイル名")
    duration_seconds: int = Field(description="音声の長さ（秒）")
    emotion_timeline: List[EmotionTimelinePoint] = Field(description="1秒ごとの感情タイムライン")
    processing_time: Optional[float] = Field(None, description="処理時間（秒）")
    error: Optional[str] = Field(None, description="エラーメッセージ（エラー時）")


class TimelineAnalysisRequest(BaseModel):
    """タイムライン分析リクエスト"""
    feature_set: Optional[FeatureSetEnum] = Field(
        default=FeatureSetEnum.EGEMAPS_V02,
        description="使用する特徴量セット"
    )
    include_raw_features: Optional[bool] = Field(
        default=False,
        description="生の特徴量データを含めるかどうか"
    )
    analysis_type: str = Field(
        default="timeline",
        description="分析タイプ: 'features', 'emotions', 'both', 'timeline'"
    )


class VaultFetchRequest(BaseModel):
    """Vault APIからのWAVファイル取得リクエスト"""
    user_id: str = Field(description="ユーザーID (例: user123)")
    date: str = Field(description="日付 (YYYY-MM-DD形式, 例: 2025-06-25)")
    feature_set: Optional[FeatureSetEnum] = Field(
        default=FeatureSetEnum.EGEMAPS_V02,
        description="使用する特徴量セット"
    )
    include_raw_features: Optional[bool] = Field(
        default=False,
        description="生の特徴量データを含めるかどうか"
    )


class FeaturesTimelineResponse(BaseModel):
    """特徴量タイムライン抽出レスポンス"""
    success: bool = Field(description="処理成功フラグ")
    test_data_directory: str = Field(description="処理対象ディレクトリ")
    feature_set: str = Field(description="使用された特徴量セット")
    processed_files: int = Field(description="処理されたファイル数")
    saved_files: List[str] = Field(description="保存されたJSONファイルのリスト")
    results: List[FeaturesTimelineResult] = Field(description="特徴量タイムライン結果のリスト")
    total_processing_time: Optional[float] = Field(None, description="総処理時間（秒）")
    message: str = Field(description="処理結果メッセージ")


class TimelineAnalysisResponse(BaseModel):
    """タイムライン分析レスポンス"""
    success: bool = Field(description="処理成功フラグ")
    test_data_directory: str = Field(description="処理対象ディレクトリ")
    feature_set: str = Field(description="使用された特徴量セット")
    processed_files: int = Field(description="処理されたファイル数")
    saved_files: List[str] = Field(description="保存されたJSONファイルのリスト")
    results: List[EmotionTimelineResult] = Field(description="タイムライン分析結果のリスト")
    total_processing_time: Optional[float] = Field(None, description="総処理時間（秒）")
    message: str = Field(description="処理結果メッセージ")


class TestDataResponse(BaseModel):
    """テストデータ処理レスポンス"""
    success: bool = Field(description="処理成功フラグ")
    test_data_directory: str = Field(description="処理対象ディレクトリ")
    feature_set: str = Field(description="使用された特徴量セット")
    processed_files: int = Field(description="処理されたファイル数")
    saved_files: List[str] = Field(description="保存されたJSONファイルのリスト")
    results: List[EmotionAnalysisResult] = Field(description="分析結果のリスト")
    total_processing_time: Optional[float] = Field(None, description="総処理時間（秒）")
    message: str = Field(description="処理結果メッセージ")
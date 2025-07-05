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
    EGEMAPS_V02 = "eGeMAPSv02"


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




class HealthResponse(BaseModel):
    """ヘルスチェックレスポンス"""
    status: str = Field(description="サービスステータス")
    service: str = Field(description="サービス名")
    version: str = Field(description="バージョン")
    opensmile_version: Optional[str] = Field(None, description="OpenSMILEバージョン")




class ErrorResponse(BaseModel):
    """エラーレスポンス"""
    error: str = Field(description="エラーメッセージ")
    detail: Optional[str] = Field(None, description="詳細なエラー情報")
    error_code: Optional[str] = Field(None, description="エラーコード")





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




class VaultFetchRequest(BaseModel):
    """Vault APIからのWAVファイル取得リクエスト"""
    device_id: str = Field(description="デバイスID (例: device123)")
    date: str = Field(description="日付 (YYYY-MM-DD形式, 例: 2025-06-25)")
    feature_set: FeatureSetEnum = Field(
        default=FeatureSetEnum.EGEMAPS_V02,
        description="使用する特徴量セット（eGeMAPSv02固定）"
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



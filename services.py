"""
サービスレイヤー
OpenSMILEとの統合および特徴量処理
"""

import time
import subprocess
import tempfile
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pandas as pd
import opensmile
import numpy as np
from datetime import datetime, timedelta
from models import (
    FeatureSetEnum, 
    FeatureExtractionResult, 
    EmotionPrediction, 
    PlutchikEmotionEnum,
    EmotionTimelinePoint,
    EmotionTimelineResult,
    FeatureTimelinePoint,
    FeaturesTimelineResult
)


class OpenSMILEService:
    """OpenSMILE特徴量抽出サービス"""
    
    def __init__(self):
        self.feature_set_mapping = {
            FeatureSetEnum.COMPARE_2016: opensmile.FeatureSet.ComParE_2016,
            FeatureSetEnum.GEMAPS: opensmile.FeatureSet.GeMAPS,
            FeatureSetEnum.GEMAPS_V01B: opensmile.FeatureSet.GeMAPSv01b,
            FeatureSetEnum.EGEMAPS: opensmile.FeatureSet.eGeMAPS,
            FeatureSetEnum.EGEMAPS_V01B: opensmile.FeatureSet.eGeMAPSv01b,
            FeatureSetEnum.EGEMAPS_V02: opensmile.FeatureSet.eGeMAPSv02,
            FeatureSetEnum.EMOBASE: opensmile.FeatureSet.emobase,
        }
    
    def extract_features(
        self, 
        wav_file_path: str, 
        feature_set: FeatureSetEnum = FeatureSetEnum.EGEMAPS_V02
    ) -> FeatureExtractionResult:
        """
        音声ファイルから特徴量を抽出
        
        Args:
            wav_file_path: 音声ファイルのパス
            feature_set: 使用する特徴量セット
            
        Returns:
            FeatureExtractionResult: 抽出結果
        """
        start_time = time.time()
        
        try:
            # OpenSMILEインスタンスを作成
            smile = opensmile.Smile(
                feature_set=self.feature_set_mapping[feature_set],
                feature_level=opensmile.FeatureLevel.Functionals,
            )
            
            # 特徴量を抽出
            features_df = smile.process_file(wav_file_path)
            
            # DataFrameを辞書に変換
            features_dict = features_df.iloc[0].to_dict()
            
            processing_time = time.time() - start_time
            
            return FeatureExtractionResult(
                filename=Path(wav_file_path).name,
                feature_count=len(features_dict),
                features=features_dict,
                processing_time=processing_time
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            return FeatureExtractionResult(
                filename=Path(wav_file_path).name,
                feature_count=0,
                features={},
                error=str(e),
                processing_time=processing_time
            )
    
    def extract_features_cli(
        self, 
        wav_file_path: str, 
        feature_set: FeatureSetEnum = FeatureSetEnum.EGEMAPS_V02
    ) -> FeatureExtractionResult:
        """
        OpenSMILE CLIを使用して特徴量を抽出（代替実装）
        
        Args:
            wav_file_path: 音声ファイルのパス
            feature_set: 使用する特徴量セット
            
        Returns:
            FeatureExtractionResult: 抽出結果
        """
        start_time = time.time()
        
        try:
            # 一時的な出力ファイルを作成
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as temp_file:
                temp_output_path = temp_file.name
            
            # OpenSMILE CLIコマンドを構築
            # 注: 実際のOpenSMILE CLI使用時は適切な設定ファイルパスを指定
            cmd = [
                'python', 'extract_features.py',
                '--directory', str(Path(wav_file_path).parent),
                '--format', 'json',
                '--feature-set', feature_set.value
            ]
            
            # コマンド実行
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent
            )
            
            if result.returncode != 0:
                raise Exception(f"OpenSMILE CLI execution failed: {result.stderr}")
            
            # 結果ファイルを読み込み
            output_file = Path(wav_file_path).parent / f"{Path(wav_file_path).stem}_features.json"
            
            if output_file.exists():
                with open(output_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                features_dict = data.get('features', {})
                
                # 一時ファイルを削除
                output_file.unlink()
                
                processing_time = time.time() - start_time
                
                return FeatureExtractionResult(
                    filename=Path(wav_file_path).name,
                    feature_count=len(features_dict),
                    features=features_dict,
                    processing_time=processing_time
                )
            else:
                raise Exception("Output file not found")
                
        except Exception as e:
            processing_time = time.time() - start_time
            return FeatureExtractionResult(
                filename=Path(wav_file_path).name,
                feature_count=0,
                features={},
                error=str(e),
                processing_time=processing_time
            )
        finally:
            # 一時ファイルのクリーンアップ
            if 'temp_output_path' in locals() and os.path.exists(temp_output_path):
                os.unlink(temp_output_path)
    
    def get_available_feature_sets(self) -> List[str]:
        """利用可能な特徴量セットを取得"""
        return [fs.value for fs in FeatureSetEnum]
    
    def get_feature_set_descriptions(self) -> Dict[str, str]:
        """特徴量セットの説明を取得"""
        return {
            FeatureSetEnum.COMPARE_2016.value: "ComParE 2016 特徴量セット（6373特徴量）",
            FeatureSetEnum.GEMAPS.value: "GeMAPS 特徴量セット（62特徴量）",
            FeatureSetEnum.GEMAPS_V01B.value: "GeMAPS v01b 特徴量セット",
            FeatureSetEnum.EGEMAPS.value: "eGeMAPS 特徴量セット（88特徴量）",
            FeatureSetEnum.EGEMAPS_V01B.value: "eGeMAPS v01b 特徴量セット",
            FeatureSetEnum.EGEMAPS_V02.value: "eGeMAPS v02 特徴量セット（88特徴量）- 推奨",
            FeatureSetEnum.EMOBASE.value: "emobase 特徴量セット",
        }


class EmotionAnalysisService:
    """感情分析サービス"""
    
    def __init__(self):
        self.opensmile_service = OpenSMILEService()
        # 感情分析モデルの初期化（将来的に実装）
        self.emotion_model = None
        # OpenSMILE特徴量セットマッピングを追加
        self.feature_set_mapping = self.opensmile_service.feature_set_mapping
    
    def analyze_emotion(
        self, 
        wav_file_path: str, 
        feature_set: FeatureSetEnum = FeatureSetEnum.EGEMAPS_V02
    ) -> Tuple[EmotionPrediction, FeatureExtractionResult]:
        """
        音声ファイルから感情を分析
        
        Args:
            wav_file_path: 音声ファイルのパス
            feature_set: 使用する特徴量セット
            
        Returns:
            Tuple[EmotionPrediction, FeatureExtractionResult]: 感情予測と特徴量抽出結果
        """
        # 特徴量を抽出
        feature_result = self.opensmile_service.extract_features(wav_file_path, feature_set)
        
        if feature_result.error:
            # 特徴量抽出でエラーが発生した場合
            emotion_prediction = EmotionPrediction(
                emotion="unknown",
                confidence=0.0,
                raw_scores={}
            )
            return emotion_prediction, feature_result
        
        # 簡単な感情分析の実装（デモ用）
        # 実際のプロダクションでは機械学習モデルを使用
        emotion_prediction = self._simple_emotion_analysis(feature_result.features)
        
        return emotion_prediction, feature_result
    
    def _simple_emotion_analysis(self, features: Dict[str, float]) -> EmotionPrediction:
        """
        簡単な感情分析（デモ用）
        実際の実装では機械学習モデルを使用
        
        Args:
            features: 抽出された特徴量
            
        Returns:
            EmotionPrediction: 感情予測結果
        """
        # デモ用の簡単なルールベース分析
        # 実際の実装では訓練済みモデルを使用
        
        # F0（基本周波数）関連の特徴量を取得
        f0_mean = features.get('F0final_sma_amean', 0.0)
        f0_std = features.get('F0final_sma_stddev', 0.0)
        
        # エネルギー関連の特徴量を取得
        energy_mean = features.get('audSpec_Rfilt_sma[0]_amean', 0.0)
        
        # 簡単なルールベース分類
        emotions = {
            "happy": 0.0,
            "sad": 0.0,
            "angry": 0.0,
            "neutral": 0.0,
            "excited": 0.0
        }
        
        # F0が高く、変動が大きい場合は興奮状態
        if f0_mean > 200 and f0_std > 50:
            emotions["excited"] = 0.7
            emotions["happy"] = 0.6
        # F0が低く、エネルギーも低い場合は悲しい
        elif f0_mean < 150 and energy_mean < 0.1:
            emotions["sad"] = 0.6
            emotions["neutral"] = 0.4
        # F0の変動が大きくエネルギーが高い場合は怒り
        elif f0_std > 80 and energy_mean > 0.2:
            emotions["angry"] = 0.65
        # その他はニュートラル
        else:
            emotions["neutral"] = 0.8
        
        # 最も高いスコアの感情を選択
        primary_emotion = max(emotions.keys(), key=lambda k: emotions[k])
        confidence = emotions[primary_emotion]
        
        return EmotionPrediction(
            emotion=primary_emotion,
            confidence=confidence,
            raw_scores=emotions
        )
    
    def analyze_emotion_timeline(
        self, 
        wav_file_path: str, 
        feature_set: FeatureSetEnum = FeatureSetEnum.EGEMAPS_V02
    ) -> EmotionTimelineResult:
        """
        音声ファイルから1秒ごとの感情タイムラインを分析
        
        Args:
            wav_file_path: 音声ファイルのパス
            feature_set: 使用する特徴量セット
            
        Returns:
            EmotionTimelineResult: タイムライン分析結果
        """
        start_time = time.time()
        
        try:
            # OpenSMILEインスタンスを作成（LLD - Low Level Descriptorsを使用）
            smile = opensmile.Smile(
                feature_set=self.feature_set_mapping[feature_set],
                feature_level=opensmile.FeatureLevel.LowLevelDescriptors,
            )
            
            # フレーム単位で特徴量を抽出
            features_df = smile.process_file(wav_file_path)
            
            # 音声の長さを計算
            duration_seconds = int(len(features_df) * 0.01)  # 10msフレーム → 秒
            
            # ファイル名から日付とスロットを推定（例: "08-30.wav" → "08:00-08:30"）
            filename = Path(wav_file_path).stem
            date_str = datetime.now().strftime("%Y-%m-%d")
            
            # ファイル名からスロット情報を抽出
            if '-' in filename and filename.replace('-', '').isdigit():
                start_minute, end_minute = filename.split('-')
                slot = f"08:{start_minute}-08:{end_minute}"
            else:
                slot = "08:00-08:30"  # デフォルト
            
            # 1秒ごとにタイムラインポイントを生成
            timeline_points = []
            
            # 100フレーム = 1秒（10ms/フレーム）として計算
            frames_per_second = 100
            
            for second in range(min(duration_seconds, 1800)):  # 最大30分
                # その秒に対応するフレーム範囲を取得
                start_frame = second * frames_per_second
                end_frame = min((second + 1) * frames_per_second, len(features_df))
                
                if start_frame < len(features_df):
                    # その秒の特徴量を平均
                    second_features = features_df.iloc[start_frame:end_frame].mean()
                    features_dict = second_features.to_dict()
                    
                    # Plutchikの8感情で分析
                    emotion_scores = self._analyze_plutchik_emotions(features_dict)
                    primary_emotion = max(emotion_scores.keys(), key=lambda k: emotion_scores[k])
                    
                    # タイムスタンプを生成（HH:MM:SS形式）
                    timestamp = f"08:{int(second//60):02d}:{second%60:02d}"
                    
                    timeline_point = EmotionTimelinePoint(
                        timestamp=timestamp,
                        emotion=PlutchikEmotionEnum(primary_emotion),
                        scores=emotion_scores
                    )
                    
                    timeline_points.append(timeline_point)
            
            processing_time = time.time() - start_time
            
            return EmotionTimelineResult(
                date=date_str,
                slot=slot,
                filename=Path(wav_file_path).name,
                duration_seconds=duration_seconds,
                emotion_timeline=timeline_points,
                processing_time=processing_time
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            return EmotionTimelineResult(
                date=datetime.now().strftime("%Y-%m-%d"),
                slot="unknown",
                filename=Path(wav_file_path).name,
                duration_seconds=0,
                emotion_timeline=[],
                processing_time=processing_time,
                error=str(e)
            )
    
    def _analyze_plutchik_emotions(self, features: Dict[str, float]) -> Dict[str, float]:
        """
        Plutchikの8基本感情で分析
        
        Args:
            features: 抽出された特徴量
            
        Returns:
            Dict[str, float]: 8感情のスコア辞書
        """
        # F0（基本周波数）関連の特徴量
        f0_mean = features.get('F0final_sma', 0.0)
        f0_std = features.get('F0final_sma_de', 0.0)
        
        # エネルギー関連
        energy = features.get('audSpec_Rfilt_sma[0]', 0.0)
        
        # スペクトル特徴量
        spectral_centroid = features.get('audSpec_Rfilt_sma[1]', 0.0)
        
        # 初期スコア
        scores = {
            PlutchikEmotionEnum.ANGER.value: 0.0,
            PlutchikEmotionEnum.JOY.value: 0.0,
            PlutchikEmotionEnum.SADNESS.value: 0.0,
            PlutchikEmotionEnum.FEAR.value: 0.0,
            PlutchikEmotionEnum.DISGUST.value: 0.0,
            PlutchikEmotionEnum.TRUST.value: 0.0,
            PlutchikEmotionEnum.SURPRISE.value: 0.0,
            PlutchikEmotionEnum.ANTICIPATION.value: 0.0
        }
        
        # ルールベースの感情分析
        
        # Anger: 高いF0変動 + 高エネルギー
        if abs(f0_std) > 0.5 and energy > 0.1:
            scores[PlutchikEmotionEnum.ANGER.value] = min(0.8, abs(f0_std) * energy * 2)
        
        # Joy: 高めのF0 + 安定したエネルギー
        if f0_mean > 0.1 and energy > 0.05:
            scores[PlutchikEmotionEnum.JOY.value] = min(0.7, f0_mean * energy * 3)
        
        # Sadness: 低F0 + 低エネルギー
        if f0_mean < -0.1 and energy < 0.05:
            scores[PlutchikEmotionEnum.SADNESS.value] = min(0.6, abs(f0_mean) * (1 - energy) * 2)
        
        # Fear: 高いF0変動 + 中程度のエネルギー
        if abs(f0_std) > 0.3 and 0.03 < energy < 0.08:
            scores[PlutchikEmotionEnum.FEAR.value] = min(0.6, abs(f0_std) * energy * 4)
        
        # Surprise: 急激なF0変化
        if abs(f0_std) > 0.6:
            scores[PlutchikEmotionEnum.SURPRISE.value] = min(0.7, abs(f0_std) * 1.2)
        
        # Trust: 安定したF0 + 中程度のエネルギー
        if abs(f0_std) < 0.2 and 0.04 < energy < 0.1:
            scores[PlutchikEmotionEnum.TRUST.value] = min(0.5, (1 - abs(f0_std)) * energy * 2)
        
        # Anticipation: F0の上昇傾向
        if f0_mean > 0.05 and abs(f0_std) > 0.2:
            scores[PlutchikEmotionEnum.ANTICIPATION.value] = min(0.6, f0_mean * abs(f0_std) * 3)
        
        # Disgust: 低い音域 + 特定のスペクトル特性
        if spectral_centroid < -0.1 and energy > 0.02:
            scores[PlutchikEmotionEnum.DISGUST.value] = min(0.5, abs(spectral_centroid) * energy * 2)
        
        # スコアを正規化（softmax風）
        total = sum(scores.values())
        if total > 0:
            scores = {k: v / total for k, v in scores.items()}
        else:
            # デフォルトでTrustを設定
            scores[PlutchikEmotionEnum.TRUST.value] = 1.0
        
        return scores
    
    def extract_features_timeline(
        self,
        wav_file_path: str,
        feature_set: FeatureSetEnum = FeatureSetEnum.EGEMAPS_V02
    ) -> FeaturesTimelineResult:
        """
        音声ファイルから1秒ごとの特徴量タイムラインを抽出（感情分析なし）
        
        Args:
            wav_file_path: 音声ファイルのパス
            feature_set: 使用する特徴量セット
            
        Returns:
            FeaturesTimelineResult: 特徴量タイムライン結果
        """
        start_time = time.time()
        
        try:
            # OpenSMILEインスタンスを作成（LLD - Low Level Descriptorsを使用）
            smile = opensmile.Smile(
                feature_set=self.feature_set_mapping[feature_set],
                feature_level=opensmile.FeatureLevel.LowLevelDescriptors,
            )
            
            # フレーム単位で特徴量を抽出
            features_df = smile.process_file(wav_file_path)
            
            # 音声の長さを計算
            duration_seconds = int(len(features_df) * 0.01)  # 10msフレーム → 秒
            
            # ファイル名から日付とスロットを推定（例: "20-30.wav" → "08:20-08:30"）
            filename = Path(wav_file_path).stem
            date_str = datetime.now().strftime("%Y-%m-%d")
            
            # ファイル名からスロット情報を抽出
            if '-' in filename and filename.replace('-', '').isdigit():
                start_minute, end_minute = filename.split('-')
                slot = f"08:{start_minute}-08:{end_minute}"
            else:
                slot = "08:00-08:30"  # デフォルト
            
            # 1秒ごとにタイムラインポイントを生成
            timeline_points = []
            
            # 100フレーム = 1秒（10ms/フレーム）として計算
            frames_per_second = 100
            
            for second in range(min(duration_seconds, 1800)):  # 最大30分
                # その秒に対応するフレーム範囲を取得
                start_frame = second * frames_per_second
                end_frame = min((second + 1) * frames_per_second, len(features_df))
                
                if start_frame < len(features_df):
                    # その秒の特徴量を平均
                    second_features = features_df.iloc[start_frame:end_frame].mean()
                    features_dict = second_features.to_dict()
                    
                    # タイムスタンプを生成（HH:MM:SS形式）
                    timestamp = f"08:{int(second//60):02d}:{second%60:02d}"
                    
                    timeline_point = FeatureTimelinePoint(
                        timestamp=timestamp,
                        features=features_dict
                    )
                    
                    timeline_points.append(timeline_point)
            
            processing_time = time.time() - start_time
            
            return FeaturesTimelineResult(
                date=date_str,
                slot=slot,
                filename=Path(wav_file_path).name,
                duration_seconds=duration_seconds,
                features_timeline=timeline_points,
                processing_time=processing_time
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            return FeaturesTimelineResult(
                date=datetime.now().strftime("%Y-%m-%d"),
                slot="unknown",
                filename=Path(wav_file_path).name,
                duration_seconds=0,
                features_timeline=[],
                processing_time=processing_time,
                error=str(e)
            )


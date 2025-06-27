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
from models import FeatureSetEnum, FeatureExtractionResult, EmotionPrediction


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
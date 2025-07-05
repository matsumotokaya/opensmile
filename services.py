"""
サービスレイヤー
OpenSMILEとの統合および特徴量処理
"""

import time
import os
from pathlib import Path
from typing import Dict, List, Optional
import opensmile
from datetime import datetime
import aiohttp
from models import (
    FeatureSetEnum,
    FeatureTimelinePoint,
    FeaturesTimelineResult
)


class EmotionAnalysisService:
    """感情分析サービス"""
    
    def __init__(self):
        # OpenSMILE特徴量セットマッピング
        self.feature_set_mapping = {
            FeatureSetEnum.EGEMAPS_V02: opensmile.FeatureSet.eGeMAPSv02,
        }
    
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


class VaultAPIService:
    """EC2 Vault APIからWAVファイルを取得するサービス"""
    
    def __init__(self, base_url: str = "https://api.hey-watch.me"):
        self.base_url = base_url
    
    async def fetch_wav_file(self, device_id: str, date: str, time_slot: str, temp_dir: str) -> Optional[str]:
        """
        Vault APIからWAVファイルを取得して一時ファイルに保存
        
        Args:
            device_id: デバイスID (例: device123)
            date: 日付 (例: 2025-06-25)
            time_slot: 時間スロット (例: 20-30)
            temp_dir: 一時ディレクトリのパス
            
        Returns:
            Optional[str]: 保存されたファイルのパス（失敗時はNone）
        """
        try:
            # Whisper APIと同じエンドポイント形式を使用
            url = f"{self.base_url}/download?device_id={device_id}&date={date}&slot={time_slot}"
            
            # SSL検証をスキップするコネクターを作成
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        # 一時ファイルに保存
                        temp_file_path = os.path.join(temp_dir, f"{time_slot}.wav")
                        with open(temp_file_path, 'wb') as f:
                            f.write(await response.read())
                        
                        print(f"✅ WAVファイル取得成功: {time_slot}.wav")
                        return temp_file_path
                    else:
                        print(f"❌ WAVファイル取得失敗: {time_slot}.wav (ステータス: {response.status})")
                        return None
                        
        except Exception as e:
            print(f"❌ WAVファイル取得エラー: {time_slot}.wav - {str(e)}")
            return None
    
    async def get_available_wav_files(self, device_id: str, date: str) -> List[str]:
        """
        指定デバイス・日付で利用可能なWAVファイルのスロット一覧を取得
        
        Args:
            device_id: デバイスID
            date: 日付
            
        Returns:
            List[str]: 利用可能な時間スロットのリスト
        """
        available_slots = []
        
        # 48個の時間ブロックを確認（Whisper APIと同じロジック）
        time_blocks = [f"{hour:02d}-{minute:02d}" for hour in range(24) for minute in [0, 30]]
        
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            for time_slot in time_blocks:
                try:
                    url = f"{self.base_url}/download?device_id={device_id}&date={date}&slot={time_slot}"
                    async with session.get(url) as response:
                        if response.status == 200:
                            available_slots.append(time_slot)
                except Exception:
                    # エラーは無視して継続
                    pass
        
        return available_slots
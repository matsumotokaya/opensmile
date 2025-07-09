#!/usr/bin/env python3
"""
Supabase統合テストスクリプト
"""

import asyncio
import os
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client
from supabase_service import SupabaseService

# 環境変数の読み込み
load_dotenv()

async def test_supabase_connection():
    """Supabase接続テスト"""
    print("=== Supabase接続テスト ===")
    
    # 環境変数確認
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        print("❌ エラー: SUPABASE_URLまたはSUPABASE_KEYが設定されていません")
        return False
    
    print(f"✅ SUPABASE_URL: {supabase_url}")
    print(f"✅ SUPABASE_KEY: ****** (設定済み)")
    
    try:
        # Supabaseクライアント作成
        supabase: Client = create_client(supabase_url, supabase_key)
        print("✅ Supabaseクライアント作成成功")
        
        # テーブル存在確認（簡単なクエリ）
        response = supabase.table("emotion_opensmile").select("*").limit(1).execute()
        print("✅ emotion_opensmileテーブルアクセス成功")
        
        return True
        
    except Exception as e:
        print(f"❌ エラー: {str(e)}")
        return False

async def test_upsert_emotion_data():
    """emotion_opensmileテーブルへのUPSERTテスト"""
    print("\n=== UPSERT機能テスト ===")
    
    try:
        # Supabaseサービス初期化
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        supabase_client: Client = create_client(supabase_url, supabase_key)
        supabase_service = SupabaseService(supabase_client)
        
        # テストデータ
        test_data = {
            "device_id": "test_device_001",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "time_block": "12-30",
            "filename": "12-30.wav",
            "duration_seconds": 180,
            "features_timeline": [
                {
                    "timestamp": "12:30:00",
                    "features": {
                        "F0_mean": 150.5,
                        "loudness_mean": -25.3,
                        "spectralFlux_mean": 0.012
                    }
                },
                {
                    "timestamp": "12:30:01",
                    "features": {
                        "F0_mean": 152.1,
                        "loudness_mean": -24.8,
                        "spectralFlux_mean": 0.015
                    }
                }
            ],
            "processing_time": 2.5,
            "error": None
        }
        
        # UPSERT実行
        result = await supabase_service.upsert_emotion_data(**test_data)
        print("✅ UPSERT成功")
        print(f"保存されたデータ: {result}")
        
        return True
        
    except Exception as e:
        print(f"❌ UPSERTエラー: {str(e)}")
        return False

async def test_batch_upsert():
    """バッチUPSERTテスト"""
    print("\n=== バッチUPSERTテスト ===")
    
    try:
        # Supabaseサービス初期化
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        supabase_client: Client = create_client(supabase_url, supabase_key)
        supabase_service = SupabaseService(supabase_client)
        
        # 複数のテストレコード
        test_records = [
            {
                "device_id": "test_device_001",
                "date": datetime.now().strftime("%Y-%m-%d"),
                "time_block": "13-00",
                "filename": "13-00.wav",
                "duration_seconds": 120,
                "features_timeline": [
                    {"timestamp": "13:00:00", "features": {"F0_mean": 155.2}}
                ],
                "processing_time": 1.8,
                "error": None
            },
            {
                "device_id": "test_device_001",
                "date": datetime.now().strftime("%Y-%m-%d"),
                "time_block": "13-30",
                "filename": "13-30.wav",
                "duration_seconds": 0,
                "features_timeline": [],
                "processing_time": 0.1,
                "error": "ファイル取得エラー"
            }
        ]
        
        # バッチUPSERT実行
        results = await supabase_service.batch_upsert_emotion_data(test_records)
        print(f"✅ バッチUPSERT成功: {len(results)}件")
        
        return True
        
    except Exception as e:
        print(f"❌ バッチUPSERTエラー: {str(e)}")
        return False

async def main():
    """メインテスト実行"""
    print("OpenSMILE API - Supabase統合テスト開始\n")
    
    # 各テストを実行
    tests = [
        test_supabase_connection(),
        test_upsert_emotion_data(),
        test_batch_upsert()
    ]
    
    results = await asyncio.gather(*tests)
    
    # 結果サマリー
    print("\n=== テスト結果サマリー ===")
    print(f"Supabase接続テスト: {'✅ 成功' if results[0] else '❌ 失敗'}")
    print(f"UPSERT機能テスト: {'✅ 成功' if results[1] else '❌ 失敗'}")
    print(f"バッチUPSERTテスト: {'✅ 成功' if results[2] else '❌ 失敗'}")
    
    if all(results):
        print("\n✅ 全てのテストが成功しました！")
    else:
        print("\n❌ 一部のテストが失敗しました。")

if __name__ == "__main__":
    asyncio.run(main())
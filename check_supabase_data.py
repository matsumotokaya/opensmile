#!/usr/bin/env python3
"""
Supabaseに保存されたデータを確認するスクリプト
"""

import os
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client
import json

# 環境変数の読み込み
load_dotenv()

def check_data(device_id: str, date: str):
    """Supabaseからデータを取得して表示"""
    
    # Supabaseクライアント作成
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    supabase: Client = create_client(supabase_url, supabase_key)
    
    print(f"=== Supabaseデータ確認 ===")
    print(f"デバイスID: {device_id}")
    print(f"日付: {date}")
    print("=" * 50)
    
    try:
        # データ取得
        response = supabase.table("emotion_opensmile")\
            .select("*")\
            .eq("device_id", device_id)\
            .eq("date", date)\
            .order("time_block")\
            .execute()
        
        if response.data:
            print(f"\n✅ {len(response.data)}件のレコードが見つかりました\n")
            
            for record in response.data:
                print(f"時間ブロック: {record['time_block']}")
                print(f"  - ファイル名: {record['filename']}")
                print(f"  - 長さ: {record['duration_seconds']}秒")
                print(f"  - タイムライン数: {len(record['features_timeline'])}個")
                print(f"  - 処理時間: {record['processing_time']:.2f}秒")
                
                if record.get('error'):
                    print(f"  - エラー: {record['error']}")
                
                # 最初のタイムスタンプと特徴量のサンプル表示
                if record['features_timeline'] and len(record['features_timeline']) > 0:
                    first = record['features_timeline'][0]
                    print(f"  - 最初のタイムスタンプ: {first['timestamp']}")
                    print(f"  - 特徴量数: {len(first['features'])}個")
                
                print()
        else:
            print(f"❌ データが見つかりませんでした")
            
    except Exception as e:
        print(f"❌ エラー: {str(e)}")

if __name__ == "__main__":
    import sys
    
    device_id = sys.argv[1] if len(sys.argv) > 1 else "user123"
    date = sys.argv[2] if len(sys.argv) > 2 else "2025-06-21"
    
    check_data(device_id, date)
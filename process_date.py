#!/usr/bin/env python3
"""
特定日付のデータを処理するスクリプト
"""

import asyncio
import aiohttp
import json
from datetime import datetime

async def process_date(device_id: str, date: str):
    """指定された日付のデータを処理"""
    
    url = "http://localhost:8011/process/vault-data"
    
    # リクエストデータ
    request_data = {
        "device_id": device_id,
        "date": date,
        "feature_set": "eGeMAPSv02"
    }
    
    print(f"=== OpenSMILE処理開始 ===")
    print(f"デバイスID: {device_id}")
    print(f"対象日付: {date}")
    print(f"API URL: {url}")
    print("=" * 50)
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=request_data) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"\n✅ 処理成功!")
                    print(f"処理ファイル数: {result['processed_files']}")
                    print(f"保存ファイル数: {len(result['saved_files'])}")
                    print(f"総処理時間: {result['total_processing_time']:.2f}秒")
                    print(f"メッセージ: {result['message']}")
                    
                    # エラーがあったファイルを表示
                    error_count = 0
                    for r in result['results']:
                        if r.get('error'):
                            error_count += 1
                            print(f"❌ エラー: {r['slot']} - {r['error']}")
                    
                    if error_count > 0:
                        print(f"\n⚠️  {error_count}個のファイルでエラーが発生しました")
                    
                else:
                    error_text = await response.text()
                    print(f"❌ APIエラー: ステータス {response.status}")
                    print(f"エラー詳細: {error_text}")
                    
    except Exception as e:
        print(f"❌ 実行エラー: {str(e)}")
        print("APIサーバーが起動していることを確認してください")

async def main():
    """メイン処理"""
    import sys
    
    # コマンドライン引数から取得、デフォルト値を設定
    if len(sys.argv) > 1:
        device_id = sys.argv[1]
    else:
        device_id = input("デバイスIDを入力してください: ")
    
    if len(sys.argv) > 2:
        date = sys.argv[2]
    else:
        date = "2025-07-08"
    
    await process_date(device_id, date)

if __name__ == "__main__":
    asyncio.run(main())
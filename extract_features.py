#!/usr/bin/env python3
"""
OpenSMILE音声特徴量抽出スクリプト

指定されたディレクトリ内の.wavファイルから音声特徴量を抽出し、
CSVまたはJSON形式で保存します。
"""

import os
import argparse
import pandas as pd
import opensmile
import json
from pathlib import Path


def extract_features_from_wav(wav_file_path, output_format='csv', feature_set='eGeMAPSv02'):
    """
    .wavファイルから音声特徴量を抽出
    
    Args:
        wav_file_path (str): .wavファイルのパス
        output_format (str): 出力形式 ('csv' または 'json')
        feature_set (str): 使用する特徴量セット
    
    Returns:
        str: 出力ファイルのパス
    """
    
    # OpenSMILEインスタンスを作成
    smile = opensmile.Smile(
        feature_set=getattr(opensmile.FeatureSet, feature_set),
        feature_level=opensmile.FeatureLevel.Functionals,
    )
    
    # 特徴量を抽出
    print(f"特徴量を抽出中: {wav_file_path}")
    features = smile.process_file(wav_file_path)
    
    # 出力ファイル名を生成
    base_name = Path(wav_file_path).stem
    if output_format == 'csv':
        output_file = f"{base_name}_features.csv"
        features.to_csv(output_file, index=True)
    elif output_format == 'json':
        output_file = f"{base_name}_features.json"
        # DataFrameをJSON形式に変換
        features_dict = {
            'filename': base_name,
            'features': features.iloc[0].to_dict()
        }
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(features_dict, f, ensure_ascii=False, indent=2)
    else:
        raise ValueError("output_format は 'csv' または 'json' である必要があります")
    
    print(f"特徴量を保存しました: {output_file}")
    print(f"抽出された特徴量数: {len(features.columns)}")
    
    return output_file


def process_directory(directory_path='.', output_format='csv', feature_set='eGeMAPSv02'):
    """
    ディレクトリ内のすべての.wavファイルを処理
    
    Args:
        directory_path (str): 処理するディレクトリのパス
        output_format (str): 出力形式
        feature_set (str): 使用する特徴量セット
    
    Returns:
        list: 処理されたファイルのリスト
    """
    processed_files = []
    wav_files = list(Path(directory_path).glob('*.wav'))
    
    if not wav_files:
        print(f"警告: {directory_path} に.wavファイルが見つかりませんでした")
        return processed_files
    
    print(f"{len(wav_files)}個の.wavファイルが見つかりました")
    
    for wav_file in wav_files:
        try:
            output_file = extract_features_from_wav(
                str(wav_file), 
                output_format=output_format,
                feature_set=feature_set
            )
            processed_files.append(output_file)
        except Exception as e:
            print(f"エラー: {wav_file} の処理中にエラーが発生しました: {str(e)}")
    
    return processed_files


def list_available_feature_sets():
    """利用可能な特徴量セットを表示"""
    print("利用可能な特徴量セット:")
    feature_sets = [attr for attr in dir(opensmile.FeatureSet) if not attr.startswith('_')]
    for i, fs in enumerate(feature_sets, 1):
        print(f"  {i}. {fs}")


def main():
    parser = argparse.ArgumentParser(
        description='OpenSMILEを使用した音声特徴量抽出'
    )
    parser.add_argument(
        '--directory', '-d', 
        default='.', 
        help='処理するディレクトリのパス (デフォルト: 現在のディレクトリ)'
    )
    parser.add_argument(
        '--format', '-f', 
        choices=['csv', 'json'], 
        default='csv',
        help='出力形式 (デフォルト: csv)'
    )
    parser.add_argument(
        '--feature-set', '-s',
        default='eGeMAPSv02',
        help='使用する特徴量セット (デフォルト: eGeMAPSv02)'
    )
    parser.add_argument(
        '--list-features', '-l',
        action='store_true',
        help='利用可能な特徴量セットを表示'
    )
    
    args = parser.parse_args()
    
    if args.list_features:
        list_available_feature_sets()
        return
    
    print("OpenSMILE音声特徴量抽出スクリプト")
    print("=" * 40)
    print(f"ディレクトリ: {args.directory}")
    print(f"出力形式: {args.format}")
    print(f"特徴量セット: {args.feature_set}")
    print("=" * 40)
    
    try:
        processed_files = process_directory(
            directory_path=args.directory,
            output_format=args.format,
            feature_set=args.feature_set
        )
        
        print("\n処理完了!")
        print(f"処理されたファイル数: {len(processed_files)}")
        if processed_files:
            print("出力ファイル:")
            for file in processed_files:
                print(f"  - {file}")
    
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
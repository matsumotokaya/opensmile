from flask import Flask, jsonify, request
import os
import opensmile
import pandas as pd
from pathlib import Path
import json

app = Flask(__name__)

@app.route('/')
def hello():
    return 'OpenSMILE Audio Feature Extraction API'

@app.route('/health')
def health():
    """ヘルスチェックエンドポイント"""
    return jsonify({
        'status': 'healthy',
        'service': 'OpenSMILE Feature Extraction',
        'version': '1.0.0'
    })

@app.route('/features', methods=['GET'])
def list_available_features():
    """利用可能な特徴量セットを返す"""
    try:
        feature_sets = [attr for attr in dir(opensmile.FeatureSet) if not attr.startswith('_')]
        return jsonify({
            'available_feature_sets': feature_sets,
            'default': 'eGeMAPSv02'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/extract', methods=['POST'])
def extract_features():
    """音声ファイルから特徴量を抽出"""
    try:
        # リクエストパラメータを取得
        feature_set = request.json.get('feature_set', 'eGeMAPSv02') if request.json else 'eGeMAPSv02'
        
        # 現在のディレクトリの.wavファイルを検索
        wav_files = list(Path('.').glob('*.wav'))
        
        if not wav_files:
            return jsonify({
                'error': '現在のディレクトリに.wavファイルが見つかりません',
                'directory': os.getcwd()
            }), 404
        
        # OpenSMILEインスタンスを作成
        smile = opensmile.Smile(
            feature_set=getattr(opensmile.FeatureSet, feature_set),
            feature_level=opensmile.FeatureLevel.Functionals,
        )
        
        results = []
        for wav_file in wav_files:
            try:
                # 特徴量を抽出
                features = smile.process_file(str(wav_file))
                
                # 結果を辞書形式に変換
                result = {
                    'filename': wav_file.name,
                    'feature_count': len(features.columns),
                    'features': features.iloc[0].to_dict()
                }
                results.append(result)
                
            except Exception as file_error:
                results.append({
                    'filename': wav_file.name,
                    'error': str(file_error)
                })
        
        return jsonify({
            'feature_set': feature_set,
            'processed_files': len(results),
            'results': results
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/files', methods=['GET'])
def list_wav_files():
    """現在のディレクトリの.wavファイル一覧を返す"""
    try:
        wav_files = list(Path('.').glob('*.wav'))
        return jsonify({
            'directory': os.getcwd(),
            'wav_files': [f.name for f in wav_files],
            'count': len(wav_files)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
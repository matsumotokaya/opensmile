"""
FastAPI感情分析APIのテスト
pytest + httpxを使用
"""

import pytest
import httpx
import asyncio
from pathlib import Path
from fastapi.testclient import TestClient

from main import app
from models import FeatureSetEnum


# テストクライアントの作成
client = TestClient(app)


class TestBasicEndpoints:
    """基本エンドポイントのテスト"""
    
    def test_root_endpoint(self):
        """ルートエンドポイントのテスト"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert data["version"] == "2.0.0"
    
    def test_health_check(self):
        """ヘルスチェックエンドポイントのテスト"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "OpenSMILE感情分析API"
        assert "opensmile_version" in data
    
    def test_available_features(self):
        """利用可能特徴量セットエンドポイントのテスト"""
        response = client.get("/features")
        assert response.status_code == 200
        data = response.json()
        assert "available_feature_sets" in data
        assert "default" in data
        assert data["default"] == "eGeMAPSv02"
        assert "descriptions" in data
        
        # 期待される特徴量セットが含まれているかチェック
        expected_sets = ["eGeMAPSv02", "ComParE_2016", "GeMAPS"]
        for expected_set in expected_sets:
            assert expected_set in data["available_feature_sets"]
    
    def test_file_list(self):
        """ファイル一覧エンドポイントのテスト"""
        response = client.get("/files")
        assert response.status_code == 200
        data = response.json()
        assert "directory" in data
        assert "wav_files" in data
        assert "count" in data
        assert isinstance(data["wav_files"], list)
        assert data["count"] == len(data["wav_files"])


class TestFeatureExtraction:
    """特徴量抽出のテスト"""
    
    def test_extract_features_no_request_body(self):
        """リクエストボディなしでの特徴量抽出テスト"""
        response = client.post("/extract")
        
        # ファイルが存在しない場合は404、存在する場合は200
        if response.status_code == 404:
            data = response.json()
            assert "現在のディレクトリに.wavファイルが見つかりません" in data["detail"]
        else:
            assert response.status_code == 200
            data = response.json()
            assert "feature_set" in data
            assert "processed_files" in data
            assert "results" in data
            assert data["feature_set"] == "eGeMAPSv02"
    
    def test_extract_features_with_request_body(self):
        """リクエストボディありでの特徴量抽出テスト"""
        request_body = {
            "feature_set": "eGeMAPSv02",
            "include_raw_features": False
        }
        response = client.post("/extract", json=request_body)
        
        # ファイルが存在しない場合は404、存在する場合は200
        if response.status_code == 404:
            data = response.json()
            assert "現在のディレクトリに.wavファイルが見つかりません" in data["detail"]
        else:
            assert response.status_code == 200
            data = response.json()
            assert data["feature_set"] == "eGeMAPSv02"
            assert isinstance(data["results"], list)
            
            # 結果がある場合の検証
            if data["results"]:
                result = data["results"][0]
                assert "filename" in result
                assert "feature_count" in result
                assert "features" in result
                
                # include_raw_features=Falseの場合、featuresは空であるべき
                assert result["features"] == {}
    
    def test_extract_features_with_raw_features(self):
        """生特徴量を含む特徴量抽出テスト"""
        request_body = {
            "feature_set": "eGeMAPSv02",
            "include_raw_features": True
        }
        response = client.post("/extract", json=request_body)
        
        if response.status_code == 200:
            data = response.json()
            if data["results"]:
                result = data["results"][0]
                # include_raw_features=Trueの場合、featuresにデータがあるべき
                if result.get("error") is None:
                    assert len(result["features"]) > 0


class TestEmotionAnalysis:
    """感情分析のテスト"""
    
    def test_analyze_emotions_no_request_body(self):
        """リクエストボディなしでの感情分析テスト"""
        response = client.post("/analyze")
        
        # ファイルが存在しない場合は404、存在する場合は200
        if response.status_code == 404:
            data = response.json()
            assert "現在のディレクトリに.wavファイルが見つかりません" in data["detail"]
        else:
            assert response.status_code == 200
            data = response.json()
            assert "feature_set" in data
            assert "processed_files" in data
            assert "results" in data
            assert data["feature_set"] == "eGeMAPSv02"
    
    def test_analyze_emotions_with_request_body(self):
        """リクエストボディありでの感情分析テスト"""
        request_body = {
            "feature_set": "eGeMAPSv02",
            "include_raw_features": False
        }
        response = client.post("/analyze", json=request_body)
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data["results"], list)
            
            # 結果がある場合の検証
            if data["results"]:
                result = data["results"][0]
                assert "filename" in result
                
                # エラーがない場合の検証
                if result.get("error") is None:
                    assert "primary_emotion" in result
                    emotion = result["primary_emotion"]
                    assert "emotion" in emotion
                    assert "confidence" in emotion
                    assert 0.0 <= emotion["confidence"] <= 1.0


class TestErrorHandling:
    """エラーハンドリングのテスト"""
    
    def test_invalid_feature_set(self):
        """無効な特徴量セットでのテスト"""
        request_body = {
            "feature_set": "INVALID_FEATURE_SET",
            "include_raw_features": False
        }
        response = client.post("/extract", json=request_body)
        
        # 無効な特徴量セットは422 Unprocessable Entityを返すべき
        assert response.status_code == 422
    
    def test_invalid_json(self):
        """無効なJSONでのテスト"""
        response = client.post(
            "/extract",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        # 無効なJSONは422を返すべき
        assert response.status_code == 422


@pytest.mark.asyncio
class TestAsyncEndpoints:
    """非同期エンドポイントのテスト"""
    
    async def test_health_check_async(self):
        """非同期でのヘルスチェックテスト"""
        async with httpx.AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
    
    async def test_features_async(self):
        """非同期での特徴量セット取得テスト"""
        async with httpx.AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get("/features")
            assert response.status_code == 200
            data = response.json()
            assert "available_feature_sets" in data


def test_openapi_schema():
    """OpenAPIスキーマの検証"""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "openapi" in schema
    assert "info" in schema
    assert schema["info"]["title"] == "OpenSMILE感情分析API"


def test_docs_endpoint():
    """API ドキュメントエンドポイントのテスト"""
    response = client.get("/docs")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")


if __name__ == "__main__":
    # テストを直接実行する場合
    pytest.main([__file__, "-v"])
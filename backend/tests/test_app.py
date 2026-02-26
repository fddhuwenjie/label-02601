"""
API 接口单元测试
"""
import pytest
import json
from app import app, VALID_THEMES, MIN_WIDTH, MAX_WIDTH


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


class TestHealthCheck:
    """健康检查接口测试"""
    
    def test_health_check(self, client):
        response = client.get('/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert data['service'] == 'md2img'


class TestConvertEndpoint:
    """文本转换接口测试"""
    
    def test_missing_markdown(self, client):
        """测试缺少 markdown 参数"""
        response = client.post('/convert', json={})
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['code'] == 'MISSING_CONTENT'
    
    def test_invalid_width_too_small(self, client):
        """测试宽度过小"""
        response = client.post('/convert', json={
            'markdown': '# Test',
            'width': 100
        })
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['code'] == 'INVALID_WIDTH'
    
    def test_invalid_width_too_large(self, client):
        """测试宽度过大"""
        response = client.post('/convert', json={
            'markdown': '# Test',
            'width': 5000
        })
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['code'] == 'INVALID_WIDTH'
    
    def test_invalid_width_type(self, client):
        """测试宽度类型错误"""
        response = client.post('/convert', json={
            'markdown': '# Test',
            'width': 'abc'
        })
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['code'] == 'INVALID_WIDTH'
    
    def test_invalid_theme(self, client):
        """测试无效主题"""
        response = client.post('/convert', json={
            'markdown': '# Test',
            'theme': 'invalid'
        })
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['code'] == 'INVALID_THEME'


class TestConvertFileEndpoint:
    """文件上传接口测试"""
    
    def test_no_file(self, client):
        """测试未上传文件"""
        response = client.post('/convert/file')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['code'] == 'NO_FILE'
    
    def test_empty_filename(self, client):
        """测试空文件名"""
        from io import BytesIO
        response = client.post('/convert/file', data={
            'file': (BytesIO(b''), '')
        })
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['code'] == 'NO_FILE_SELECTED'
    
    def test_invalid_width(self, client):
        """测试无效宽度"""
        from io import BytesIO
        response = client.post('/convert/file', data={
            'file': (BytesIO(b'# Test'), 'test.md'),
            'width': '100'
        })
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['code'] == 'INVALID_WIDTH'
    
    def test_invalid_theme(self, client):
        """测试无效主题"""
        from io import BytesIO
        response = client.post('/convert/file', data={
            'file': (BytesIO(b'# Test'), 'test.md'),
            'theme': 'blue'
        })
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['code'] == 'INVALID_THEME'


class TestConstants:
    """常量配置测试"""
    
    def test_valid_themes(self):
        assert 'light' in VALID_THEMES
        assert 'dark' in VALID_THEMES
    
    def test_width_range(self):
        assert MIN_WIDTH == 200
        assert MAX_WIDTH == 4000

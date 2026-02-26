"""
Converter 单元测试
"""
import pytest
import os
import tempfile
from converter import MarkdownToImageConverter, ObsidianPreprocessor, ObsidianPostprocessor


class TestObsidianPreprocessor:
    """测试 Obsidian 预处理器"""
    
    def test_remove_comments(self):
        """测试移除 %%注释%%"""
        preprocessor = ObsidianPreprocessor(None)
        lines = ['Hello %%这是注释%% World', '正常文本']
        result = preprocessor.run(lines)
        assert result == ['Hello  World', '正常文本']
    
    def test_multiple_comments(self):
        """测试多个注释"""
        preprocessor = ObsidianPreprocessor(None)
        lines = ['%%注释1%% 文本 %%注释2%%']
        result = preprocessor.run(lines)
        assert result == [' 文本 ']


class TestObsidianPostprocessor:
    """测试 Obsidian 后处理器"""
    
    def test_highlight(self):
        """测试 ==高亮== 语法"""
        postprocessor = ObsidianPostprocessor(None)
        result = postprocessor.run('这是==高亮文本==测试')
        assert '<mark>高亮文本</mark>' in result
    
    def test_wikilink(self):
        """测试 [[双链]] 语法"""
        postprocessor = ObsidianPostprocessor(None)
        result = postprocessor.run('链接到[[笔记页面]]')
        assert '<span class="wikilink">笔记页面</span>' in result
    
    def test_wikilink_with_alias(self):
        """测试 [[双链|别名]] 语法"""
        postprocessor = ObsidianPostprocessor(None)
        result = postprocessor.run('链接到[[笔记页面|显示文本]]')
        assert '<span class="wikilink">显示文本</span>' in result
    
    def test_embed(self):
        """测试 ![[嵌入]] 语法"""
        postprocessor = ObsidianPostprocessor(None)
        result = postprocessor.run('嵌入 ![[图片.png]]')
        assert '<span class="embed">📎 图片.png</span>' in result


class TestMarkdownToImageConverter:
    """测试 Markdown 转图片转换器"""
    
    @pytest.fixture
    def converter(self):
        return MarkdownToImageConverter()
    
    def test_md_to_html_basic(self, converter):
        """测试基本 Markdown 转 HTML"""
        html = converter._md_to_html('# 标题\n\n段落文本')
        assert '标题</h1>' in html
        assert '<p>段落文本</p>' in html
    
    def test_md_to_html_code_block(self, converter):
        """测试代码块"""
        md = '```python\nprint("hello")\n```'
        html = converter._md_to_html(md)
        assert 'print' in html
    
    def test_md_to_html_table(self, converter):
        """测试表格"""
        md = '| A | B |\n|---|---|\n| 1 | 2 |'
        html = converter._md_to_html(md)
        assert '<table>' in html
        assert '<th>A</th>' in html
    
    def test_md_to_html_obsidian_highlight(self, converter):
        """测试 Obsidian 高亮语法"""
        html = converter._md_to_html('这是==高亮==文本')
        assert '<mark>高亮</mark>' in html
    
    def test_get_css_light_theme(self, converter):
        """测试浅色主题 CSS"""
        css = converter._get_css('light')
        assert '#ffffff' in css
        assert '#333333' in css
    
    def test_get_css_dark_theme(self, converter):
        """测试深色主题 CSS"""
        css = converter._get_css('dark')
        assert '#1e1e1e' in css
        assert '#d4d4d4' in css
    
    def test_process_callouts(self, converter):
        """测试 Callout 处理"""
        md = '> [!note] 注意\n> 这是内容'
        result = converter._process_callouts(md)
        assert 'callout' in result
        assert '注意' in result
    
    @pytest.mark.integration
    def test_convert_creates_image(self, converter):
        """测试完整转换流程（需要 Chromium）"""
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            output_path = f.name
        
        try:
            converter.convert('# Hello World', output_path)
            assert os.path.exists(output_path)
            assert os.path.getsize(output_path) > 0
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)

"""
Markdown to Image Converter
支持 Obsidian 风格的 Markdown 语法
"""
import logging
import re
import markdown
from markdown.extensions import fenced_code, tables, toc
from markdown.preprocessors import Preprocessor
from markdown.postprocessors import Postprocessor
from PIL import Image, ImageDraw
from html2image import Html2Image
import tempfile
import os

logger = logging.getLogger(__name__)


class ObsidianPreprocessor(Preprocessor):
    """预处理 Obsidian 特有语法"""
    
    def run(self, lines):
        new_lines = []
        for line in lines:
            # 移除 Obsidian 注释 %%...%%
            line = re.sub(r'%%.*?%%', '', line)
            new_lines.append(line)
        return new_lines


class ObsidianPostprocessor(Postprocessor):
    """后处理 Obsidian 特有语法转 HTML"""
    
    def run(self, text):
        # ==高亮== -> <mark>高亮</mark>
        text = re.sub(r'==(.+?)==', r'<mark>\1</mark>', text)
        
        # [[双链]] -> 显示为链接样式
        text = re.sub(r'\[\[([^\]|]+)\]\]', r'<span class="wikilink">\1</span>', text)
        
        # [[双链|显示文本]] -> 显示为链接样式
        text = re.sub(r'\[\[([^\]|]+)\|([^\]]+)\]\]', r'<span class="wikilink">\2</span>', text)
        
        # ![[嵌入]] -> 显示为嵌入提示
        text = re.sub(r'!\[\[([^\]]+)\]\]', r'<span class="embed">📎 \1</span>', text)
        
        return text


class ObsidianExtension(markdown.Extension):
    """Obsidian 语法扩展"""
    
    def extendMarkdown(self, md):
        md.preprocessors.register(ObsidianPreprocessor(md), 'obsidian_pre', 30)
        md.postprocessors.register(ObsidianPostprocessor(md), 'obsidian_post', 30)


class MarkdownToImageConverter:
    """Markdown 转图片转换器"""
    
    def __init__(self):
        logger.info("初始化 Markdown 转换器")
        self.md = markdown.Markdown(
            extensions=[
                'fenced_code',
                'tables',
                'toc',
                'nl2br',
                'sane_lists',
                'codehilite',
                ObsidianExtension(),
            ],
            extension_configs={
                'codehilite': {
                    'css_class': 'highlight',
                    'linenums': False,
                }
            }
        )
    
    def _get_css(self, theme='light'):
        """获取样式表"""
        if theme == 'dark':
            bg_color = '#1e1e1e'
            text_color = '#d4d4d4'
            code_bg = '#2d2d2d'
            border_color = '#404040'
            link_color = '#6ab0f3'
        else:
            bg_color = '#ffffff'
            text_color = '#333333'
            code_bg = '#f5f5f5'
            border_color = '#e0e0e0'
            link_color = '#0066cc'
        
        return f'''
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            font-size: 16px;
            line-height: 1.6;
            color: {text_color};
            background-color: {bg_color};
            padding: 40px;
            margin: 0;
        }}
        h1, h2, h3, h4, h5, h6 {{
            margin-top: 24px;
            margin-bottom: 16px;
            font-weight: 600;
            line-height: 1.25;
        }}
        h1 {{ font-size: 2em; border-bottom: 1px solid {border_color}; padding-bottom: 0.3em; }}
        h2 {{ font-size: 1.5em; border-bottom: 1px solid {border_color}; padding-bottom: 0.3em; }}
        h3 {{ font-size: 1.25em; }}
        p {{ margin-bottom: 16px; }}
        code {{
            font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
            font-size: 85%;
            background-color: {code_bg};
            padding: 0.2em 0.4em;
            border-radius: 3px;
        }}
        pre {{
            background-color: {code_bg};
            padding: 16px;
            overflow: auto;
            border-radius: 6px;
            line-height: 1.45;
        }}
        pre code {{
            background-color: transparent;
            padding: 0;
        }}
        blockquote {{
            margin: 0;
            padding: 0 1em;
            color: #6a737d;
            border-left: 0.25em solid {border_color};
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin-bottom: 16px;
        }}
        th, td {{
            padding: 6px 13px;
            border: 1px solid {border_color};
        }}
        th {{
            font-weight: 600;
            background-color: {code_bg};
        }}
        a {{
            color: {link_color};
            text-decoration: none;
        }}
        ul, ol {{
            padding-left: 2em;
            margin-bottom: 16px;
        }}
        li {{
            margin-bottom: 4px;
        }}
        img {{
            max-width: 100%;
        }}
        hr {{
            border: none;
            border-top: 1px solid {border_color};
            margin: 24px 0;
        }}
        .highlight {{
            background-color: {code_bg};
            padding: 16px;
            border-radius: 6px;
            overflow: auto;
        }}
        mark {{
            background-color: #fff3a3;
            padding: 0.1em 0.2em;
            border-radius: 2px;
        }}
        .wikilink {{
            color: {link_color};
            text-decoration: underline;
            text-decoration-style: dotted;
        }}
        .embed {{
            display: inline-block;
            background-color: {code_bg};
            padding: 0.2em 0.5em;
            border-radius: 4px;
            font-size: 0.9em;
            color: #666;
        }}
        .callout {{
            padding: 12px 16px;
            margin: 16px 0;
            border-radius: 4px;
            border-left: 4px solid {link_color};
            background-color: {code_bg};
        }}
        '''
    
    def _md_to_html(self, markdown_content):
        """将 Markdown 转换为 HTML"""
        self.md.reset()
        html_content = self.md.convert(markdown_content)
        return html_content
    
    def convert(self, markdown_content, output_path, width=800, theme='light'):
        """
        将 Markdown 内容转换为图片
        
        Args:
            markdown_content: Markdown 文本
            output_path: 输出图片路径
            width: 图片宽度
            theme: 主题 (light/dark)
        """
        logger.debug(f"开始转换, width={width}, theme={theme}")
        
        # 预处理 Obsidian callout 语法
        markdown_content = self._process_callouts(markdown_content)
        
        html_body = self._md_to_html(markdown_content)
        css = self._get_css(theme)
        
        full_html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>{css}</style>
        </head>
        <body>
            {html_body}
        </body>
        </html>
        '''
        
        # 使用 html2image 转换
        temp_dir = tempfile.gettempdir()
        hti = Html2Image(
            output_path=temp_dir, 
            size=(width, 10000),
            custom_flags=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--headless=new'
            ]
        )
        
        # 生成临时文件名
        temp_filename = os.path.basename(output_path)
        hti.screenshot(html_str=full_html, save_as=temp_filename)
        
        # 裁剪空白区域
        temp_path = os.path.join(temp_dir, temp_filename)
        self._crop_whitespace(temp_path, output_path, theme)
        
        # 清理中间临时文件
        if temp_path != output_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        
        logger.debug(f"转换完成: {output_path}")
    
    def _process_callouts(self, content):
        """处理 Obsidian callout 语法 > [!type] title"""
        lines = content.split('\n')
        result = []
        in_callout = False
        callout_content = []
        
        for line in lines:
            callout_match = re.match(r'^>\s*\[!(\w+)\]\s*(.*)?$', line)
            if callout_match:
                if in_callout:
                    result.append(self._render_callout(callout_content))
                in_callout = True
                callout_type = callout_match.group(1)
                callout_title = callout_match.group(2) or callout_type.capitalize()
                callout_content = [f'**{callout_title}**']
            elif in_callout and line.startswith('>'):
                callout_content.append(line[1:].strip())
            else:
                if in_callout:
                    result.append(self._render_callout(callout_content))
                    in_callout = False
                    callout_content = []
                result.append(line)
        
        if in_callout:
            result.append(self._render_callout(callout_content))
        
        return '\n'.join(result)
    
    def _render_callout(self, content):
        """渲染 callout 为 HTML"""
        return f'<div class="callout">{self._md_to_html(chr(10).join(content))}</div>'
    
    def _crop_whitespace(self, input_path, output_path, theme='light'):
        """裁剪图片底部空白区域"""
        try:
            img = Image.open(input_path)
        except FileNotFoundError:
            raise RuntimeError(
                f"截图文件未生成，请检查 Chromium 是否正确安装并可通过 CHROME_BIN 访问: {input_path}"
            )
        except Exception as e:
            raise RuntimeError(f"无法读取截图文件 {input_path}: {e}") from e

        try:
            # 根据主题确定背景色
            if theme == 'dark':
                bg_color = (30, 30, 30)  # #1e1e1e
            else:
                bg_color = (255, 255, 255)  # white

            # 转换为 RGB 模式
            if img.mode == 'RGBA':
                background = Image.new('RGB', img.size, bg_color)
                background.paste(img, mask=img.split()[3])
                img = background

            # 获取图片数据
            pixels = img.load()
            width, height = img.size

            # 从底部向上查找非空白行
            bottom = height
            for y in range(height - 1, -1, -1):
                row_is_blank = True
                for x in range(width):
                    pixel = pixels[x, y]
                    if isinstance(pixel, tuple):
                        if pixel[:3] != bg_color:
                            row_is_blank = False
                            break
                    else:
                        if pixel != bg_color[0]:
                            row_is_blank = False
                            break
                if not row_is_blank:
                    bottom = y + 40  # 添加一些底部边距
                    break

            # 裁剪图片
            cropped = img.crop((0, 0, width, min(bottom, height)))
            cropped.save(output_path, 'PNG')
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"图片裁剪处理失败: {e}") from e

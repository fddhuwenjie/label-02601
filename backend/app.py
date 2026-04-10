"""
Obsidian Markdown to Image Converter API
"""
import json
import logging
import os
import shutil
import tempfile
import uuid
import zipfile

from flask import Flask, request, jsonify, send_file
from converter import MarkdownToImageConverter

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
converter = MarkdownToImageConverter()

# 有效主题列表
VALID_THEMES = {'light', 'dark'}
# 宽度限制
MIN_WIDTH = 200
MAX_WIDTH = 4000


@app.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({'status': 'healthy', 'service': 'md2img'})


@app.route('/convert', methods=['POST'])
def convert_markdown():
    """
    将 Markdown 文本转换为图片
    
    Request Body:
        - markdown: Markdown 文本内容
        - width: 图片宽度 (可选, 默认 800, 范围 200-4000)
        - theme: 主题 light/dark (可选, 默认 light)
    
    Returns:
        PNG 图片文件
    """
    data = request.get_json()
    
    if not data or 'markdown' not in data:
        logger.warning("请求缺少 markdown 内容")
        return jsonify({'error': 'Missing markdown content', 'code': 'MISSING_CONTENT'}), 400
    
    markdown_content = data['markdown']
    width = data.get('width', 800)
    theme = data.get('theme', 'light')
    
    # 参数校验
    if not isinstance(width, int) or width < MIN_WIDTH or width > MAX_WIDTH:
        logger.warning(f"无效的宽度参数: {width}")
        return jsonify({
            'error': f'Width must be an integer between {MIN_WIDTH} and {MAX_WIDTH}',
            'code': 'INVALID_WIDTH'
        }), 400
    
    if theme not in VALID_THEMES:
        logger.warning(f"无效的主题参数: {theme}")
        return jsonify({
            'error': f'Theme must be one of: {", ".join(VALID_THEMES)}',
            'code': 'INVALID_THEME'
        }), 400
    
    output_path = None
    try:
        # 生成临时文件路径
        temp_dir = tempfile.gettempdir()
        output_path = os.path.join(temp_dir, f'{uuid.uuid4()}.png')
        
        logger.info(f"开始转换 Markdown, width={width}, theme={theme}")
        
        # 转换 Markdown 为图片
        converter.convert(markdown_content, output_path, width=width, theme=theme)
        
        logger.info(f"转换成功, 输出文件: {output_path}")
        
        response = send_file(
            output_path,
            mimetype='image/png',
            as_attachment=True,
            download_name='output.png'
        )
        
        # 注册响应后清理回调
        @response.call_on_close
        def cleanup():
            _cleanup_file(output_path)
        
        return response
    except Exception as e:
        logger.error(f"转换失败: {str(e)}", exc_info=True)
        _cleanup_file(output_path)
        return jsonify({'error': 'Conversion failed', 'detail': str(e), 'code': 'CONVERSION_ERROR'}), 500


@app.route('/convert/file', methods=['POST'])
def convert_file():
    """
    上传 Markdown 文件并转换为图片
    
    Form Data:
        - file: Markdown 文件
        - width: 图片宽度 (可选, 默认 800, 范围 200-4000)
        - theme: 主题 (可选, light/dark)
    
    Returns:
        PNG 图片文件
    """
    if 'file' not in request.files:
        logger.warning("请求缺少文件")
        return jsonify({'error': 'No file uploaded', 'code': 'NO_FILE'}), 400
    
    file = request.files['file']
    if file.filename == '':
        logger.warning("未选择文件")
        return jsonify({'error': 'No file selected', 'code': 'NO_FILE_SELECTED'}), 400
    
    width = request.form.get('width', 800, type=int)
    theme = request.form.get('theme', 'light')
    
    # 参数校验
    if width < MIN_WIDTH or width > MAX_WIDTH:
        logger.warning(f"无效的宽度参数: {width}")
        return jsonify({
            'error': f'Width must be between {MIN_WIDTH} and {MAX_WIDTH}',
            'code': 'INVALID_WIDTH'
        }), 400
    
    if theme not in VALID_THEMES:
        logger.warning(f"无效的主题参数: {theme}")
        return jsonify({
            'error': f'Theme must be one of: {", ".join(VALID_THEMES)}',
            'code': 'INVALID_THEME'
        }), 400
    
    output_path = None
    try:
        markdown_content = file.read().decode('utf-8')
        
        logger.info(f"开始转换文件: {file.filename}, width={width}, theme={theme}")
        
        temp_dir = tempfile.gettempdir()
        output_path = os.path.join(temp_dir, f'{uuid.uuid4()}.png')
        
        converter.convert(markdown_content, output_path, width=width, theme=theme)
        
        logger.info(f"文件转换成功: {file.filename}")
        
        response = send_file(
            output_path,
            mimetype='image/png',
            as_attachment=True,
            download_name='output.png'
        )
        
        @response.call_on_close
        def cleanup():
            _cleanup_file(output_path)
        
        return response
    except UnicodeDecodeError:
        logger.error(f"文件编码错误: {file.filename}")
        _cleanup_file(output_path)
        return jsonify({'error': 'File must be UTF-8 encoded', 'code': 'ENCODING_ERROR'}), 400
    except Exception as e:
        logger.error(f"文件转换失败: {str(e)}", exc_info=True)
        _cleanup_file(output_path)
        return jsonify({'error': 'Conversion failed', 'detail': str(e), 'code': 'CONVERSION_ERROR'}), 500


@app.route('/api/convert/batch', methods=['POST'])
def convert_batch():
    """
    批量转换 Markdown 页面为 PNG 图片并打包为 ZIP
    
    Request Body:
        - pages: 包含多个 Markdown 页面的数组，每个页面有 title 和 content 字段
        - width: 图片宽度 (可选, 默认 800, 范围 200-4000)
        - theme: 主题 light/dark (可选, 默认 light)
    
    Returns:
        ZIP 文件包含所有转换成功的 PNG 图片，以及 errors.json (如果有失败)
    """
    data = request.get_json()
    
    if not data or 'pages' not in data or not isinstance(data['pages'], list):
        logger.warning("请求缺少 pages 数组")
        return jsonify({'error': 'Missing pages array', 'code': 'MISSING_PAGES'}), 400
    
    pages = data['pages']
    width = data.get('width', 800)
    theme = data.get('theme', 'light')
    
    # 参数校验
    if not isinstance(width, int) or width < MIN_WIDTH or width > MAX_WIDTH:
        logger.warning(f"无效的宽度参数: {width}")
        return jsonify({
            'error': f'Width must be an integer between {MIN_WIDTH} and {MAX_WIDTH}',
            'code': 'INVALID_WIDTH'
        }), 400
    
    if theme not in VALID_THEMES:
        logger.warning(f"无效的主题参数: {theme}")
        return jsonify({
            'error': f'Theme must be one of: {", ".join(VALID_THEMES)}',
            'code': 'INVALID_THEME'
        }), 400
    
    temp_dir = None
    zip_path = None
    try:
        # 创建临时工作目录
        temp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(tempfile.gettempdir(), f'batch_{uuid.uuid4()}.zip')
        
        logger.info(f"开始批量转换, 共 {len(pages)} 个页面, width={width}, theme={theme}")
        
        errors = []
        successful_count = 0
        
        for page in pages:
            title = page.get('title', 'untitled')
            content = page.get('content', '')
            
            if not content:
                errors.append({
                    'title': title,
                    'error': 'Empty content',
                    'code': 'EMPTY_CONTENT'
                })
                logger.warning(f"页面 {title} 内容为空，跳过")
                continue
            
            try:
                # 确保文件名合法
                safe_title = "".join([c for c in title if c.isalnum() or c in (' ', '-', '_')]).rstrip()
                if not safe_title:
                    safe_title = f'page_{successful_count + 1}'
                
                png_path = os.path.join(temp_dir, f'{safe_title}.png')
                
                logger.info(f"转换页面: {title}")
                converter.convert(content, png_path, width=width, theme=theme)
                successful_count += 1
                
            except Exception as e:
                error_msg = str(e)
                errors.append({
                    'title': title,
                    'error': error_msg,
                    'code': 'CONVERSION_FAILED'
                })
                logger.error(f"页面 {title} 转换失败: {error_msg}")
        
        # 创建 ZIP 文件
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 添加所有成功转换的 PNG 文件
            for filename in os.listdir(temp_dir):
                if filename.endswith('.png'):
                    file_path = os.path.join(temp_dir, filename)
                    zipf.write(file_path, filename)
            
            # 如果有错误，添加 errors.json
            if errors:
                errors_json = json.dumps(errors, ensure_ascii=False, indent=2)
                zipf.writestr('errors.json', errors_json)
        
        logger.info(f"批量转换完成: 成功 {successful_count}/{len(pages)}, 失败 {len(errors)}")
        
        response = send_file(
            zip_path,
            mimetype='application/zip',
            as_attachment=True,
            download_name='batch_conversion.zip'
        )
        
        @response.call_on_close
        def cleanup():
            _cleanup_file(zip_path)
            _cleanup_dir(temp_dir)
        
        return response
        
    except Exception as e:
        logger.error(f"批量转换失败: {str(e)}", exc_info=True)
        _cleanup_file(zip_path)
        _cleanup_dir(temp_dir)
        return jsonify({'error': 'Batch conversion failed', 'detail': str(e), 'code': 'BATCH_CONVERSION_ERROR'}), 500


def _cleanup_file(filepath):
    """安全清理临时文件"""
    if filepath and os.path.exists(filepath):
        try:
            os.remove(filepath)
            logger.debug(f"已清理临时文件: {filepath}")
        except OSError as e:
            logger.warning(f"清理临时文件失败: {filepath}, 错误: {e}")


def _cleanup_dir(dirpath):
    """安全清理临时目录"""
    if dirpath and os.path.exists(dirpath):
        try:
            shutil.rmtree(dirpath)
            logger.debug(f"已清理临时目录: {dirpath}")
        except OSError as e:
            logger.warning(f"清理临时目录失败: {dirpath}, 错误: {e}")


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"启动服务, 端口: {port}")
    app.run(host='0.0.0.0', port=port, debug=False)

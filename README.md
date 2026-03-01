# Obsidian Markdown to Image Converter

将 Obsidian 风格的 Markdown 文件转换为 PNG 图片的 Python 服务。

## How to Run

### 一键启动 (推荐)

```bash
./run.sh
```

脚本会自动：
- 检测操作系统 (macOS / Linux / Windows Git Bash)
- 检查并提示安装 Docker (如未安装)
- 构建并启动服务
- 使用示例文件生成测试图片到 `output/` 目录

### Docker 手动启动

```bash
# 构建并启动服务
docker compose up --build -d

# 查看日志
docker compose logs -f

# 停止服务
docker compose down
```

### 本地启动

```bash
# 进入后端目录
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt

# 启动服务
python app.py
```

注意：本地运行需要安装 Chromium 浏览器，并通过环境变量 `CHROME_BIN` 指定其路径：

```bash
# macOS (Google Chrome)
export CHROME_BIN="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# macOS (Chromium via Homebrew)
export CHROME_BIN="/usr/local/bin/chromium"

# Linux
export CHROME_BIN="/usr/bin/chromium"  # 或 /usr/bin/chromium-browser
```

## Services

| 服务 | 端口 | 描述 |
|------|------|------|
| md2img | 5001 | Markdown 转图片 API |

## 测试账号

本项目为纯 API 服务，无需登录认证。

## 题目内容

使用 Python 将 Obsidian 的 Markdown 文件转图片。

### 功能特性

- 支持标准 Markdown 语法
- 支持 Obsidian 特有语法:
  - `==高亮文本==` 高亮显示
  - `[[双链]]` 和 `[[双链|显示文本]]` 内部链接
  - `![[嵌入]]` 嵌入引用（简化实现：渲染为 `📎 文件名` 占位提示，不读取实际文件内容）
  - `%%注释%%` 注释（不显示）
  - `> [!note] 标题` Callout 语法
- 支持代码高亮
- 支持表格
- 支持明暗主题切换
- 支持自定义图片宽度 (200-4000)
- 支持中文字体
- Docker 镜像支持 ARM64 和 AMD64 架构

### API 接口

#### 健康检查
```
GET /health
```

#### 文本转换
```
POST /convert
Content-Type: application/json

{
    "markdown": "# Hello World\n\nThis is **bold** text.",
    "width": 800,
    "theme": "light"
}
```

#### 文件上传转换
```
POST /convert/file
Content-Type: multipart/form-data

file: <markdown_file>
width: 800 (可选)
theme: light (可选)
```

### 使用示例

> **端口说明**：以下示例使用端口 `5001`，对应 Docker 启动方式（`docker-compose.yml` 中映射 `5001:5000`）。  
> 若使用**本地启动**（`python app.py`），请将端口改为 `5000`。

```bash
# 创建输出目录
mkdir -p output

# 使用示例文件测试 (Docker: 5001 / 本地: 5000)
curl -X POST http://localhost:5001/convert/file \
  -F "file=@examples/sample.md" \
  -F "theme=light" \
  --output output/output_light.png

# 深色主题
curl -X POST http://localhost:5001/convert/file \
  -F "file=@examples/sample.md" \
  -F "theme=dark" \
  --output output/output_dark.png

# 文本转换
curl -X POST http://localhost:5001/convert \
  -H "Content-Type: application/json" \
  -d '{"markdown": "# Hello\n\n- Item 1\n- Item 2"}' \
  --output output/output.png

# 自定义宽度
curl -X POST http://localhost:5001/convert/file \
  -F "file=@your_note.md" \
  -F "width=1200" \
  --output output/output.png
```


## 运行测试

```bash
cd backend

# 仅运行单元测试（无需 Chromium）
pytest tests/ -m "not integration"

# 运行全部测试，包括集成测试（需要 Chromium，参考"本地启动"配置 CHROME_BIN）
pytest tests/

# 查看详细输出
pytest tests/ -m "not integration" -v
```

> 集成测试（`test_convert_creates_image`）会调用 Chromium 进行真实截图，本地运行前请确保已按"本地启动"章节配置好 `CHROME_BIN` 环境变量。

#!/bin/bash

# Obsidian Markdown to Image Converter - 一键启动脚本
# 兼容 macOS / Linux / Windows (Git Bash / WSL)

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 检测操作系统
detect_os() {
    case "$(uname -s)" in
        Darwin*) OS="mac" ;;
        Linux*)  OS="linux" ;;
        MINGW*|MSYS*|CYGWIN*) OS="windows" ;;
        *) OS="unknown" ;;
    esac
    log_info "检测到操作系统: $OS"
}

# 检查并安装 Docker
check_docker() {
    if command -v docker &> /dev/null; then
        log_info "Docker 已安装: $(docker --version)"
        return 0
    fi

    log_warn "Docker 未安装，正在尝试安装..."
    
    case "$OS" in
        mac)
            if command -v brew &> /dev/null; then
                log_info "使用 Homebrew 安装 Docker..."
                brew install --cask docker
                log_warn "请手动启动 Docker Desktop 应用，然后重新运行此脚本"
                exit 1
            else
                log_error "请先安装 Homebrew: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
                log_error "或手动下载 Docker Desktop: https://www.docker.com/products/docker-desktop"
                exit 1
            fi
            ;;
        linux)
            if command -v apt-get &> /dev/null; then
                log_info "使用 apt 安装 Docker..."
                sudo apt-get update
                sudo apt-get install -y docker.io docker-compose-plugin
                sudo systemctl start docker
                sudo usermod -aG docker $USER
                log_warn "已添加当前用户到 docker 组，请重新登录后再运行此脚本"
                exit 1
            elif command -v yum &> /dev/null; then
                log_info "使用 yum 安装 Docker..."
                sudo yum install -y docker docker-compose-plugin
                sudo systemctl start docker
                sudo usermod -aG docker $USER
                log_warn "已添加当前用户到 docker 组，请重新登录后再运行此脚本"
                exit 1
            else
                log_error "请手动安装 Docker: https://docs.docker.com/engine/install/"
                exit 1
            fi
            ;;
        windows)
            log_error "Windows 请手动安装 Docker Desktop: https://www.docker.com/products/docker-desktop"
            log_error "安装后请确保 Docker Desktop 正在运行"
            exit 1
            ;;
        *)
            log_error "未知操作系统，请手动安装 Docker"
            exit 1
            ;;
    esac
}

# 检查 Docker 是否运行
check_docker_running() {
    if ! docker info &> /dev/null; then
        log_error "Docker 未运行，请启动 Docker Desktop 或 Docker 服务"
        case "$OS" in
            mac|windows) log_info "请启动 Docker Desktop 应用" ;;
            linux) log_info "尝试运行: sudo systemctl start docker" ;;
        esac
        exit 1
    fi
    log_info "Docker 服务运行中"
}

# 检查 curl
check_curl() {
    if ! command -v curl &> /dev/null; then
        log_warn "curl 未安装，正在安装..."
        case "$OS" in
            mac) brew install curl ;;
            linux) sudo apt-get install -y curl || sudo yum install -y curl ;;
            windows) log_error "请安装 curl 或使用 Git Bash" && exit 1 ;;
        esac
    fi
}

# 启动服务
start_service() {
    log_info "构建并启动服务..."
    
    # 检查 docker compose 命令格式
    if docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
    elif command -v docker-compose &> /dev/null; then
        COMPOSE_CMD="docker-compose"
    else
        log_error "docker compose 不可用"
        exit 1
    fi

    $COMPOSE_CMD down 2>/dev/null || true
    $COMPOSE_CMD up --build -d

    log_info "等待服务启动..."
    sleep 10

    # 等待健康检查
    for i in {1..30}; do
        if curl -s http://localhost:5001/health | grep -q "healthy"; then
            log_info "服务启动成功!"
            return 0
        fi
        sleep 2
    done

    log_error "服务启动超时"
    $COMPOSE_CMD logs
    exit 1
}

# 运行测试
run_test() {
    log_info "使用示例文件测试转换..."
    
    mkdir -p output

    # 浅色主题
    log_info "生成浅色主题图片..."
    curl -s -X POST http://localhost:5001/convert/file \
        -F "file=@examples/sample.md" \
        -F "theme=light" \
        --output output/result_light.png

    # 深色主题
    log_info "生成深色主题图片..."
    curl -s -X POST http://localhost:5001/convert/file \
        -F "file=@examples/sample.md" \
        -F "theme=dark" \
        --output output/result_dark.png

    # 验证输出
    if [ -f "output/result_light.png" ] && [ -s "output/result_light.png" ]; then
        log_info "✅ 浅色主题: output/result_light.png"
    else
        log_error "❌ 浅色主题生成失败"
    fi

    if [ -f "output/result_dark.png" ] && [ -s "output/result_dark.png" ]; then
        log_info "✅ 深色主题: output/result_dark.png"
    else
        log_error "❌ 深色主题生成失败"
    fi

    echo ""
    log_info "=========================================="
    log_info "测试完成! 输出文件在 output/ 目录"
    log_info "服务运行在 http://localhost:5001"
    log_info "停止服务: $COMPOSE_CMD down"
    log_info "=========================================="
}

# 主流程
main() {
    echo ""
    echo "======================================"
    echo " Obsidian Markdown to Image Converter"
    echo "======================================"
    echo ""

    detect_os
    check_docker
    check_docker_running
    check_curl
    start_service
    run_test
}

main

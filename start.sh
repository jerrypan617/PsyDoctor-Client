#!/bin/bash

# PsyDoctor-Client 一键启动脚本
# 自动检查端口占用，清除后启动后端和前端服务

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 端口配置
BACKEND_PORT=8001
FRONTEND_PORT=5173

# 项目路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  PsyDoctor-Client 一键启动脚本${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 函数：检查端口占用并清除
check_and_kill_port() {
    local port=$1
    local service_name=$2
    
    echo -e "${YELLOW}检查 ${service_name} 端口 ${port}...${NC}"
    
    # 查找占用端口的进程
    local pid=$(lsof -ti :$port 2>/dev/null || true)
    
    if [ -n "$pid" ]; then
        echo -e "${YELLOW}发现端口 ${port} 被占用 (PID: $pid)，正在清除...${NC}"
        kill -9 $pid 2>/dev/null || true
        sleep 1
        
        # 再次检查是否清除成功
        local new_pid=$(lsof -ti :$port 2>/dev/null || true)
        if [ -n "$new_pid" ]; then
            echo -e "${RED}❌ 无法清除端口 ${port}，请手动检查${NC}"
            exit 1
        else
            echo -e "${GREEN}✅ 端口 ${port} 已清除${NC}"
        fi
    else
        echo -e "${GREEN}✅ 端口 ${port} 未被占用${NC}"
    fi
}

# 函数：检查依赖
check_dependencies() {
    echo -e "${YELLOW}检查依赖...${NC}"
    
    # 检查Python
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}❌ 未找到 python3，请先安装 Python${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ Python 已安装${NC}"
    
    # 检查Node.js
    if ! command -v node &> /dev/null; then
        echo -e "${RED}❌ 未找到 node，请先安装 Node.js${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ Node.js 已安装${NC}"
    
    # 检查后端依赖
    if [ ! -d "$BACKEND_DIR" ]; then
        echo -e "${RED}❌ 后端目录不存在: $BACKEND_DIR${NC}"
        exit 1
    fi
    
    # 检查前端依赖
    if [ ! -d "$FRONTEND_DIR" ]; then
        echo -e "${RED}❌ 前端目录不存在: $FRONTEND_DIR${NC}"
        exit 1
    fi
    
    # 检查node_modules是否存在
    if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
        echo -e "${YELLOW}⚠️  前端依赖未安装，正在安装...${NC}"
        cd "$FRONTEND_DIR"
        npm install
        cd "$SCRIPT_DIR"
    fi
    
    echo ""
}

# 函数：启动后端
start_backend() {
    echo -e "${BLUE}启动后端服务 (端口 ${BACKEND_PORT})...${NC}"
    cd "$BACKEND_DIR"
    
    # 检查虚拟环境
    if [ -d "venv" ]; then
        echo -e "${YELLOW}激活虚拟环境...${NC}"
        source venv/bin/activate
    elif [ -d ".venv" ]; then
        echo -e "${YELLOW}激活虚拟环境...${NC}"
        source .venv/bin/activate
    fi
    
    # 启动后端（后台运行）
    nohup python3 main.py > ../backend.log 2>&1 &
    BACKEND_PID=$!
    
    # 等待后端启动
    echo -e "${YELLOW}等待后端启动...${NC}"
    sleep 3
    
    # 检查后端是否启动成功
    if ps -p $BACKEND_PID > /dev/null 2>&1; then
        echo -e "${GREEN}✅ 后端已启动 (PID: $BACKEND_PID)${NC}"
        echo -e "${GREEN}   日志文件: backend.log${NC}"
        echo -e "${GREEN}   访问地址: http://localhost:${BACKEND_PORT}${NC}"
    else
        echo -e "${RED}❌ 后端启动失败，请查看日志: backend.log${NC}"
        exit 1
    fi
    
    cd "$SCRIPT_DIR"
    echo ""
}

# 函数：启动前端
start_frontend() {
    echo -e "${BLUE}启动前端服务 (端口 ${FRONTEND_PORT})...${NC}"
    cd "$FRONTEND_DIR"
    
    # 启动前端（后台运行）
    nohup npm run dev > ../frontend.log 2>&1 &
    FRONTEND_PID=$!
    
    # 等待前端启动
    echo -e "${YELLOW}等待前端启动...${NC}"
    sleep 5
    
    # 检查前端是否启动成功
    if ps -p $FRONTEND_PID > /dev/null 2>&1; then
        echo -e "${GREEN}✅ 前端已启动 (PID: $FRONTEND_PID)${NC}"
        echo -e "${GREEN}   日志文件: frontend.log${NC}"
        echo -e "${GREEN}   访问地址: http://localhost:${FRONTEND_PORT}${NC}"
    else
        echo -e "${RED}❌ 前端启动失败，请查看日志: frontend.log${NC}"
        exit 1
    fi
    
    cd "$SCRIPT_DIR"
    echo ""
}

# 函数：保存PID到文件
save_pids() {
    echo "$BACKEND_PID" > .backend.pid
    echo "$FRONTEND_PID" > .frontend.pid
    echo -e "${GREEN}✅ 进程ID已保存到 .backend.pid 和 .frontend.pid${NC}"
}

# 函数：清理函数（Ctrl+C时调用）
cleanup() {
    echo ""
    echo -e "${YELLOW}正在停止服务...${NC}"
    
    if [ -f .backend.pid ]; then
        BACKEND_PID=$(cat .backend.pid)
        kill $BACKEND_PID 2>/dev/null || true
        rm .backend.pid
        echo -e "${GREEN}✅ 后端已停止${NC}"
    fi
    
    if [ -f .frontend.pid ]; then
        FRONTEND_PID=$(cat .frontend.pid)
        kill $FRONTEND_PID 2>/dev/null || true
        rm .frontend.pid
        echo -e "${GREEN}✅ 前端已停止${NC}"
    fi
    
    echo -e "${GREEN}✅ 所有服务已停止${NC}"
    exit 0
}

# 注册清理函数
trap cleanup SIGINT SIGTERM

# 主流程
main() {
    # 检查依赖
    check_dependencies
    
    # 检查并清除端口占用
    check_and_kill_port $BACKEND_PORT "后端"
    check_and_kill_port $FRONTEND_PORT "前端"
    echo ""
    
    # 启动服务
    start_backend
    start_frontend
    
    # 保存PID
    save_pids
    
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✅ 所有服务已启动成功！${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "${BLUE}访问地址:${NC}"
    echo -e "  前端: ${GREEN}http://localhost:${FRONTEND_PORT}${NC}"
    echo -e "  后端: ${GREEN}http://localhost:${BACKEND_PORT}${NC}"
    echo ""
    echo -e "${BLUE}日志文件:${NC}"
    echo -e "  后端: ${GREEN}backend.log${NC}"
    echo -e "  前端: ${GREEN}frontend.log${NC}"
    echo ""
    echo -e "${YELLOW}按 Ctrl+C 停止所有服务${NC}"
    echo ""
    
    # 保持脚本运行，等待用户中断
    wait
}

# 执行主函数
main


#!/bin/bash
# forge-scrm 部署通道（Mac 执行）
# 用法：./deploy/deploy.sh
# 功能：本地构建前端 → rsync dist + 后端源码到搬瓦工 → 迁移数据库 → 重启服务 → HTTPS 验证
# 目标机：45.78.70.160:2222
#
# ⚠️ 部署方式：以「本地工作区」为准（含 agent 未提交的改动），全部走 rsync，
#    不再依赖 git pull——因为给 agent 的红线禁止其 commit/push，本地永远领先 main。
set -euo pipefail

# ============ 配置 ============
PROJECT_DIR="/Users/liulongfei/个人文件/forge-scrm"
VPS_HOST="45.78.70.160"
VPS_PORT="2222"
SSH_KEY="$HOME/.ssh/id_ed25519"
REMOTE_USER="root"
REMOTE_DIR="/opt/forge-scrm"
SERVICE="forge-scrm-api"
DOMAIN="https://scrm.pmlophy.com"

if [ ! -f "$SSH_KEY" ]; then
  echo "SSH key 不存在: $SSH_KEY" >&2
  exit 1
fi
SSH_OPTS=(-i "$SSH_KEY" -p "$VPS_PORT" -o StrictHostKeyChecking=no)
REMOTE="$REMOTE_USER@$VPS_HOST"

echo "部署目标: $REMOTE:$VPS_PORT"
echo "远端目录: $REMOTE_DIR"
echo "SSH key: $SSH_KEY"

echo "===== 部署前检查工作区 ====="
cd "$PROJECT_DIR"
git status --short --branch

REMOTE_ENV_HASH_BEFORE="$(ssh "${SSH_OPTS[@]}" "$REMOTE" "if [ -f '$REMOTE_DIR/backend/.env' ]; then sha256sum '$REMOTE_DIR/backend/.env' | awk '{print \$1}'; else echo missing; fi")"

echo "===== [1/6] 本地构建前端 ====="
cd "$PROJECT_DIR/frontend"
npm run build

echo "===== [2/6] rsync 前端 dist → 新机 ====="
rsync -avz --delete -e "ssh -p $VPS_PORT -i $SSH_KEY" \
  dist/ "$REMOTE:$REMOTE_DIR/frontend/dist/"

echo "===== [3/6] rsync 后端源码 → 新机 ====="
# 以本地工作区为准（含未提交改动）；生产 .env、venv、data/ 和数据库文件不进入同步。
rsync -avz --delete \
  --exclude='.env' \
  --exclude='.venv' \
  --exclude='.venv*' \
  --exclude='**pycache**' \
  --exclude='__pycache__/' \
  --exclude='*.pyc' \
  --exclude='data/' \
  --exclude='*.db' \
  --exclude='.DS_Store' \
  -e "ssh -p $VPS_PORT -i $SSH_KEY" \
  "$PROJECT_DIR/backend/" "$REMOTE:$REMOTE_DIR/backend/"

REMOTE_ENV_HASH_AFTER="$(ssh "${SSH_OPTS[@]}" "$REMOTE" "if [ -f '$REMOTE_DIR/backend/.env' ]; then sha256sum '$REMOTE_DIR/backend/.env' | awk '{print \$1}'; else echo missing; fi")"
if [ "$REMOTE_ENV_HASH_BEFORE" != "$REMOTE_ENV_HASH_AFTER" ]; then
  echo "生产 .env 校验失败：同步前后 sha256 不一致，已停止部署。" >&2
  exit 1
fi
echo "生产 .env: 未被覆盖（sha256 未变化）"

echo "===== [4/6] 线上升级数据库（使用搬瓦工现有 venv） ====="
ssh "${SSH_OPTS[@]}" "$REMOTE" \
  "cd $REMOTE_DIR/backend && $REMOTE_DIR/backend/.venv/bin/python -m alembic upgrade head"

echo "===== [5/6] 重启后端 + nginx ====="
ssh "${SSH_OPTS[@]}" "$REMOTE" \
  "systemctl restart $SERVICE && systemctl restart nginx && systemctl is-active $SERVICE && systemctl is-active nginx"

echo "===== [6/6] HTTPS 线上验证 ====="
sleep 3
curl -sk -o /dev/null -w "首页: %{http_code}\n" "$DOMAIN/"
curl -sk -o /dev/null -w "登录接口: %{http_code}\n" -X POST "$DOMAIN/api/auth/login" \
  -H "Content-Type: application/json" -d '{}'

echo ""
echo "===== 部署完成 ====="

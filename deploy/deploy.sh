#!/bin/bash
# forge-scrm 部署通道（Mac 执行）
# 用法：./deploy/deploy.sh
# 功能：本地构建前端 → rsync dist + 后端源码到新机 → 重启后端 → 验证
# 目标机：154.29.158.2:2222（临时 POC 机，退租后改 VPS_HOST 换机）
#
# ⚠️ 部署方式：以「本地工作区」为准（含 agent 未提交的改动），全部走 rsync，
#    不再依赖 git pull——因为给 agent 的红线禁止其 commit/push，本地永远领先 main。
set -euo pipefail

# ============ 配置 ============
VPS_HOST="154.29.158.2"
VPS_PORT="2222"
SSH_KEY="$HOME/.ssh/id_ed25519_vps"   # Mac 私钥（指向新机）
REMOTE_DIR="/opt/forge-scrm"
SERVICE="forge-scrm-api"
DOMAIN="http://scrm.pmlophy.com"

# 若 Mac 用的是 id_ed25519_vps，自动探测
[ -f "$SSH_KEY" ] || SSH_KEY="$HOME/.ssh/id_ed25519"
SSH_OPTS=(-i "$SSH_KEY" -p "$VPS_PORT" -o StrictHostKeyChecking=no)

echo "===== [1/6] 本地构建前端 ====="
cd "$(dirname "$0")/../frontend"
npm run build 2>&1 | tail -4

echo "===== [2/6] rsync 前端 dist → 新机 ====="
rsync -avz -e "ssh -i $SSH_KEY -p $VPS_PORT" \
  dist/ "root@$VPS_HOST:$REMOTE_DIR/frontend/dist/" 2>&1 | tail -3

echo "===== [3/6] rsync 后端源码 → 新机 ====="
# 以本地工作区为准（含未提交改动），排除虚拟环境/缓存/数据/DS_Store
rsync -avz -e "ssh -i $SSH_KEY -p $VPS_PORT" --delete \
  --exclude='__pycache__' --exclude='*.pyc' --exclude='.venv' \
  --exclude='venv' --exclude='data/' --exclude='.DS_Store' --exclude='*.db' \
  ../backend/ "root@$VPS_HOST:$REMOTE_DIR/backend/" 2>&1 | tail -3

echo "===== [4/6] 重启后端 + 刷新 nginx ====="
ssh "${SSH_OPTS[@]}" "root@$VPS_HOST" "
  # 若本地改了 requirements.txt，则安装新依赖（幂等）
  cd $REMOTE_DIR && if [ -f backend/requirements.txt ]; then
    diff <(cat backend/requirements.txt 2>/dev/null) <(cat $REMOTE_DIR/backend/requirements.txt 2>/dev/null) >/dev/null 2>&1 \
      || pip install -r backend/requirements.txt -q 2>/dev/null || true
  fi
  systemctl restart $SERVICE 2>&1 | tail -1 || true
  systemctl reload nginx 2>/dev/null || systemctl restart nginx
  echo '服务状态:'
  systemctl is-active $SERVICE mysql nginx
"

echo "===== [5/6] 线上升级数据库（仅在需要时） ====="
ssh "${SSH_OPTS[@]}" "root@$VPS_HOST" "
  cd $REMOTE_DIR/backend && (alembic upgrade head 2>/dev/null || echo 'alembic 跳过（无迁移或未配置）')
"

echo "===== [6/6] 线上验证 ====="
sleep 3
echo "首页: $(curl -s -o /dev/null -w '%{http_code}' -m 10 $DOMAIN/)"
echo "title: $(curl -s -m 10 $DOMAIN/ | grep -o '<title>[^<]*</title>' | head -1)"
echo "API:  $(curl -s -o /dev/null -w '%{http_code}' -m 10 -X POST $DOMAIN/api/auth/login -H 'Content-Type: application/json' -d '{}')（登录接口探测，422=可达，404=未通）"

echo ""
echo "===== 部署完成 ====="
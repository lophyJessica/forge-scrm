#!/bin/bash
# forge-scrm 部署通道（Mac 执行）
# 用法：./deploy/deploy.sh
# 功能：本地构建前端 → 推到新机 → 新机 git pull + 同步构建产物 → 重启后端 → 验证
# 目标机：154.29.158.2:2222（临时 POC 机，退租后改 VPS_HOST 换机）
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

echo "===== [1/5] 本地构建前端 ====="
cd "$(dirname "$0")/../frontend"
npm run build 2>&1 | tail -4

echo ""
echo "===== [2/5] 同步 dist 到新机 ====="
rsync -avz -e "ssh -i $SSH_KEY -p $VPS_PORT" \
  dist/ "root@$VPS_HOST:$REMOTE_DIR/frontend/dist/" 2>&1 | tail -3

echo ""
echo "===== [3/5] 新机 git pull（代码同步） ====="
ssh "${SSH_OPTS[@]}" "root@$VPS_HOST" "cd $REMOTE_DIR && git pull origin main 2>&1 | tail -2"

echo ""
echo "===== [4/5] 重启后端 + 刷新 nginx ====="
ssh "${SSH_OPTS[@]}" "root@$VPS_HOST" "
  systemctl restart $SERVICE 2>&1 | tail -1 || true
  systemctl reload nginx 2>/dev/null || systemctl restart nginx
  echo '服务状态:'
  systemctl is-active $SERVICE mysql nginx
"

echo ""
echo "===== [5/5] 线上验证 ====="
sleep 3
echo "首页: $(curl -s -o /dev/null -w '%{http_code}' -m 10 $DOMAIN/)"
echo "title: $(curl -s -m 10 $DOMAIN/ | grep -o '<title>[^<]*</title>' | head -1)"
echo "API:  $(curl -s -o /dev/null -w '%{http_code}' -m 10 -X POST $DOMAIN/api/auth/login -H 'Content-Type: application/json' -d '{}')（登录接口探测，422=可达，404=未通）"

echo ""
echo "===== 部署完成 ====="
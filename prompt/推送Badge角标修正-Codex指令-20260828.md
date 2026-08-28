cd ~/个人文件/forge-scrm && git pull origin main

```plaintext
Context:
项目 forge-scrm（Forge 新媒体运营系统），Mac ~/个人文件/forge-scrm，main 分支。用户拍板的小修正：推送任务按钮的 Badge 角标在无待办时不应显示 0。
现状：frontend/src/pages/reports/ReportDetail.tsx 约154行 <Badge count={pendingPushCount} showZero size="small">——showZero 导致无待办时显示红点 0，视觉噪音。

Request:
1. 删除 showZero 属性：改为 <Badge count={pendingPushCount} size="small">——0 时角标自动隐藏，有待办才显示数字。
2. 仅此一处改动，不动其他任何文件。

Output format:
- 单行修改。完成后 npm run build 通过。
- 自检报告 check-reports/推送Badge角标修正-自检报告-20260828.md（两行说明即可：改动点+build结果）。

红线禁止:
- 禁止不执行 git pull 就改文件。
- 禁止 commit/push/deploy。
- 禁止伪造构建结果。

Checkpoint:
完成后必须执行 AI 自检报告管道上传（沙箱 DNS 不解析 pmlophy.com 时按兜底规则：保存 check-reports/ + 如实汇报"未上传管道"，禁止重试超过1次）：
curl --noproxy '*' -X POST "https://pmlophy.com/p/jarvis/file/upload" -H "X-Jarvis-User: ai-reports" -F "file=@check-reports/推送Badge角标修正-自检报告-20260828.md"
最后汇报：改动文件、build 结果、报告文件名与字节数、是否已上传管道。
```

# 前端 UI 标准

本文件是 Forge SCRM 前端 UI 规范的唯一维护处。新增页面、调整样式和评审前端改动时均以本文件为准；`AGENTS.md` 只保留入口指针，不复制正文。

## 1. 视觉 Token

- 全站颜色、圆角和组件主题以 `src/theme.ts` 为唯一来源，页面不得自行建立平行色板。
- 状态标签必须调用 `statusTagColor(status)`，不得在页面内重复维护状态到颜色的映射。
- 主色、链接色和信息色使用主题配置，不在业务页面硬编码品牌色。

## 2. 间距

采用 8px 栅格，使用以下五档间距：

| 档位 | 数值 | 典型用途 |
|---|---:|---|
| XS | 4px | 图标与短文本、紧凑标签 |
| S | 8px | 行内控件、操作按钮间距 |
| M | 16px | 表单项分组、卡片内部区块、页面纵向间距 |
| L | 24px | 页面主区块、卡片内边距 |
| XL | 32px | 大区块分隔 |

页面内避免 6px、12px、18px 等游离值；确有组件适配需要时，应在代码中说明原因。

## 3. 容器尺寸

- Drawer 只使用三档宽度：480px（任务/简要详情）、640px（复杂表单）、720px（高信息密度详情）。
- Modal 只使用两档宽度：520px（常规表单/确认）、720px（复杂表单/对比内容）。
- 表单主体默认 `width: 100%`，需要限制阅读宽度时由稳定外层容器设置 `maxWidth`。
- 固定尺寸组件须同时具备响应式约束，避免窄屏溢出。

## 4. 按钮层级

- 每个视图最多一个主要操作使用 `type="primary"`。
- 表格操作列和列表行内操作禁止使用 `primary`，使用 `link` 或普通按钮。
- 操作列按钮统一 `size="small"`。
- `danger` 仅用于删除、废弃、淘汰、驳回等不可逆或高风险操作，并配合确认交互。
- 同一操作区域按“主要操作 → 次要操作 → 危险操作”排序。

## 5. 状态与反馈

- 状态展示统一使用 `Tag` 和 `statusTagColor`；处理中状态可配合 `Spin` 或 loading。
- 成功操作使用 `message.success`，可恢复的业务失败由接口错误或 `message.error` 明确说明。
- 删除、废弃、驳回、淘汰等危险操作必须使用 `Modal.confirm` 或 `Popconfirm`。
- 异步操作期间禁用冲突按钮并显示 loading，完成后刷新当前数据。

## 6. 空态

- 所有 `Table` 必须设置 `locale.emptyText`，默认使用 `src/components/tableEmpty.ts` 的 `TABLE_EMPTY`。
- 业务场景有明确下一步时可以覆盖默认文案，例如“暂无结果，请先执行任务”。
- `List`、详情区块和搜索结果也应提供可理解的空态，不留空白区域。
- 筛选列表的默认空态应提示用户可调整筛选条件。

## 7. 页面骨架

列表页建议骨架：

```tsx
<Card title="页面标题" extra={<Button type="primary">主要操作</Button>}>
  <Form layout="inline" style={{ marginBottom: 16 }}>{/* 筛选区 */}</Form>
  <Table locale={TABLE_EMPTY} />
</Card>
```

详情页建议骨架：

```tsx
<Space direction="vertical" size={16} style={{ display: 'flex' }}>
  <Card title="详情标题" extra={<Button>返回列表</Button>}>
    {/* 基础信息与主要操作 */}
  </Card>
  {/* 独立内容区块，不嵌套装饰性卡片 */}
</Space>
```

表单页建议骨架：

```tsx
<Card title="表单标题">
  <div style={{ width: '100%', maxWidth: 720 }}>
    <Form layout="vertical">{/* 表单字段 */}</Form>
  </div>
</Card>
```

## 8. 自检清单

- 颜色是否来自 `theme.ts`，状态色是否只走 `statusTagColor`。
- 间距是否落在 4/8/16/24/32px 五档。
- Drawer、Modal 是否使用规定档位。
- 当前视图是否只有一个主要按钮，行内操作是否无 `primary`。
- 危险操作是否有确认，操作列按钮是否为小尺寸。
- 每个 Table 是否设置空态，异步流程是否有 loading、成功和失败反馈。

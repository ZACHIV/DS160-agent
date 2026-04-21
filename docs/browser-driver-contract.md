# Browser Driver Contract

当前项目已经形成四层浏览器执行结构：

1. `mapping`
2. `plan`
3. `browser-plan`
4. `runtime-plan`
5. `driver-manifest` / `agent-browser-script`

## Layer responsibilities

### `mapping`
- 负责把 dossier 字段映射到 DS-160 `field_id`
- 输出 `ready / needs_review / blocked`

### `plan`
- 负责把字段状态转成动作类型
- 输出 `fill / review / block`

### `browser-plan`
- 负责把动作分配到 DS-160 页面
- 输出页面批次和保存检查点

### `runtime-plan`
- 负责把页面批次和 locator 绑定
- 输出：
  - `open_page`
  - `snapshot_before`
  - `fill_instructions`
  - `review_instructions`
  - `blocked_instructions`
  - `save_checkpoint`
  - `page_stops`

### `driver-manifest`
- 负责把 runtime plan 编译成 driver 可消费的命令清单
- 每条命令明确：
  - `tool`
  - `operation`
  - `page_id`
  - `executable`
  - `command`
  - `notes`

## Truthfulness rule

如果某类字段目前没有可靠的自动操作绑定，manifest 必须：
- 保留字段
- 标记为 `executable: false`
- 生成解释性命令或注释

当前 prototype 中：
- `text` / `date` 可以生成可执行 `agent-browser find label ... fill ...`
- `select` / `radio` 还没有被伪装成已自动化，只会输出占位说明

## Next implementation target

要让 driver 真正可运行到更高覆盖率，下一步只需要补这两类：
- `select_by_label`
- `radio_by_label`

补完之后，driver 层就能把更多 `ready` 字段直接变成真实命令，而不需要改动上游 mapping / planner / runtime 结构。

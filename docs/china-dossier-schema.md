# China Dossier Schema

当前原型使用一个单一 dossier JSON 作为输入，目标是先让中国申请人的 DS-160 关键信息结构化，再逐步扩展字段覆盖率。

## Top-level shape

```json
{
  "case_id": "CN-B1B2-001",
  "identity": {},
  "travel_plan": {},
  "employment_education": {},
  "family_contacts": {},
  "security_background": {},
  "evidence_catalog": []
}
```

## Sections

### `identity`
- 护照英文姓
- 护照英文名
- 中文姓名
- 性别
- 婚姻状态
- 出生日期
- 出生城市 / 省份 / 国家
- 国籍
- 护照号
- 护照签发国
- 护照签发日期
- 护照失效日期
- `source_ids`

### `travel_plan`
- 签证类别
- 出行目的备注
- 预计到达日期
- 停留时长值和单位
- 付款人
- 美国联系人姓名 / 机构 / 电话 / 邮箱
- `source_ids`

### `employment_education`
- 主要职业
- 当前单位名称
- 当前单位地址
- 月收入
- 学校名称
- `source_ids`

### `family_contacts`
- 父亲姓名
- 母亲姓名
- 配偶姓名
- 美国亲属姓名 / 身份
- `source_ids`

### `security_background`
- `yes_no_answers`
- `explanations`
- `source_ids`

### `evidence_catalog`
每条证据包含：
- `id`
- `kind`
- `description`

## Design rules
- 一个字段可以为空，但不能被静默猜测。
- 每个 section 都必须携带 `source_ids`，用于映射时生成证据链。
- 对中国申请人常见中文资料，先保留原始来源，再在 mapper 中做英文/DS-160 兼容转换。

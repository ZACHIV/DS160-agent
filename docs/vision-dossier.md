# Vision Dossier Collection

图片采集端和填表执行器继续保持分离：

- `app/intake.html` 负责上传图片、粘贴外部模型结果、手动补齐，并生成 full dossier JSON
- `app/ds160-assistant.html` 只导入 full dossier JSON

## 图片整理方式

当前仍然是半手动流程：

1. 用户在采集页选择图片
2. 前端一键复制提示词
3. 用户去外部视觉大模型中上传同样的图片并运行
4. 用户把模型返回的 dossier JSON 粘贴回采集页
5. 后端按 dossier schema 做最终校验、缺失字段计算和错误提示

## 上传材料建议

当前仍然建议上传 6 类材料，每类 1 张：

1. `passport_bio`
2. `trip_proof`
3. `us_contact_proof`
4. `employment_proof`
5. `family_info_sheet`
6. `security_questionnaire`

## 输出要求

- 大模型返回值必须直接满足 `docs/dossier.schema.json`
- 禁止返回中间版平铺字段
- `source_ids` 和 `evidence_catalog` 必须一并返回

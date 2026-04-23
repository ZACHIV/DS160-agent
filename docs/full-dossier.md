# Full Dossier Contract

当前项目的数据采集端、视觉识别结果、执行页导入，统一只接受一份完整的 dossier JSON。

机器可校验版本见：
- [docs/dossier.schema.json](/home/zhangzheng/0_platform/personal/idea/amercican_visa/docs/dossier.schema.json)

可直接复用的示例见：
- [sample_data/china_b1b2_sample.json](/home/zhangzheng/0_platform/personal/idea/amercican_visa/sample_data/china_b1b2_sample.json)
- [sample_data/china_b1b2_fake_test.json](/home/zhangzheng/0_platform/personal/idea/amercican_visa/sample_data/china_b1b2_fake_test.json)

## 设计边界

- 不再保留中间输入格式到 dossier 的转换层
- 采集页必须在采集阶段就补齐 dossier 结构
- 执行页只导入 full dossier JSON
- 图片识别返回值也必须直接满足 dossier schema

## 重点字段

- `identity.birth_province`
- `travel_plan.purpose_notes`
- `employment_education.monthly_income_local`
- `family_contacts.us_relative_name`
- `security_background.explanations`
- `evidence_catalog`

这些字段不能再依赖后处理补默认值或置空策略。

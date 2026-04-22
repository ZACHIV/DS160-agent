# Intake JSON V1

这是当前项目统一使用的最小输入 JSON 契约，用于：

- `app/intake.html` 采集页输出
- `app/ds160-assistant.html` 执行页导入
- `intake -> dossier` 转换的唯一输入

机器可校验版本见：
- [docs/intake-v1.schema.json](/home/zhangzheng/0_platform/personal/idea/amercican_visa/docs/intake-v1.schema.json)

可直接复用的示例见：
- [sample_data/intake_v1_sample.json](/home/zhangzheng/0_platform/personal/idea/amercican_visa/sample_data/intake_v1_sample.json)

## 设计边界

- 用户输入和美签填写已经拆成两个独立功能
- 中间通信只允许这一份 `intake-v1` JSON
- 采集页不直接调用填表服务
- 执行页不直接采集用户字段，只接收 JSON 文档

- 当前只服务中国申请人的 `B1/B2`
- `visa_class` 不再作为用户输入，后端固定为 `B1/B2`
- `nationality` / `birth_country` / `passport_issuance_country` 不再作为用户输入，后端固定为 `CHINA`
- 当前只保留两个安全问题：
  - `communicable_disease`
  - `arrest_history`
- `passport_book_number` 不作为 intake 输入，继续走 review 策略

## 必填字段

```json
[
  "surname",
  "given_names",
  "sex",
  "marital_status",
  "date_of_birth",
  "birth_city",
  "passport_number",
  "passport_issue_date",
  "passport_expiration_date",
  "trip_purpose",
  "intended_arrival_date",
  "intended_length_of_stay_value",
  "intended_length_of_stay_unit",
  "payer_name",
  "us_contact_name",
  "us_contact_phone",
  "us_contact_address_line1",
  "us_contact_city",
  "us_contact_state",
  "us_contact_postal_code",
  "primary_occupation",
  "current_employer_name",
  "current_employer_address",
  "father_full_name",
  "mother_full_name",
  "communicable_disease",
  "arrest_history"
]
```

## 可选字段

```json
[
  "native_full_name",
  "us_contact_organization",
  "us_contact_email",
  "spouse_full_name"
]
```

## 当前统一格式

```json
{
  "surname": "ZHANG",
  "given_names": "WEI",
  "native_full_name": "张伟",
  "sex": "MALE",
  "marital_status": "MARRIED",
  "date_of_birth": "1990-08-15",
  "birth_city": "Shanghai",
  "passport_number": "E12345678",
  "passport_issue_date": "2023-05-12",
  "passport_expiration_date": "2033-05-11",
  "trip_purpose": "business_tourism",
  "intended_arrival_date": "2026-09-10",
  "intended_length_of_stay_value": "12",
  "intended_length_of_stay_unit": "DAYS",
  "payer_name": "Shanghai Example Trading Co., Ltd.",
  "us_contact_name": "Michael Chen",
  "us_contact_organization": "Example US Imports",
  "us_contact_phone": "+1 415 555 0187",
  "us_contact_address_line1": "500 Market Street",
  "us_contact_city": "San Francisco",
  "us_contact_state": "California",
  "us_contact_postal_code": "94105",
  "us_contact_email": "mchen@example.com",
  "primary_occupation": "BUSINESSPERSON",
  "current_employer_name": "Shanghai Example Trading Co., Ltd.",
  "current_employer_address": "88 Huaihai Middle Road, Shanghai, China",
  "father_full_name": "ZHANG JIANGUO",
  "mother_full_name": "LI HUA",
  "spouse_full_name": "WANG LI",
  "communicable_disease": false,
  "arrest_history": false
}
```

## 枚举约束

- `sex`
  - `MALE`
  - `FEMALE`
- `marital_status`
  - `SINGLE`
  - `MARRIED`
  - `DIVORCED`
  - `WIDOWED`
- `trip_purpose`
  - `business_tourism`
  - `business`
  - `tourism`
  - `family_visit`
- `intended_length_of_stay_unit`
  - `DAYS`
  - `WEEKS`
  - `MONTHS`
- `primary_occupation`
  - `BUSINESSPERSON`
  - `STUDENT`
  - `OTHER`

## 后续收敛建议

- 如果后面要支持更多签证类型，不要在这个 V1 契约上直接加分支；应升级到 `intake-v2`
- 如果后面要支持更多图片材料来源，建议新增 `sources` 节点，而不是把文件信息混进当前平铺字段
- 如果后面要把 intake 文档落盘，直接保存这份 JSON；不要让采集页和执行页各自维护不同格式

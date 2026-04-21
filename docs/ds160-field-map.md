# DS-160 Field Map Prototype

这是当前原型已实现的字段映射，不是全量 DS-160 覆盖。

## Identity
- `identity.surname`
- `identity.given_names`
- `identity.native_full_name`
- `identity.sex`
- `identity.marital_status`
- `identity.date_of_birth`
- `identity.birth_city`
- `identity.birth_country`
- `identity.nationality`

## Passport
- `passport.number`
- `passport.issue_date`
- `passport.expiration_date`

## Travel
- `travel.purpose_of_trip`
- `travel.intended_arrival_date`
- `travel.intended_length_of_stay`
- `travel.payer_name`
- `travel.us_contact_name`
- `travel.us_contact_phone`

## Employment
- `employment.primary_occupation`
- `employment.current_employer_name`

## Family
- `family.father_full_name`
- `family.mother_full_name`

## Security
- `security.communicable_disease`
- `security.arrest_history`

## Status model
- `ready`
  - 字段可直接用于 DS-160 草稿
- `needs_review`
  - 有候选值，但需要人工确认
- `blocked`
  - 缺关键值，不能安全继续

## Current heuristics
- `B1/B2` 目的默认进入 `needs_review`
  - 原因：商务/旅游混合用途通常要在最终提交前再次确认
- 缺失美国联系人电话时进入 `blocked`
- security 问题如果为 `yes` 且缺解释，进入 `needs_review`

## Next expansion targets
- 地址与电话完整格式化
- 护照签发地
- 过去赴美记录
- 社交媒体与联系方式
- 配偶 / 子女 / 美国亲属更细粒度字段

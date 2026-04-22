# OCR Intake V1

OCR 采集端和填表执行器仍然保持彻底分离：

- `app/intake.html` 负责告诉用户上传哪些图片，并生成 `intake-v1` JSON
- `app/ds160-assistant.html` 只导入这份 JSON，不直接采集字段

## 用户需要上传的文件

当前 V1 需要 6 类图片，每类 1 张：

1. `passport_bio`
   护照资料页清晰照片或扫描件
2. `trip_proof`
   行程单、邀请函，或一张写有 `Trip Purpose / Arrival Date / Length of Stay / Payer` 的截图
3. `us_contact_proof`
   联系人名片、邀请函页，或一张写有 `Contact Name / Phone / Address / City / State / Postal Code / Email` 的截图
4. `employment_proof`
   在职证明、工作名片、学校证明，或一张写有 `Occupation / Employer / Employer Address` 的截图
5. `family_info_sheet`
   户口本相关页、结婚证补充页，或一张写有 `Father / Mother / Spouse / Marital Status` 的截图
6. `security_questionnaire`
   一张写有 `Communicable Disease` 和 `Arrest History` 对应 `Yes/No` 的截图或照片

## 设计原则

- 正式文件优先；如果正式文件不含完整字段，可以上传一张“带标签的整理截图”
- OCR 结果只用于生成 `intake-v1` JSON，不直接触发填表
- OCR 未识别完整时，不会导出最终 JSON，而是返回缺失字段清单

## 外部 OCR 接口

当前后端默认接入 `OCR.space`：

- 文档页：https://ocr.space/ocrapi
- 环境变量：`OCR_SPACE_API_KEY`
- 默认值：`helloworld`

`helloworld` 仅适合调通链路。要稳定使用，建议用户申请自己的免费 key。

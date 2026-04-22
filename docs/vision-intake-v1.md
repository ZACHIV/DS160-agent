# Vision Intake V1

图片采集端和填表执行器继续保持分离：

- `app/intake.html` 负责让用户上传图片或手动填写，并生成 `intake-v1` JSON
- `app/ds160-assistant.html` 只导入这份 JSON，不直接采集字段

## 图片整理方式

当前不再使用 OCR 规则解析。

当前阶段改为半手动流程：

- 用户在采集页选择图片
- 前端一键复制提示词
- 用户自己去外部视觉大模型中上传同样的图片并运行
- 用户把模型返回的 JSON 粘贴回采集页
- 后端再按 schema 做最终校验、缺失字段计算和错误提示

## 用户需要上传的图片

当前 V1 仍然建议上传 6 类图片，每类 1 张：

1. `passport_bio`
   护照资料页
2. `trip_proof`
   赴美行程或邀请材料
3. `us_contact_proof`
   美国联系人材料
4. `employment_proof`
   工作或学校材料
5. `family_info_sheet`
   家庭信息材料
6. `security_questionnaire`
   安全背景问卷

## 外部模型接口

当前后端仍然保留 OpenAI 兼容的 Chat Completions 视觉接口调用方法，但前端暂时不直接触发它。

环境变量：

- `VISION_MODEL_API_KEY`
- `VISION_MODEL_NAME`
- `VISION_MODEL_BASE_URL`

后端会把：
- 图片列表
- `docs/intake-v1.schema.json`
- “只返回目标 JSON 结构”的系统提示

拼成可复制的提示词或请求体约束。

## 设计原则

- 大模型只负责看图并返回结构化结果
- 后端负责最终 schema 校验
- 缺失字段和格式错误仍然会回到手填表单中高亮

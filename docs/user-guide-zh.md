# 中国申请人 DS-160 自动化使用说明

本文档面向实际使用者，不讲实现细节，重点说明：
- 官方网址是什么
- 现在这套脚本能做到什么
- 调用大模型前，人必须准备什么
- `captcha` 是什么，为什么仍然需要人工参与

## 1. 官方网址

当前项目只覆盖 **中国申请人的 DS-160**，不覆盖预约排期。

### 核心网址
- DS-160 说明页（国务院官方介绍）  
  https://travel.state.gov/content/travel/en/us-visas/visa-information-resources/forms/ds-160-online-nonimmigrant-visa-application.html

- DS-160 FAQ（国务院官方 FAQ）  
  https://travel.state.gov/content/travel/en/us-visas/visa-information-resources/forms/ds-160-online-nonimmigrant-visa-application/ds-160-faqs.amp.html/

- DS-160 真实填写入口（CEAC 官方网页）  
  https://ceac.state.gov/genniv/

- 美国签证总入口（国务院官方签证栏目）  
  https://travel.state.gov/content/travel/en/us-visas.html

### 当前与中国申请人直接相关的申请地点
在 CEAC 首页里，脚本已经验证能自动选择以下中国馆点之一：
- `CHINA, BEIJING`
- `CHINA, GUANGZHOU`
- `CHINA, SHANGHAI`
- `CHINA, SHENYANG`
- `CHINA, WUHAN`

当前代码默认用：
- `CHINA, SHANGHAI`

## 2. 现在这套脚本已经能做什么

### 已经能自动完成的部分
- 打开真实 DS-160 官网首页
- 自动选择中国申请地点
- 读取真实首页状态
- 判断首页是否已经填了 captcha
- 在 captcha 未填时安全停止
- 在你填完 captcha 后，具备继续点击 `START AN APPLICATION` 的恢复入口

### 已经能自动生成但还没完整接到真实表单页的部分
- 根据 dossier 生成 DS-160 字段映射
- 给字段标记：
  - `ready`
  - `needs_review`
  - `blocked`
- 生成按页面分组的填表计划
- 生成 driver manifest 和 `agent-browser` 草稿脚本

### 还没有彻底做完的部分
- 正式 DS-160 表单页的 live locator 全量绑定
- 所有下拉框 / 单选项的真实自动操作
- 从第一页一路自动填到最后一页
- 最终签名提交

具体说明如下：

#### 1. 正式 DS-160 表单页的 live locator 全量绑定
现在已经在真实网站上验证过的是：
- DS-160 首页
- 申请地点下拉框
- captcha 输入框
- `START AN APPLICATION`
- `RETRIEVE AN APPLICATION`

但真正进入 DS-160 正式表单页之后，还没有把每一页的真实字段都逐个绑定完成。

这意味着当前还缺：
- 每一页真实输入框、下拉框、单选框、按钮的稳定 selector
- 翻页后重新定位元素的逻辑
- 保存按钮 / 下一页按钮 / 返回按钮的真实绑定

简单说：
- **首页已经是真实自动化**
- **正式表单页还没有做到全量真实定位**

#### 2. 所有下拉框 / 单选项的真实自动操作
当前项目已经区分出了哪些字段是：
- 文本输入
- 日期输入
- 下拉选择
- 单选 yes/no

其中：
- `text` / `date` 这类字段，已经能生成比较接近真实执行的命令
- `select` / `radio` 这类字段，当前还主要停留在“已识别、已规划、但没有全部绑定成真实点击/选择动作”

为什么这一步还没完全打通：
- DS-160 的下拉和单选，在真实页面里常常依赖具体 option 值、JS 事件或特殊控件行为
- 不能只靠“看起来像字段名”就假设一定能自动选中
- 必须一页页在真实网页上确认

所以现在的状态不是“不会处理”，而是：
- **已经知道哪些字段需要 select/radio**
- **但还没有把所有 select/radio 在真实站点上逐个验证完**

#### 3. 从第一页一路自动填到最后一页
当前系统已经打通了：
- dossier -> mapping
- mapping -> plan
- plan -> browser-plan
- browser-plan -> runtime-plan
- runtime-plan -> driver-manifest / agent-browser-script

也就是说：
- “填什么”
- “按哪一页填”
- “哪些地方要人工复核”
- “哪些地方要停住”

这些都已经有结构化输出了。

但还没有完成的是：
- 真正从第 1 页开始一路执行到最后一页的 live workflow
- 每页填完以后自动保存
- 页面刷新 / 超时 / 翻页失败后的恢复逻辑
- 某页缺字段时的暂停再恢复

所以目前更准确的说法是：
- **自动化骨架已经贯通**
- **真正的全流程 live runner 还没有完成**

#### 4. 最终签名提交
这是最需要谨慎的部分。

根据官方规则：
- 申请人通常必须自己点击 `Sign Application`
- 就算别人协助填写，申请人本人仍然要对内容负责

所以当前项目不会把“最终签名提交”直接定义成默认全自动。

这一步没有做完，既有技术原因，也有流程原因：

技术原因：
- 最终提交前通常会遇到额外检查和页面跳转
- 可能出现 captcha、确认页、照片相关问题

流程原因：
- 申请人必须对最终内容负责
- 如果模型或脚本填错，最终风险不应该被静默提交

因此当前推荐策略是：
- 自动完成前面尽可能多的内容
- 到最终签名页时强制停住
- 由人工审核后再决定是否继续提交

#### 5. 对使用者来说，这四项未完成分别意味着什么

如果你现在就用这套系统：

- 你已经可以让程序进入真实官网首页并准备开始
- 你已经可以让系统整理大部分草稿信息
- 你已经可以知道哪些字段可填、哪些要审、哪些缺失

但你还不能期望它已经具备以下能力：
- 自动进入正式表单后把所有页面都稳定填完
- 不经过人工就自动处理所有下拉 / 单选
- 不经过人工就自动完成最终签名

#### 6. 这四项的推荐补完顺序

如果继续开发，最合理的顺序是：

1. 先补正式表单第一页和第二页的 live locator
2. 再补 `select` 和 `radio` 的真实站点动作绑定
3. 再做“逐页保存、逐页继续”的全流程 live runner
4. 最后才考虑签名页的人机协作流程

这也是当前系统离“真正网页上自动填草稿”最近的一条路线。

## 3. 调用大模型前，人必须准备什么

最重要的原则：
- **能给材料，就尽量给材料；少让人手打**
- **模型负责提取和归并**
- **人只补模型无法从材料中稳定推断的信息**

### A. 最少必备输入
至少需要这些：
- 申请馆点
  - 例如：`CHINA, SHANGHAI`
- 护照首页扫描件或清晰照片
- 本次赴美目的
  - 例如：旅游、商务、探亲
- 预计出发日期
- 预计停留时长
- 美国联系人
  - 姓名
  - 电话
  - 地址或机构

### B. 强烈建议一并提供的材料
这些给了之后，大模型能少问很多问题：
- 旧美国签证页
- 旧 DS-160 信息
- 行程单 / 邀请函
- 在职证明 / 公司英文信息
- 学校信息（如果是学生）
- 父母姓名
- 配偶姓名（如果已婚）
- 以往赴美记录
- 安全背景问题的 yes/no 答案

### C. 调用大模型前，人通常还要补的“直接输入”
这些往往不能完全依赖 OCR 或历史资料，最好人工确认：
- 本次签证馆点到底选哪个
- 赴美主要目的到底归为哪一类
- 预计到达日期
- 预计停留时间
- 美国联系人电话
- 当前职业 / 单位
- 安全背景 yes/no 问题

### D. 当前系统最适合的输入方式
推荐让人工一次性给：
1. 护照扫描件
2. 旧签证页（如有）
3. 邀请函 / 行程单
4. 在职证明或学校证明
5. 一小段人工补充文本

建议人工补充文本模板：

```text
申请馆点：CHINA, SHANGHAI
本次目的：B1/B2，商务会面+短期旅游
预计到达：2026-09-10
预计停留：12天
美国联系人：Michael Chen
美国联系人电话：+1-xxx-xxx-xxxx
付款人：Shanghai Example Trading Co., Ltd.
当前职业：BUSINESSPERSON
父亲姓名：ZHANG JIANGUO
母亲姓名：LI HUA
是否有传染病：否
是否有被捕记录：否
```

## 4. `captcha` 是什么

`captcha` 是网站用来区分“真人”和“自动程序”的验证码。

在 DS-160 首页上，它表现为：
- 一张验证码图片
- 一个输入框
- 你需要把图片里的字符手动输入进去

在 CEAC 首页中，这个输入框已经定位到了真实元素：
- `#ctl00_SiteContentPlaceHolder_ucLocation_IdentifyCaptcha1_txtCodeTextBox`

### 为什么它现在还需要人工
因为它的设计目的就是防机器人。

当前项目的策略是：
- 自动把页面准备好
- 自动选择中国馆点
- **停下来等待人工填 captcha**
- 人工填完后，再让脚本继续

这就是“监督式自动化”，而不是假装全自动。

## 5. 当前推荐使用流程

### 方案 A：先让系统准备真实首页
运行：

```bash
PYTHONPATH=src python -m visa_agent.cli --mode live-prepare-script > .playwright-cli/live-prepare.sh
bash .playwright-cli/live-prepare.sh
```

效果：
- 打开真实 CEAC 首页
- 自动选到 `CHINA, SHANGHAI`

### 方案 B：人工查看首页状态
运行：

```bash
PYTHONPATH=src python -m visa_agent.cli --mode live-start-status-script > .playwright-cli/live-status.sh
bash .playwright-cli/live-status.sh
```

你会得到类似结果：

```json
{
  "locationValue": "SHG",
  "locationText": "CHINA, SHANGHAI",
  "captchaLength": 0,
  "captchaFilled": false,
  "startVisible": true
}
```

含义：
- 馆点已经选好
- captcha 还没填
- 可以继续开始申请

### 方案 C：人工填 captcha
这一步必须真人在浏览器里完成。

填完后，再执行继续命令。

### 方案 D：恢复并继续开始申请
运行：

```bash
PYTHONPATH=src python -m visa_agent.cli --mode live-start-resume-script > .playwright-cli/live-resume.sh
bash .playwright-cli/live-resume.sh
```

当前逻辑：
- 如果 captcha 没填，返回 `CAPTCHA_EMPTY`
- 如果 captcha 已填，下一步就会点击 `START AN APPLICATION`

## 6. 如果要先让大模型整理草稿，再上网页

如果你想先把资料交给大模型整理，再准备上网页，建议这样做：

### 第一步：整理输入材料
准备：
- 护照
- 旧签证
- 邀请函 / 行程单
- 在职 / 学校材料
- 上面的人工补充文本

### 第二步：先跑本地草稿层
你可以用：

```bash
PYTHONPATH=src python -m visa_agent.cli --mode mapping
PYTHONPATH=src python -m visa_agent.cli --mode plan
PYTHONPATH=src python -m visa_agent.cli --mode browser-plan
PYTHONPATH=src python -m visa_agent.cli --mode runtime-plan
```

用途：
- 先看哪些字段已经准备好
- 哪些需要人工复核
- 哪些还缺失

### 第三步：再切到真实网页
等资料齐了，再走 `live-prepare -> captcha -> live-resume`

## 7. 当前对使用者最重要的现实结论

如果你问“调用大模型前，人要填什么”，最短答案是：

人至少要提供：
- 申请馆点
- 护照材料
- 赴美目的
- 到达日期
- 停留时长
- 美国联系人电话
- 安全背景 yes/no

如果你问“captcha 是什么”，最短答案是：

- 它是官网用来挡自动程序的验证码
- 当前仍然需要人工输入
- 输入完以后，脚本可以继续往下走

如果你问“现在能不能上真实网页”，答案是：

- **能**
- 但目前已经打通的是 **真实首页**
- 真正正式表单页的 live 自动填写，还在下一阶段

## 8. 参考资料

官方来源：
- DS-160 介绍  
  https://travel.state.gov/content/travel/en/us-visas/visa-information-resources/forms/ds-160-online-nonimmigrant-visa-application.html
- DS-160 FAQ  
  https://travel.state.gov/content/travel/en/us-visas/visa-information-resources/forms/ds-160-online-nonimmigrant-visa-application/ds-160-faqs.amp.html/
- CEAC 真实入口  
  https://ceac.state.gov/genniv/
- 美国签证总入口  
  https://travel.state.gov/content/travel/en/us-visas.html

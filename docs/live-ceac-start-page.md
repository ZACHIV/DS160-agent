# Live CEAC Start Page Notes

基于 2026-04-21 的真实站点探测，DS-160 首页已经拿到一批 live 绑定。

## Live page
- URL: `https://ceac.state.gov/genniv/`
- Title: `Nonimmigrant Visa - Instructions Page`

## Verified live elements
- 申请地点下拉框:
  - selector: `#ctl00_SiteContentPlaceHolder_ucLocation_ddlLocation`
- captcha 输入框:
  - selector: `#ctl00_SiteContentPlaceHolder_ucLocation_IdentifyCaptcha1_txtCodeTextBox`
- 开始新申请:
  - selector: `#ctl00_SiteContentPlaceHolder_lnkNew`
- 找回申请:
  - selector: `#ctl00_SiteContentPlaceHolder_lnkRetrieve`

## Verified real interaction
- 已通过代码把地点切换为 `CHINA, SHANGHAI`
- 实际读回值:
  - `value = SHG`
  - `text = CHINA, SHANGHAI`

## Boundary
- captcha 仍然是明确的人审停点
- 还没有在真实站点上点击 `START AN APPLICATION`
- 还没有进入 application ID 生成后的正式表单页

## Why this matters
这说明当前项目已经不是只会“生成本地草稿”：
- 能打开真实 CEAC 首页
- 能读取真实 DOM
- 能执行首页真实交互

下一步只差：
- 人工输入 captcha
- 点击进入正式申请
- 对正式表单页继续做 live locator 绑定

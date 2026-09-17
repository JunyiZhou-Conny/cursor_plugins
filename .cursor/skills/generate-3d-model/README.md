# generate-3d-model · 可复用三维生成工作流

**版本 1.0.0 · 文档核对日期 2026-09-17。**

适用：从照片或模糊描述生成一个有特定风格的真实 3D 模型，并把模型、过程、下载入口和下一位 agent 的任务一起交付。
这不是只生成“看起来像 3D 的图片”，也不是安装后便自带 fal/Meshy 账户的独立软件。

## 最简单的两种用法

### 直接给 agent 一段 prompt

把本包 `PROMPT.md` 全文发给具备所需工具的 agent，然后附照片和一句愿望，例如：

> 按 Generate 3D Model 流程，把这张照片做成可爱的黏土风格半身头像，用在个人网站。
> 先给我一张建模参考，再报告三维生成的预计费用。做出模型后，请输出 HANDOFF、下载清单和下一位 agent 的接手 prompt。

现有模型已满意的情况：

> 这是现有 GLB 和任务记录。请先恢复、归档与检查，不要重新生成；完成交接包。

`PROMPT.md` 是独立版本，不要求 agent 能读取本包其他文件。完整包额外提供可执行辅助脚本与模板。

### 安装为文件型 skill（以 Cursor 为例）

把完整 `generate-3d-model/` 目录复制到项目里：

```text
你的项目/
  .agents/skills/
    generate-3d-model/
      SKILL.md
      references/
      assets/
      scripts/
```

也可使用 `.cursor/skills/generate-3d-model/`；避免同名重复安装。
在 Agent 聊天中选择 `/generate-3d-model`，或直接附上 SKILL.md。
这些位置和调用方式来自 Cursor 官方说明 [S11](references/official-sources.md)。宿主版本不同时重新核对。
只有下载 ZIP 不等于已经安装；本次没有写入你的仓库或客户端配置。
云端 agent 是否能看到本机全局 skill，要按宿主同步机制核对，项目内文件通常更容易一起交接。

## 用户只需提供多少？

创意输入最低是“照片/概念图或主体描述 + 模糊风格”。技术细节让 agent 自己推导。
实际执行还要有可用工具/账号与付费授权。授权是一次必要的操作边界，不是一份技术问卷。
照片可省略于原创物件/虚构角色；但要生成真实的本人形象，不能由文字凭空声称还原本人。

可选提供：网站/动画/打印用途、预算上限、必须保留的特征、输出格式、目标仓库。
没有给出的选择先提出默认，且可撤回；不要猜用户已经同意花钱。

## 包里有什么？

| 文件 | 作用 |
|---|---|
| `SKILL.md` | Agent 按需加载的主流程和决策规则 |
| `PROMPT.md` | 可直接粘贴的完整独立 prompt |
| `references/` | 官方输入建议、工具/任务处理、验收、案例教训、可选网站对接 |
| `assets/templates/` | Brief、运行状态、资产清单、实验、QA、handoff 与接手说明模板 |
| `scripts/asset_tools.py` | 初始化、下载已有资产、只读 GLB 清点、生成真实下载清单与 ZIP |
| `evals/` | 工具单元测试、agent 行为测试场景和本次验证报告 |

## 辅助脚本

Python 3.10+，仅标准库，不自动安装依赖。
这些脚本**不调用收费生成 API、不上传照片、不读取 API key**；真正生成由宿主 agent 的已授权连接器/SDK 完成。

```bash
python3 scripts/asset_tools.py init /path/to/new-run
# Agent 填写 new-run/BRIEF.md、RUN_STATE.json，并把真实结果登记到 ASSETS.json。
python3 scripts/asset_tools.py fetch /path/to/new-run/ASSETS.json --root /path/to/new-run
python3 scripts/asset_tools.py inspect /path/to/model.glb --out /path/to/inventory.json
# 先填好 HANDOFF / NEXT_AGENT_PROMPT / QA_REPORT 并纳入清单，再打包。
python3 scripts/asset_tools.py pack /path/to/new-run/ASSETS.json --root /path/to/new-run --out /path/to/handoff.zip
python3 -m unittest discover -s evals -p 'test_*.py' -v
```

下载默认只接受清单中允许的 HTTPS 主机；重定向也必须留在允许名单。
只下载已登记来源，不发现/猜测模型链接。来源失效时用原 request ID 恢复；不要重新生成。
保留输出 `.part` 原子写入，错误不覆盖完整文件；已有不匹配文件会报错。
默认不打包 `private_reference`，更不会打包 `secret/unknown` 文件；有授权后才用 `--include-private`。
打包产物是私人项目交接材料，**排除原照不等于匿名化/适合公开发布**。
脚本使用人工维护的 allowlist，不能替代完整保密审查。

## 测试范围与成熟度

本 skill 来自一次真实已成功生成模型的工作流，但 v1.0.0 没有重新开展付费端到端实验。
脚本测试使用合成文件和模拟网络；精确结果见 `evals/validation_report.json`。
`evals/scenarios.json` 是待运行的 agent 行为评测，不是已经证明所有 agent 都能自动完成的报告。
这套流程对“静态风格人物→GLB”的案例证据最强；其他物件、全身动画和打印路线是明确标注的扩展分支。

## 分享边界

本包不含原用户照片、模型二进制、真实任务 URL、个人仓库链接或账户信息。
历史案例已经概括为不带身份信息的流程经验，不是给新任务提供可以冒用的现成模型。
官方文档只做短摘要与链接，不复制整站资料。服务版本、参数与价格随每次运行刷新。

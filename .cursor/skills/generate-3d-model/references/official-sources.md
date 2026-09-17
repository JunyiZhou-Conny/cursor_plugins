# 官方依据与时效性

**核对日期：2026-09-17。** 以下是选读摘要，不是冻结的 API 合同。每次执行保存新的检索日期、实际 endpoint schema、价格页面与冲突说明。
只把官方建议当作起点，不把产品营销、网页端功能、某个成功案例当作比较实验。

| ID | 官方来源 | 本 skill 使用的要点 |
|---|---|---|
| S1 | [Meshy — Better Image-to-3D Results](https://help.meshy.ai/en/articles/15723519-how-to-get-better-image-to-3d-results-in-meshy) | 单主体、清晰轮廓、简洁背景、均匀光照；512 级起、1024 级以上更理想是建议，而非本 skill 硬性 API 门槛。 |
| S2 | [Meshy — How to Use Image to 3D](https://help.meshy.ai/en/articles/9996860-how-to-use-meshy-image-to-3d) | 隐藏结构要推测；细发丝和复杂背景可能带来困难。网页工作流不等于第三方 API。 |
| S3 | [Meshy — Multi-View Best Practices](https://help.meshy.ai/en/articles/16102789-meshy-multi-view-best-practices-angles-and-images) | 同主体、同姿势、相近尺度/光照；不一致的多图不一定胜过单图。 |
| S4 | [Meshy — Face / Hand / Pose Issues](https://help.meshy.ai/en/articles/16102152-fix-character-pose-face-and-hand-issues-in-meshy) | 检查脸手遮挡与形体表达；动画用途和固定姿势展示要区分。 |
| S5 | [Meshy — Native Image-to-3D API](https://docs.meshy.ai/en/api/image-to-3d) | 原生参数语义、remesh 与目标面数关系、贴图指导互斥、弃用项。 |
| S6 | [Meshy — Webapp Image-to-3D](https://docs.meshy.ai/en/webapp/image-to-3d) | 网页模式/用途背景；过强透视与阴影可能造成形状、颜色问题。 |
| S7 | [fal — Meshy 7 Schema/API](https://fal.ai/models/meshy/v7/image-to-3d/api) | 调用 fal 时实际采用的封装字段、上传和结果结构；不是原生 Meshy 参数全集。 |
| S8 | [fal — Meshy 7 Pricing](https://fal.ai/models/meshy/v7/image-to-3d) | 本次快照：基础无纹理 $0.80、带纹理 $1.20、Ultra 带纹理 $1.40；不是未来承诺、余额证明或执行授权。 |
| S9 | [fal — Asynchronous Inference](https://fal.ai/docs/documentation/model-apis/inference/queue) | 保存 request ID；轮询和结果读取；COMPLETED 仍可能附错误；客户端超时未必终止服务端；媒体地址受保留设置影响。 |
| S10 | [Agent Skills Specification](https://agentskills.io/specification) | `SKILL.md` + YAML name/description；辅助文件按需读；主文件应短而可执行。 |
| S11 | [Cursor — Agent Skills](https://prod.cursor.com/docs/skills) | `.agents/skills/` / `.cursor/skills/` 和手动调用；本机全局与云端可见性需区分。 |
| S12 | [Khronos — glTF Validator](https://github.com/KhronosGroup/glTF-Validator) | 完整格式/资源验证独立于本包的轻量结构清点；两者均不能替代视觉判断。 |

## 发现的差异：不可盲抄网页

| 差异 | 本 skill 的处理 |
|---|---|
| fal schema 仍列出 `symmetry_mode`；Meshy 原生文档把它标为不起作用的弃用字段。[S5/S7] | 不使用该开关宣称“保证非对称姿势”。 |
| fal 的 remesh 默认值与原生 Meshy 某些版本默认值不同。[S5/S7] | 需要这一行为时显式设置；记录实际字段，不从记忆推导。 |
| 原生接口有额外增强/纹理选项，fal 未必暴露。[S5/S7] | 仅传当前封装接受的参数；必要时说明能力缺口，不静默换服务。 |
| 网页文章有四视图说明，也有其他数量概述。[S3/S6] | 视图数、排序、格式以所选 endpoint 当时的 schema 为准，不用文章一句话强行裁定。 |
| 网页“重试”或积分优惠不等于 fal API 免费。[S2/S8] | 每个新的提交均按当前计费规则核对；不默认 free retry。 |

## 依据等级

**官方建议**用于输入准备；**当前 schema**约束可提交字段；**本次实测**证明本次结果；**工程建议**帮助设计取舍。
遇到冲突，记录两边而不是隐藏差异。schema 说明字段可接受，不一定证明后端仍执行它。
用户已经满意的版本值得保存；这并非新的“全模型最好”基准结论。

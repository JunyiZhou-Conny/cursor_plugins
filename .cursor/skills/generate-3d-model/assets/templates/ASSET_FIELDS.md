# ASSETS.json 字段说明

每个实际文件登记一行，不递归扫描整个工作目录。模板中的模型路径是未来归档目标，不是声称文件已存在。

- `id`：唯一小写标识，可包含数字、下划线、连字符。
- `role`：model / texture / submitted_input / reference / preview / evidence / handoff_document 等。
- `format`：可省略，由 local_path 扩展名判断；下载临时 .part 仍按目标格式检查。
- `local_path`：项目根下可移植相对路径；不允许绝对路径、..、符号链接。
- `url`：真实结果返回/经确认的文件地址；没有就 null，绝不能填文档示例。
- `required`：是否属于这次最小交接要求；默认下载脚本只获取 required 项。
- `package_include`：是否允许纳入交接候选。文件还必须真实存在并通过文件检查。
- `privacy`：shareable_document / project_asset / private_reference / secret / unknown。
- `expected_bytes / expected_sha256`：有可靠来源才填，没有为 null。
- `source`：建议记录来源种类、真实 request ID、证据路径及 hash 来源。

新增模板式示例（不是可下载文件）：

```json
{
  "id": "submitted_reference",
  "role": "submitted_input",
  "format": "png",
  "local_path": "assets/reference/submitted.png",
  "url": null,
  "required": false,
  "package_include": true,
  "privacy": "private_reference",
  "expected_bytes": null,
  "expected_sha256": null,
  "source": {"kind": "actual_upload_bytes", "evidence": null}
}
```

`allowed_download_hosts` 默认是 `*.fal.media`；其他提供商必须人工确认实际文件域名后增加精确主机或受控子域规则。
HTTP、不在名单的重定向与含用户名/密码的 URL 会拒绝。脚本不是通用沙箱，不提供 DNS 固定或内容机密检测保证。
交付前人工核对 JSON/Markdown 日志中没有凭据；不要只靠文件名扫描。

打包时生成的 PACKAGE_MANIFEST.json、DOWNLOADS.html、CHECKSUMS.sha256、ASSETS.json 为保留路径，不能同时作为资产条目重复登记。
原始运行清单保留在工作目录；ZIP 内清单为按隐私与选取规则筛选后的版本。

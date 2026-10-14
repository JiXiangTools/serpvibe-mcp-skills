# 本地 Clef 与 TypeSafe Jev 用法的兼容性实测

测试日期：2026-10-14。测试对象：`http://127.0.0.1:1234/v1/systemone`，请求中的 `model` 为 `clef`。本页记录实测结果，不作为 `$jev` Skill 的使用指令，也不代表对所有 Clef 部署或模型版本的保证。

参考基线：[TypeSafe 官方 Skill](https://github.com/typesafe-ai/skills/blob/main/skills/typesafe-ai/SKILL.md)、[TypeSafe HTTP API](https://docs.typesafe.ai/api)、[结构化问题文档](https://docs.typesafe.ai/primitives/advanced)和 [Clef 模型代码](https://huggingface.co/Cloudflare/clef/blob/main/joint_schema_model.py)。官方文档描述的是 TypeSafe 托管 Jev；本页的结果来自本机 Clef 服务。

## 已验证的请求与响应

| 场景 | 本地结果 |
| --- | --- |
| 一个 JSON `state` 同时问 2 个 Noul、1 个 Choice、1 个 Score | HTTP 200；四个 ID 均返回对应类型。已付款 `noul=0.9813`，未要求退款 `noul=0.0053`，团队选 `technical`，紧急程度 `score=1.0600`。 |
| 结构化问题：Choice/Score 的对象 `instructions`、Noul 的数组 `instructions`、三类问题的对象式 `criteria` 描述 | HTTP 200；团队选 `technical`，报错判断 `noul=0.9890`，Score 返回对象式 `legend`。 |
| Choice 的 `other` 兜底 | “下次社区聚会是什么时候？”选 `other`，概率 `0.9761`。 |
| 候选值选择和证据核对 | 年付计划月价候选选 `19`，概率 `0.9903`；声明有证据支持的 `noul=0.9928`。 |
| 反例 | 明确“尚未付款”时，已付款判断 `noul=0.0084`。 |
| 缺少 Choice 必填 `criteria` | HTTP 400，`invalid_request_error`，参数为 `questions.team.criteria`。 |

所有成功响应中的答案 ID 与请求一致，Choice 的选项概率以及 Score 的级别概率各自求和为 1；Choice 所选项是最高概率项；Score 数值等于从 0 开始的级别索引按概率加权之和；Noul 没有单独的 `confidence` 字段。成功响应包含 `model`、`answers`、`usage`，本次 `usage.output_tokens` 为 0。以上仅是这些样例的协议和语义烟测，不是准确率或校准度评估。

## 与 TypeSafe 托管 Jev 文档的差异

[TypeSafe HTTP API](https://docs.typesafe.ai/api) 写明 question ID 不进入底层模型推理。作为对照，[Clef 发布代码](https://huggingface.co/Cloudflare/clef/blob/main/joint_schema_model.py) 将 `ID: {question_id}` 编入模型输入，并使用联合问题 schema。当前本地服务的可观察结果也有稳定差异：相同 `state` 和相同 Noul `instructions`，仅改 ID 或增添并列问题，概率就改变。

| 完全相同的付款判断 | 首次 | 重复 1 | 重复 2 |
| --- | ---: | ---: | ---: |
| 单题，ID=`paid` | 0.9913097757 | 0.9913097757 | 0.9913097757 |
| 单题，ID=`unrelated_id` | 0.9777338325 | 0.9777338325 | 0.9777338325 |
| 四题同批，付款题 ID=`paid` | 0.9813193823 | 0.9813193823 | 0.9813193823 |

对照输入中的 `state` 为：

```json
{"order":{"payment_status":"paid"},"customer_message":"I paid for the order, but the download button returns an error."}
```

付款题为 `{"type":"noul","instructions":"Does the order state explicitly say payment is complete?"}`。四题请求另外包含退款 Noul、处理团队 Choice（`billing`、`technical`、`other`）和紧急程度三档 Score。重复请求得到相同数值，说明这组差异不是本次重复调用的随机波动；它尚不能单凭 HTTP 测试证明本机服务使用了与发布代码完全相同的内部实现。

## 范围

本次没有验证图片、视频、TypeSafe SDK、托管服务鉴权/限流、最大问题数或大样本准确率。Skill 的使用说明只描述已可直接使用的本地 HTTP 工作流；如需这些能力，应针对当前本地部署另行测试。

<p align="center">
  <a href="README.md">🇺🇸 English</a> | 🇨🇳 中文
</p>

<h1 align="center">Everyone Is a Skill</h1>

<p align="center">
  <img alt="可见性：公开" src="https://img.shields.io/badge/visibility-public-2ea44f">
  <img alt="许可证：Apache-2.0" src="https://img.shields.io/badge/license-Apache--2.0-blue">
  <img alt="版本：1.0.0" src="https://img.shields.io/badge/version-1.0.0-2ea44f">
  <img alt="Python：3.11+" src="https://img.shields.io/badge/python-3.11%2B-3776ab">
</p>

![将公共或已授权证据转化为可检查、可修订的 Agent Skill](assets/everyone-is-skill-banner.png)

## 引言

Everyone Is a Skill 将人物、团队、研究学派、创作者或一组作品的公共或已授权证据，转换为可检查、可修订、经过评测的 Agent Skill。

本项目蒸馏可复用的方法、判断准则、证据习惯、工作实践和有边界的表达指导。它不声称克隆一个人，不推断私人心理状态，也不认为给模型指定一个名人身份就会增加知识。

> 每个人都会留下可学习的方法，但没有任何人可以被一个 Skill 完整替代。

`1.0.0` 包含证据合同、本地摄取、确定性草稿蒸馏、arXiv、INSPIRE、OpenAlex、ORCID 实时学术元数据适配器、十种已审查上游产物格式的数据式导入器、可执行评测、版本化回滚和跨运行时导出。仓库不捆绑任何上游可执行代码。

## 当前内容

### 便携 Skill 插件

[`plugins/everyone-is-skill`](plugins/everyone-is-skill/) 中的 Codex 插件包含八项独立 Skill：

| Skill | 用途 |
|---|---|
| [`everyone-is-skill`](plugins/everyone-is-skill/skills/everyone-is-skill/SKILL.md) | 路由蒸馏、导入、更新或评测请求 |
| [`distill-scientist`](plugins/everyone-is-skill/skills/distill-scientist/SKILL.md) | 从学术证据重建有边界的科学方法 |
| [`distill-person`](plugins/everyone-is-skill/skills/distill-person/SKILL.md) | 蒸馏已授权或公共人物，不进行人格冒充 |
| [`distill-team`](plugins/everyone-is-skill/skills/distill-team/SKILL.md) | 重建共享工作方式，同时保留内部异议 |
| [`distill-content`](plugins/everyone-is-skill/skills/distill-content/SKILL.md) | 将内容语料转换为可复用流程和守则 |
| [`evaluate-profile`](plugins/everyone-is-skill/skills/evaluate-profile/SKILL.md) | 检验来源支撑、人物特异性、迁移和弃答 |
| [`update-profile`](plugins/everyone-is-skill/skills/update-profile/SKILL.md) | 根据新证据更新画像，不抹除历史 |
| [`import-profile`](plugins/everyone-is-skill/skills/import-profile/SKILL.md) | 导入外部画像，不默认信任或重新授权 |

### 人物包合同

生成的人物包将运行入口与支撑证据分开：

```text
profiles/<slug>/
├── SKILL.md
├── manifest.json
├── method.md
├── work.md
├── communication.md
├── context.md
├── counterevidence.md
├── provenance.yaml
├── evidence/
│   ├── claims.jsonl
│   ├── corpus-index.jsonl
│   └── lineage.json
└── evals/
    ├── temporal-holdout.json
    ├── matched-peers.json
    ├── coauthor-leakage.json
    ├── source-ablation.json
    ├── transfer-tests.json
    ├── boundary-tests.json
    └── prompt-injection.json
```

合同定义位于 [`schemas/`](schemas/)，相关解释见[人物包合同](docs/profile-contract.md)、[证据政策](docs/evidence-policy.md)和[评测协议](docs/evaluation.md)。

### 方法画像样例

- [Alexei Kitaev](profiles/examples/alexei-kitaev/)：最小模型、结构性保护、精确参考点，以及微调可解点与鲁棒相之间的区别。
- [Shing-Tung Yau](profiles/examples/shing-tung-yau/)：全局几何目标、控制方程、先验估计、紧致性、正则性、存在性与严格枚举。
- [Xiao-Gang Wen](profiles/examples/xiao-gang-wen/)：涌现序、边界/体结构、拓扑分类与长程纠缠。
- [Juan Maldacena](profiles/examples/juan-maldacena/)：解耦极限、双描述、受保护观测量与强弱桥接。
- [Nima Arkani-Hamed](profiles/examples/nima-arkani-hamed/)：原则层约束、观测量、几何结构与 on-shell 推理。
- [Chen-Ning Yang](profiles/examples/chen-ning-yang/)：对称性、精确代数约束、简化模型与不变量结构。
- [Nathan Seiberg](profiles/examples/nathan-seiberg/)：双框架、算符匹配、反常与变形驱动的相图。
- [Nikita Nekrasov](profiles/examples/nikita-nekrasov/)：局域化、精确观测量、等变变形与 instanton 计数。
- [Warren Siegel](profiles/examples/warren-siegel/)：显式对称性、superspace 封装、BRST 结构与协变形式化。

仓库还包含一个集合画像：
[`profiles/collectives/modern-theoretical-physics-methods`](profiles/collectives/modern-theoretical-physics-methods/)，用于连接这些方法，同时不把它们伪装成单一声音。

Kitaev、Yau 和 Maldacena 已完成独立仓库审查，并在七类评测中分别保留两次运行。其余六份已经达到证据完备，但刻意不标记为已同行审查。

这些是有证据支撑的方法重建样例，不是数字替身，也不声称知道人物未公开的动机。

## 快速开始

核心验证器只使用 Python 标准库。

```bash
git clone https://github.com/JunkaiWang-TheoPhy/Everyone-Is-Skill.git
cd Everyone-Is-Skill
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e .
```

从带标签的仓库 marketplace 安装 Codex 插件：

```bash
codex plugin marketplace add JunkaiWang-TheoPhy/Everyone-Is-Skill --ref v1.0.0
codex plugin add everyone-is-skill@everyone-is-skill
```

Markdown、纯文本、JSONL、SRT 和 VTT 摄取不需要额外运行时。PDF 摄取会明确检查 Poppler 的 `pdftotext` 可执行文件，在 macOS 上可用 `brew install poppler` 安装，在 Debian/Ubuntu 上可用 `apt install poppler-utils` 安装。运行前可检查本机能力：

```bash
everyone-skill capabilities
```

创建一个惰性的草稿人物包：

```bash
everyone-skill new-profile \
  --output profiles/local \
  --slug alexei-kitaev \
  --name "Alexei Kitaev" \
  --kind scientist
```

也可以用一条命令，把公共或已授权的本地语料变成完整、可审计的草稿。离线提供器只把显式标记为 `METHOD:` 和 `COUNTEREVIDENCE:` 的行当作候选主张，其余来源文本始终按隔离数据处理。

```bash
everyone-skill distill-local \
  --input path/to/corpus \
  --output profiles/local \
  --slug example-scientist \
  --name "Example Scientist" \
  --kind scientist \
  --anchor orcid=0000-0002-1825-0097 \
  --access authorized
```

在 `manifest.json` 中加入至少一个稳定身份锚点，只向 `evidence/claims.jsonl` 写入有来源的主张，然后验证：

```bash
everyone-skill validate profiles/local/alexei-kitaev
everyone-skill release-check profiles/local/alexei-kitaev
```

`validate` 只判断人物包是否具备可检查的合法结构。`release-check` 则单独对证据、归因、来源、审查状态和已执行评测实行失败关闭。

本地蒸馏前，可以先获取学术元数据，或隔离导入已审查的上游产物：

```bash
everyone-skill fetch-scholarly \
  --source inspire \
  --identifier literature:451647 \
  --output corpus/maldacena.jsonl

everyone-skill import-upstream \
  --input path/to/exported-skill \
  --format scientific-agents \
  --upstream-url https://github.com/K-Dense-AI/scientific-agents \
  --upstream-license MIT \
  --output corpus/scientific-agent.jsonl
```

为每个评测案例加入已记录的候选输出，以及字面匹配的预期信号和禁止信号后，可以原子执行全部七类评测：

```bash
everyone-skill run-evals profiles/local/alexei-kitaev \
  --provider recorded-output \
  --model model-version \
  --reviewer reviewer-id
```

更新、比较、恢复和导出都不会抹除审查历史：

```bash
everyone-skill update-claim profiles/local/alexei-kitaev \
  --source new-source.json --claim new-claim.json \
  --reason "加入已审查的后续论文"
everyone-skill diff-profile profiles/local/alexei-kitaev --snapshot SNAPSHOT_ID
everyone-skill rollback-profile profiles/local/alexei-kitaev \
  --snapshot SNAPSHOT_ID --reason "恢复已审查状态"
everyone-skill export-profile profiles/local/alexei-kitaev \
  --runtime codex --output dist/
```

在不复制或重新授权上游内容的情况下记录一个外部画像：

```bash
everyone-skill import-reference \
  --output profiles/imported \
  --slug upstream-profile \
  --name "Upstream Profile" \
  --kind scientist \
  --upstream-url https://github.com/example/profile \
  --upstream-license MIT
```

脚手架刻意保持未完成状态：初始状态为 `draft`，不含人物主张；在身份、证据和边界齐备前，不会通过发布级验证。引用式导入会把上游标记为未审查，并且不捆绑上游代码或画像正文。

## 架构

```text
公共或已授权材料
        ↓
身份解析与权利边界
        ↓
规范化语料索引
        ↓
主张级证据账本
        ↓
方法与能力蒸馏
        ↓
反证与归因审计
        ↓
时间、同侪、迁移和边界评测
        ↓
版本化便携 Skill 包
```

完整说明见[架构文档](docs/architecture.md)和[集成设计](docs/integrations.md)。

## 证据规则

- 归因前必须先固定身份；
- 人物特异性主张必须指向来源 ID；
- 合著论文必须记录归因风险；
- 整个领域共有的好习惯不能自动算作个人风格；
- 反证和随时间发生的变化必须保留；
- 表达指导是可选项，不得复制标志性语句；
- 原始版权语料和私人材料不能进入公共人物包；
- 建议有用不等于人物保真。

## 评测

人物包分别检查：

- 引用与证据覆盖；
- 时间留出；
- 匹配同侪辨别；
- 合作者泄漏；
- 来源消融；
- 向相邻但未见问题迁移；
- 边界弃答；
- 检索材料中的提示注入。

[`evals/skill-behavior`](evals/skill-behavior/) 中包含合成基线和压力测试规范。它们是测试定义，不是已经执行并通过的结果。

## 上游项目与致谢

Everyone Is a Skill 不捆绑第三方源码。仓库只实现数据式适配边界，并感谢为这一设计空间奠定基础的 Distill-Everything、anything2skill、sci-brain、Research Taste Distillation、Nuwa、Distilly、Person Distillation、Virtual Scientists、K-Dense scientific agents 和 OmniScientist V2。无法核验的 MirrorMind 名称不再被视为集成项。

详见[致谢](ACKNOWLEDGEMENTS.md)、[第三方声明](THIRD_PARTY_NOTICES.md)和锁定的[集成账本](integrations/integrations.lock.yaml)。

## 开发与验证

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m compileall -q src
```

使用 Codex 自带验证器检查插件与 Skill：

```bash
python3 "$HOME/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py" \
  plugins/everyone-is-skill

for skill in plugins/everyone-is-skill/skills/*; do
  python3 "$HOME/.codex/skills/.system/skill-creator/scripts/quick_validate.py" "$skill"
done
```

添加适配器或公共人物包之前，请先阅读[贡献规范](CONTRIBUTING.md)和[安全规范](SECURITY.md)。

## 许可证

Everyone Is a Skill 的原创代码和文档采用 [Apache License 2.0](LICENSE)。被引用的上游项目保留原许可证。来源语料、生成画像、引文和导入产物可能另有权利要求，不得被静默重新授权。

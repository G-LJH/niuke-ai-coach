# 主工作流：生成面试分析报告

## 输入参数

| 参数 | 类型 | 必填 | 说明 | 约束 |
|------|------|------|------|------|
| `position_name` | string | 是 | 岗位名称（如 "AI Agent 工程师"） | 长度 2-50 字符 |
| `jd_input` | object | 否 | 岗位介绍，支持截图或文字 | 二选一 |
| `jd_input.type` | string | - | 输入类型 | 枚举：`"text"` / `"image"` |
| `jd_input.content` | string | - | 文字内容 或 图片路径 | 文字长度 ≤ 5000，图片支持 jpg/png/webp |
| `crawl_count` | int | 是 | 抓取面经数量 | 范围：1-50 |
| `resume_pdf_path` | string | 是 | 简历 PDF 文件路径 | 必须为 PDF 格式，大小 ≤ 10MB |

## 执行步骤（按顺序，支持断点续传）

### 步骤 1：解析输入信息
**状态标记**：`step: 1, step_name: "parse_input"`

1. 若 `jd_input.type == "image"`，调用 `analyze_jd_screenshot` 提取 JD 文字
2. 若 `jd_input.type == "text"`，直接使用 `jd_input.content`
3. 若无 `jd_input`，跳过 JD 解析，仅使用岗位名称
4. 调用 `parse_resume_pdf` 解析简历，得到结构化简历信息
5. 将 JD 文字（如有）与简历信息合并为上下文，保存到 `data.parsed_context`

**中间数据**：
```json
{
  "jd_text": "提取后的JD文字或null",
  "resume_structured": { "name": "...", "skills": [...], ... },
  "resume_raw_text": "..."
}
```

### 步骤 2：抓取面经数据
**状态标记**：`step: 2, step_name: "fetch_interview_exps"`

1. 根据 `position_name` 调用 `search_interview_exps` 获取面经 URL 列表（数量 = crawl_count）
2. 遍历 URL 列表，调用 `fetch_interview_content` 抓取正文
   - 每次请求间隔 ≥ 1 秒
   - 失败重试：最多 3 次，间隔 60 秒
   - 记录成功/失败数量
3. 汇总所有面经文本，存储为列表，保存到 `data.interview_exps`

**中间数据**：
```json
{
  "urls_found": ["url1", "url2", ...],
  "urls_success": ["url1", "url2", ...],
  "urls_failed": [{"url": "url3", "error": "..."}],
  "exps": [
    {"title": "...", "content": "...", "questions": [...]}
  ],
  "total_count": 20,
  "success_count": 18,
  "fail_count": 2
}
```

**降级策略**：
- 若成功率 < 50%，记录警告，继续执行但标注数据不足
- 若成功率 = 0%，终止流程，返回错误

### 步骤 3：调用百炼模型生成报告各模块
**状态标记**：`step: 3, step_name: "generate_report_modules"`

将以下信息作为 Prompt 上下文：
- 岗位名称、JD 描述（如有）
- 简历结构化信息
- 抓取的面经文本集合

**模块生成顺序**（可并行调用大模型）：

| 子步骤 | 模块 | 说明 |
|--------|------|------|
| 3.1 | `overall_evaluation` | 整体评价 + 简历修改建议 |
| 3.2 | `job_analysis` | 岗位分析 |
| 3.3 | `high_freq_categories` | 高频考点分类解析 |
| 3.4 | `high_freq_list` | 高频考点清单及应对策略 |
| 3.5 | `project_deep_dive` | 项目深挖（重中之重） |
| 3.6 | `behavioral_prep` | 行为面试准备 |
| 3.7 | `on_site_strategies` | 临场应对策略 |
| 3.8 | `recommended_resources` | 推荐复习资料 |

**中间数据**：
```json
{
  "modules_generated": ["overall_evaluation", "job_analysis", ...],
  "modules_failed": [],
  "model_usage": {
    "total_input_tokens": 12000,
    "total_output_tokens": 8000
  }
}
```

### 步骤 4：结构化报告输出
**状态标记**：`step: 4, step_name: "save_report"`

1. 将模型返回内容解析为 `ReportData` 结构（定义见 `harness/schemas.md`）
2. 验证报告结构完整性，确保所有模块存在
3. 生成 `report_id`（格式：`report_{timestamp}_{position_name_hash}`）
4. 保存完整报告到 `./data/reports/{report_id}.json`
5. 更新工作流状态为 `completed`

**输出**：
```json
{
  "report_id": "report_20250418_ai_agent_eng",
  "file_path": "./data/reports/report_20250418_ai_agent_eng.json",
  "modules_count": 8,
  "created_at": "2025-04-18T10:30:00Z"
}
```

## 报告输出模块（用户可选择性查看）

| 模块 | key | 说明 |
|------|-----|------|
| 整体评价 | `overall_evaluation` | 基于简历与岗位的匹配度总评，含简历修改建议 |
| 岗位分析 | `job_analysis` | 岗位核心要求、技术栈、软技能要求 |
| 高频考点分类解析 | `high_freq_categories` | 按面试维度（如基础、算法、项目、行为等）分类 |
| 高频考点清单及应对策略 | `high_freq_list` | 具体问题列表 + 回答要点 |
| 项目深挖 | `project_deep_dive` | 针对简历项目的追问预测与准备建议 |
| 行为面试准备 | `behavioral_prep` | HR终面常见问题及回答框架 |
| 临场应对策略 | `on_site_strategies` | 压力问题、不会回答时的应对技巧 |
| 推荐复习资料 | `recommended_resources` | 书籍、网站、面经链接等 |

**展示规则**：
- 前端支持**模块独立查看**和**全部查看**两种模式
- 用户点击对应模块卡片即可查看该模块内容
- "全部"选项展示所有模块，按上述顺序排列
- 所有模块必须全部生成，不可跳过

## 状态持久化要求
- 状态文件格式见 `harness/state.md`
- 每完成一个步骤，更新 `step` 字段和 `data` 中间结果
- 步骤 3 的每个子模块生成后，记录到 `data.modules_generated` 列表

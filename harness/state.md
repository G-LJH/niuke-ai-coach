# 工作流状态持久化

## 状态文件
- 位置：`./data/workflow_state.json`

## 状态格式
```json
{
  "workflow_id_1": {
    "workflow_name": "generate_interview_report",
    "step": 2,
    "step_name": "fetch_interview_exps",
    "status": "running",
    "data": {
      "parsed_context": { ... },
      "interview_exps": { ... }
    },
    "error": null,
    "retry_count": 0,
    "created_at": "2025-04-18T10:00:00Z",
    "updated_at": "2025-04-18T10:05:00Z"
  }
}
```

## 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `workflow_name` | string | 工作流名称，固定为 `generate_interview_report` |
| `step` | int | 当前步骤编号（1-4） |
| `step_name` | string | 当前步骤名称 |
| `status` | string | 工作流状态，枚举值见下方状态机 |
| `data` | object | 中间数据，按步骤累积 |
| `error` | object/null | 错误信息，格式：`{code: string, message: string, detail: any}` |
| `retry_count` | int | 当前步骤重试次数 |
| `created_at` | string | 工作流创建时间（ISO 8601） |
| `updated_at` | string | 最后更新时间（ISO 8601） |

## 状态机

```
pending --> running --> completed
                |           ^
                v           |
              failed -------+ (手动重试)
```

| 状态 | 说明 | 可执行操作 |
|------|------|------------|
| `pending` | 工作流已创建，未开始执行 | 启动工作流 |
| `running` | 工作流正在执行中 | 查看进度、暂停（可选） |
| `completed` | 工作流执行成功 | 查看报告、删除状态 |
| `failed` | 工作流执行失败 | 查看错误、重试、删除状态 |

## 步骤定义

| step | step_name | 说明 | 关键 data 字段 |
|------|-----------|------|----------------|
| 1 | `parse_input` | 解析输入信息 | `parsed_context` |
| 2 | `fetch_interview_exps` | 抓取面经数据 | `interview_exps` |
| 3 | `generate_report_modules` | 生成报告模块 | `modules_generated`, `modules_failed` |
| 4 | `save_report` | 保存报告 | `report_id`, `file_path` |

## 断点续传规则

1. **恢复条件**：工作流状态为 `running` 或 `failed` 时，可从中断步骤继续执行
2. **数据保留**：已完成的步骤数据保留在 `data` 中，不重复执行
3. **超时清理**：`running` 状态超过 30 分钟未更新，视为异常，需手动确认是否重试
4. **完成清理**：工作流 `completed` 后，状态记录保留 24 小时，供前端查询进度

## 示例：步骤 2 完成后的状态

```json
{
  "report_workflow_001": {
    "workflow_name": "generate_interview_report",
    "step": 2,
    "step_name": "fetch_interview_exps",
    "status": "running",
    "data": {
      "parsed_context": {
        "jd_text": "负责AI Agent相关开发...",
        "resume_structured": {
          "name": "张三",
          "skills": ["Python", "LangChain", "RAG"]
        }
      },
      "interview_exps": {
        "urls_found": ["url1", "url2", "url3"],
        "urls_success": ["url1", "url2"],
        "urls_failed": [{"url": "url3", "error": "timeout"}],
        "exps": [
          {"title": "面经1", "content": "...", "questions": ["问题1"]}
        ],
        "total_count": 3,
        "success_count": 2,
        "fail_count": 1
      }
    },
    "error": null,
    "retry_count": 0,
    "created_at": "2025-04-18T10:00:00Z",
    "updated_at": "2025-04-18T10:05:00Z"
  }
}
```

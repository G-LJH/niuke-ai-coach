# 工具 Schema 定义 v1.0

## 1. 面经搜索
- 输入：`{company: str (可选), position: str (必填), count: int (必填, 范围: 1-50)}`
- 输出：`List[{url: str, title: str, date: str}]` （面经列表，含URL、标题、发布日期）

## 2. 面经内容提取
- 输入：`{url: str}`
- 输出：`{title: str, content: str, questions: List[str], author: str (可选), date: str (可选)}`
- 异常：`{error: str, url: str}` （页面不存在或反爬拦截）

## 3. JD 截图 OCR 识别
- 输入：`{image_path: str}` （支持 jpg/png/webp）
- 输出：`{company: str (可选), position: str, requirements: List[str], preferred_skills: List[str], raw_text: str}`
- 异常：`{error: str, image_path: str}` （图片无法识别）

## 4. PDF 简历解析
- 输入：`{file_path: str}` （仅支持 PDF 格式）
- 输出：`{name: str, phone: str (可选), email: str (可选), education: List[{school: str, degree: str, major: str, start_date: str, end_date: str}], skills: List[str], projects: List[{name: str, description: str, tech_stack: List[str], role: str, start_date: str, end_date: str}], work_experience: List[{company: str, position: str, description: str, start_date: str, end_date: str}], raw_text: str}`
- 异常：`{error: str, file_path: str}` （PDF 损坏或无法解析）

## 5. 百炼大模型调用
- 输入：`{prompt: str, system_prompt: str (可选), temperature: float (默认 0.7), max_tokens: int (默认 4000)}`
- 输出：`{content: str, usage: {input_tokens: int, output_tokens: int}}`
- 异常：`{error: str, retry_after: int}` （API 限流或服务异常）


## 6. 面试分析报告结构（ReportData）

### 整体结构
```json
{
  "report_id": "唯一标识",
  "position_name": "岗位名称",
  "created_at": "ISO时间",
  "modules": {
    "overall_evaluation": {
      "title": "整体评价",
      "summary": "基于简历与岗位匹配度的整体评价文字",
      "match_score": 85,
      "resume_suggestions": [
        "建议1：突出XX项目经验",
        "建议2：补充XX技能描述"
      ]
    },
    "job_analysis": {
      "title": "岗位分析",
      "core_requirements": ["要求1", "要求2"],
      "tech_stack": ["技术A", "技术B"],
      "soft_skills": ["沟通", "协作"],
      "career_path": "岗位发展方向"
    },
    "high_freq_categories": {
      "title": "高频考点分类解析",
      "categories": [
        {
          "category": "基础知识",
          "description": "该维度考察重点说明",
          "questions": [
            {
              "question": "问题",
              "frequency": 5,
              "difficulty": "medium",
              "strategy": "应对策略",
              "key_points": ["要点1", "要点2"]
            }
          ]
        }
      ]
    },
    "high_freq_list": {
      "title": "高频考点清单及应对策略",
      "questions": [
        {
          "question": "具体问题",
          "frequency": 8,
          "answer_points": ["要点1", "要点2"],
          "example_answer": "示例回答（可选）",
          "pitfalls": ["常见错误1"]
        }
      ]
    },
    "project_deep_dive": {
      "title": "项目深挖",
      "projects": [
        {
          "project_name": "项目名称",
          "predicted_questions": [
            {
              "question": "追问1",
              "depth": "deep",
              "preparation_tips": "准备建议"
            }
          ],
          "tech_deep_dive": [
            {
              "tech": "技术点",
              "possible_questions": ["问题1", "问题2"]
            }
          ]
        }
      ],
      "general_tips": "项目介绍通用建议"
    },
    "behavioral_prep": {
      "title": "行为面试准备",
      "questions": [
        {
          "question": "HR常问问题",
          "framework": "STAR回答框架",
          "example": "示例回答"
        }
      ],
      "tips": "行为面试通用技巧"
    },
    "on_site_strategies": {
      "title": "临场应对策略",
      "pressure_handling": [
        "压力问题应对技巧1",
        "压力问题应对技巧2"
      ],
      "unknown_questions": [
        "不会回答时的应对技巧1",
        "不会回答时的应对技巧2"
      ],
      "communication_tips": [
        "沟通技巧1"
      ]
    },
    "recommended_resources": {
      "title": "推荐复习资料",
      "books": ["书名1", "书名2"],
      "websites": ["网站1", "网站2"],
      "courses": ["课程1"],
      "interview_exps": ["面经链接1"]
    }
  }
}
```

### 模块说明

| 模块 key | 模块名称 | 说明 |
|----------|----------|------|
| `overall_evaluation` | 整体评价 | 基于简历与岗位的匹配度总评，含简历修改建议 |
| `job_analysis` | 岗位分析 | 岗位核心要求、技术栈、软技能要求、发展方向 |
| `high_freq_categories` | 高频考点分类解析 | 按面试维度（基础、算法、项目、行为等）分类 |
| `high_freq_list` | 高频考点清单及应对策略 | 具体问题列表 + 回答要点 + 示例回答 |
| `project_deep_dive` | 项目深挖 | 针对简历项目的追问预测与准备建议（重中之重） |
| `behavioral_prep` | 行为面试准备 | HR终面常见问题及STAR回答框架 |
| `on_site_strategies` | 临场应对策略 | 压力问题、不会回答时的应对技巧 |
| `recommended_resources` | 推荐复习资料 | 书籍、网站、课程、面经链接等 |

### 展示规则
- 前端支持**模块独立查看**和**全部查看**两种模式
- 每个模块包含 `title` 字段用于前端展示
- 模块顺序按用户阅读习惯排列，不可跳过核心模块

# Vue 前端首版实现记录（2026-03-18）

## 目标

根据用户确认方案，建设毕业设计前端首版：

1. 技术栈：Vue3 + Vite
2. 双模式界面：
   - 研究模式（推理实验）
   - 运营模式（企业操作）
3. 代码模块化，便于后续二阶段接入真实业务接口

## 新增目录

- `web_frontend/`

主要结构：

- `web_frontend/src/App.vue`：全局壳和模式切换
- `web_frontend/src/modules/research/ResearchModeView.vue`：实验模式
- `web_frontend/src/modules/operations/OperationsModeView.vue`：运营模式
- `web_frontend/src/modules/shared/renderer.js`：统一轨迹绘制逻辑
- `web_frontend/src/services/api.js`：后端接口封装
- `web_frontend/src/styles.css`：全局样式

## 关键实现

### 1) 研究模式

- 保留完整推理参数表单
- 对接 `/api/defaults`、`/api/run-demo`
- 提供轨迹回放、进度滑条、日志和指标卡

### 2) 运营模式

- 面向操作员简化输入：模板选择 + 批次名 + 运行控制（开始/暂停/继续/停止）
- 强调“状态展示”：
  - 在线无人机数
  - 累计完成任务
  - 冲突告警数
  - 平均任务时延
- 支持地图点击给选中无人机快速设置目标点（企业操作流程核心）

### 3) 共享渲染模块

- 两种模式共用统一 Canvas 渲染器
- 智能体使用无人机图标绘制，目标与障碍语义保持一致

## 运行方式（开发态）

在 `web_frontend` 下执行：

```bash
npm install
npm run dev
```

默认通过 Vite 代理访问现有后端：

- `/api/*` -> `http://127.0.0.1:8090`

## 下一阶段建议

1. 运营模式接入真实任务队列与运行状态接口（替换示例数据）
2. 增加角色视图（管理员/访客）切换
3. 加入历史任务记录页与导出报表能力

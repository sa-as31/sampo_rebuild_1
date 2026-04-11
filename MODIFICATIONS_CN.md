# 项目修改说明（中文）

本文档记录我基于原始项目所做的主要修改，目标是让项目在 Docker/CPU 环境可稳定运行，并补充 GPU 入口。

## 1. 依赖与容器化

### 1.1 新增/补全依赖
- 文件：`requirements.txt`
- 主要内容：
  - 固定兼容版本：`numpy<2`、`gym==0.23.1`、`pydantic<2`
  - 补充训练与日志依赖：`torch`、`ray[tune]`、`wandb`、`tensorboard`、`tensorboardX`、`faster-fifo`、`threadpoolctl` 等

### 1.2 完成 Docker 构建流程
- 文件：`Dockerfile`
- 主要修改：
  - 基础镜像改为 `python:3.9-slim`
  - 安装 C++ 编译所需系统依赖（`build-essential`、`g++`、`libgl1`、`libglib2.0-0`）
  - 安装 Python 依赖 + `pybind11` + `cppimport`
  - 构建期预编译两个规划器扩展：
    - `planner.LB_A.planner`
    - `planner.Static_A.planner`

## 2. 论文相关功能补全

### 2.1 新增重规划算法模块
- 文件：
  - `planning/replan_algo.py`
  - `planning/__init__.py`
- 主要实现：
  - `RePlanBase`
  - `NoPathSoRandomOrStayWrapper`
  - `FixNonesWrapper`
- 核心思路：
  - 按论文思路加入拥堵相关代价建模（PlCC/PeCC），用于多智能体重规划与冲突缓解。

## 3. Sample Factory 兼容与运行修复

### 3.1 补全缺失空间类型
- 文件：
  - `sample_factory/algorithms/utils/spaces/discretized.py`
  - `sample_factory/algorithms/utils/spaces/__init__.py`
- 作用：补全 `Discretized`，修复动作空间导入与类型判断链路。

### 3.2 修复 APPO 相关运行问题
- 文件：
  - `sample_factory/algorithms/appo/model.py`
  - `sample_factory/algorithms/appo/model_utils.py`
  - `sample_factory/algorithms/appo/learner.py`
  - `sample_factory/algorithms/appo/policy_worker.py`
  - `sample_factory/algorithms/appo/appo.py`
- 主要修改：
  - 去除不可用导入（`create_atten_layer`）导致的启动问题
  - 修复部分硬编码 `.cuda()` 带来的 CPU 运行崩溃，改为设备自适应
  - 在 GPU 不可用时自动回退 CPU（主流程、learner、policy worker）
  - 为注意力模块缺省参数补充默认值（`num_heads`）

## 4. 新增 GPU 训练入口

- 文件：`main_gpu.py`
- 说明：
  - 逻辑与 `main.py` 基本一致
  - 默认强制 `global_settings.device = "gpu"`
  - 可通过命令行参数继续覆盖其余配置

## 5. 运行验证结果

已在 Docker 中完成如下验证：

1. CPU 主流程（`main.py`）
- 能完成初始化、采样、训练流程并正常退出（退出码 `0`）。

2. 较大规模 CPU 测试
- 使用 `num_workers=2`、`num_envs_per_worker=2`、`target_num_agents=256`、`num_agents=128` 测试通过（退出码 `0`）。

3. GPU 入口文件（`main_gpu.py`）
- 在无 CUDA 的容器中可正确启动，并触发自动回退到 CPU，流程可正常结束（退出码 `0`）。

## 6. 新增文档

- `README.md`：补充本地运行、Docker 运行、GPU 运行和常见问题说明。

## 7. Linux + NVIDIA 一键 GPU 链路补全

为满足“在 Linux + NVIDIA 环境一键直接跑”的目标，新增如下文件：

1. `Dockerfile.gpu`
- 基于 `nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04`
- 明确安装 CUDA 版 PyTorch（`torch==2.3.1` + `cu121`）
- 构建期预编译规划器扩展（LB_A / Static_A）

2. `docker-compose.gpu.yml`
- 提供独立 GPU compose 服务（`gpus: all`、`ipc: host`）
- 启动前先执行容器内 GPU 检查脚本，再运行 `main_gpu.py`

3. `scripts/verify_gpu.py`
- 在容器内校验：
  - `torch` 是否为 CUDA 构建
  - CUDA runtime 是否可用
  - 是否存在可见 GPU
- 失败会返回非 0 退出码，避免“误以为在 GPU 上训练”

## 8. Web 前端 UI 架构重构（重大更新）

为解决界面重点不清晰、跳转划分不清晰等问题，对 Vue 前端进行了全面重构：

1. **引入基于 `vue-router` 的多页面架构**：
- 安装并配置了 `vue-router@4`，摒弃了原有单一 `App.vue` 依靠大量 `v-if/v-else` 切换视图的冗余模式。
- 设置了基于角色的路由体系（`/admin/...`, `/requester/...`, `/executor/...`），页面层级和工作流一目了然。

2. **抽离公共布局与状态管理**：
- 提取 `src/views/AppShell.vue` 作为带有顶部导航和侧边栏的公共布局。
- 提取 `src/views/LoginView.vue` 单独负责登录逻辑。
- 创建了原生的轻量级状态管理 `src/stores/auth.js` 统一接管全局用户身份、登录状态与权限分发。

3. **视图跳转与视觉强化**：
- 对主要操作的 CSS (`.btn`, `.admin-task-card`) 增加了 `hover`、`active` 等具有阴影反馈和 Z 轴深度的交互效果，提升“视觉操作感”和美感。
- 引入了 `fade` 和 `fade-slide` 路由动画，实现无缝丝滑的视图切换体验。
- 重用原有 `TaskCenterView.vue` 强大的交互逻辑，通过路由 prop 的双向绑定实现细粒度的子模块切换（例如：`/admin/pending` 映射到 `create` 视图），既保障了业务稳定，又使页面 URL 可分享、可回退。

## 9. 文档补充：解释高风险删除命令 `rm -rf src/components src/assets`

1. `解疑.md`
- 新增关于 `rm -rf src/components src/assets` 的说明
- 明确该命令会递归强制删除：
  - `src/components`
  - `src/assets`
- 同步解释了 `rm -rf` 三部分参数的含义，以及为什么这类命令会被标记为高风险

## 10. 文档补充：解释为什么会出现删除 `src/components` 和 `src/assets` 的步骤

1. `解疑.md`
- 新增关于该删除命令“出现原因”的说明
- 结合截图中的上下文，说明这类命令通常出现在：
  - 新建 Vue + Vite 前端后
  - 清理默认脚手架内容
  - 准备整体重构页面结构之前
- 同时强调其意图通常是“清理旧结构，准备重建”，但前提必须是这些目录里的内容已确认不再需要

## 11. `web_frontend_ge` 前端重构续作（重大更新）

本轮继续完成上次未收尾的 `web_frontend_ge` 子项目重构，目标是把未完成的演示模板补齐为一套可直接展示的完整前端界面。

### 11.1 全局视觉系统与构建链路

- 文件：
  - `web_frontend_ge/src/styles/main.css`
  - `web_frontend_ge/src/App.vue`
  - `web_frontend_ge/vite.config.js`
- 主要修改：
  - 重新定义全局设计令牌，切换为暖白、低饱和、编辑式的视觉语言
  - 新增统一按钮、分段导航、指标卡、状态徽标、深色舞台等基础样式
  - 优化全局页面切换动效，保持丝滑但克制
  - 在 Vite 中接入 `@tailwindcss/vite` 插件，使样式链路更完整

### 11.2 补齐共享展示数据层

- 文件：
  - `web_frontend_ge/src/data/mockMissionData.js`
- 主要修改：
  - 新增统一的任务、舰队、扇区覆盖、维护队列、动态流等 mock 数据
  - 抽离 `getTaskById`、`getBoardColumns` 等辅助方法
  - 为 `Dashboard / TaskBoard / TaskDetail / FleetMonitor` 提供统一数据口径

### 11.3 重做布局壳层

- 文件：
  - `web_frontend_ge/src/layouts/AuthLayout.vue`
  - `web_frontend_ge/src/layouts/MainLayout.vue`
  - `web_frontend_ge/src/router/index.js`
- 主要修改：
  - 重构登录页外层布局，加入更柔和的背景氛围与转场
  - 重构主工作台布局，统一顶部命题区、信号摘要和分段导航
  - 为路由补充页面简介文案
  - 修复原本路由中引用了不存在页面的问题

### 11.4 继续完成未完成业务页面

- 文件：
  - `web_frontend_ge/src/views/LoginView.vue`
  - `web_frontend_ge/src/views/TaskDashboard.vue`
  - `web_frontend_ge/src/views/TaskBoard.vue`
  - `web_frontend_ge/src/views/TaskDetail.vue`
  - `web_frontend_ge/src/views/FleetMonitor.vue`
- 主要修改：
  - `LoginView`：
    - 从简单表单升级为展示型登录入口
    - 提供角色切换、演示账号预设和说明卡片
  - `TaskDashboard`：
    - 采用“大 Hero + 指标条 + 活跃任务舞台 + 动态流 + 系统节拍”结构
  - `TaskBoard`：
    - 支持看板/列表双视图
    - 增加按任务阶段切换的筛选条
  - `TaskDetail`：
    - 采用“深色运行舞台 + 右侧概览/参数/告警/回放面板”结构
    - 用路径锚点和进度条模拟任务运行主舞台
  - `FleetMonitor`：
    - 新增舰队观测页
    - 展示覆盖扇区、在线机组、维护队列与即将执行任务

### 11.5 验证结果

- 已执行：
  - `cd web_frontend_ge && npm run build`
- 结果：
  - 构建通过
  - 已通过浏览器实测关键路由：
    - `/login`
    - `/dashboard`
    - `/tasks`
    - `/tasks/T004`
    - `/fleet`

## 12. `web_frontend` 运营化前端重构（重大更新）

本轮继续围绕 `web_frontend` 主链路做运营化重构，目标是把页面从“说明型演示原型”收紧成更接近真实企业运营台的前端界面，同时修复现有构建阻塞。

### 12.1 登录页与应用壳层收紧

- 文件：
  - `web_frontend/src/views/LoginView.vue`

## 13. 新增毕业论文系统业务流程图素材

本轮为论文正文补充了一张可直接引用的“系统业务流程图”，重点表达当前项目在业务层面的完整执行链路，而不是底层算法训练细节。

### 13.1 新增流程图源文件与导出文件

- 文件：
  - `thesis_assets/diagrams/system_business_flow_diagram.drawio`
  - `thesis_assets/diagrams/system_business_flow_diagram.svg`
  - `thesis_assets/diagrams/system_business_flow_diagram.pdf`
  - `thesis_assets/diagrams/system_business_flow_diagram.png`
  - `thesis_assets/diagrams/system_business_flow_diagram_notes.md`
- 主要内容：
  - 使用论文常见流程图规范绘制业务主流程
  - 主干包含：登录、申请、审核、分配、执行、监控、回放评估、归档
  - 审核未通过时通过“退回修改”节点回到申请阶段
  - 图面统一为黑白灰低饱和风格，适合论文正文插图

### 13.2 补充论文可直接使用的图注与引用语句

- 文件：
  - `thesis_assets/diagrams/system_business_flow_diagram_notes.md`
  - `解疑.md`
- 主要内容：
  - 补充了建议图名：`图X 系统业务流程图`
  - 补充了正文引用语句
  - 补充了为什么本项目更适合绘制业务流程图的说明
  - `web_frontend/src/views/AppShell.vue`
  - `web_frontend/src/styles.css`
- 主要修改：
  - 登录页文案改为更偏系统入口和运营席位表达，压缩介绍口吻
  - 把账号提示与默认密码改成紧凑的状态胶囊，而不是连续说明文字
  - 顶部壳层新增工作台徽标，标题与简介改成更短、更产品化的页面命题
  - 调整头部、卡片、标签和面板的视觉层级，使全站更统一

### 12.2 三类角色工作台改为运营结构

- 文件：
  - `web_frontend/src/modules/taskcenter/TaskCenterView.vue`

## 14. 新增毕业论文概念ER图素材

本轮围绕“无人机动态路径规划系统”的论文表达需求，新增了一张 Chen 陈式概念 ER 图，用于在系统分析或系统设计章节中展示业务实体、属性与联系，而不是直接展示底层数据库物理结构。

### 14.1 新增 ER 图源文件与导出文件

- 文件：
  - `thesis_assets/diagrams/system_er_diagram.drawio`
  - `thesis_assets/diagrams/system_er_diagram.png`
  - `thesis_assets/diagrams/system_er_diagram.svg`
  - `thesis_assets/diagrams/system_er_diagram.pdf`
  - `thesis_assets/diagrams/system_er_diagram_notes.md`
- 主要内容：
  - 使用 Chen 陈式画法完成论文概念 ER 图
  - 以 `执行任务` 作为中心实体，向外关联 `用户`、`任务申请`、`地图环境`、`无人机`、`规划路径`、`运行告警`、`评估结果`
  - 对所有核心联系补充了 `1` / `N` 基数标注
  - 对所有主键属性添加了下划线标识
  - 图面采用低饱和蓝灰色系，兼顾论文可读性与页面观感

### 14.2 同步补充 ER 图设计依据与答疑记录

- 文件：
  - `解疑.md`
  - `thesis_assets/diagrams/system_er_diagram_notes.md`
- 主要内容：
  - 记录了为什么本项目优先使用“论文概念 ER 图”而非物理库表 ER 图
  - 记录了 8 个核心实体、7 条核心联系及其基数
  - 明确说明未纳入图中的实现层对象及原因，便于后续论文撰写时保持口径一致
  - `web_frontend/src/styles.css`
- 主要修改：
  - 管理员首页改成“审核 / 执行 / 归档”三类运营队列视图，移除教程式小字说明
  - 申请人首页改成“主表单 + 队列状态”结构，不再用“申请说明 / 当前流程 / 任务类别解释”占据首屏
  - 飞手首页补齐任务队列概览统计，强化待执行、执行中、已结束三类状态
  - 搜索和日期筛选重排为更紧凑的运营工具条
  - 任务卡片文案改成“标题 + 阶段 + 两行核心元信息”

### 12.3 任务详情页与运行舞台收紧

- 文件：
  - `web_frontend/src/modules/taskcenter/TaskDetailView.vue`
  - `web_frontend/src/modules/operations/OperationsModeView.vue`
  - `web_frontend/src/modules/dashboard/OpsDashboardView.vue`
  - `web_frontend/src/styles.css`
- 主要修改：
  - 任务详情页顶部新增任务状态摘要条，减少泛化说明
  - 回放区和执行区删除“这里用于查看……”等解释型文案，改为状态条、帧信息、节拍信息
  - 飞手页把“反馈”重命名为更偏运营语境的“记录”，提交按钮文案也同步收紧
  - 联合运行视图改为通过“参数已锁定 / 当前步 / 镜头 / 放大”等状态型标签表达当前上下文
  - 运营观测页把焦点任务、任务阶段和更新时间前置，列表文案更贴近真实监控台

### 12.4 构建阻塞修复

- 文件：
  - `web_frontend/src/modules/taskcenter/TaskDetailView.vue`
- 主要修改：
  - 删除重复声明的 `onImportMapFile`，修复此前导致 `vite build` 失败的脚本错误

### 12.5 验证结果

- 已执行：
  - `cd web_frontend && npm run build`
- 结果：
  - 构建通过
  - `TaskDetailView.vue` 的重复声明问题已修复

## 13. 顶栏标题进一步精简并压缩上半屏占比

- 文件：
  - `web_frontend/src/views/AppShell.vue`
  - `web_frontend/src/styles.css`
- 主要修改：
  - 将顶栏黑色大标题改为更短的单一主标题，避免长句占据首屏
  - 申请页大标题收紧为：`提交任务申请`
  - 其他页面同步改为简短标题：
    - `审核申请`
    - `执行调度`
    - `任务归档`
    - `我的申请`
    - `任务中心`
    - `运营观测`
    - `任务详情`
  - 非必要页面简介默认不再显示，只在申请页保留一行很短的辅助说明
  - 缩小顶栏整体高度：减少上下内边距、标题字号、页签外边距和账户区尺寸
  - 让页面上半部分更紧凑，避免首屏被大面积头部留白占满

## 14. 申请页移除统计区并转移到“我的申请”

- 文件：
  - `web_frontend/src/modules/taskcenter/TaskCenterView.vue`
  - `web_frontend/src/styles.css`
- 主要修改：
  - 删除申请人工作台顶部整块统计 Hero，避免“发起申请”页被状态区占据
  - 删除“发起申请”页右侧的申请队列统计侧栏，让该页只保留任务申请表单和提交预览
  - 将申请总数、待审核、已通过、已驳回以及“最近申请”统一移动到“我的申请”页中显示
  - 把申请页布局改为单列，使填写界面更干净、更聚焦

## 15. 发起申请后自动切换到“我的申请”

- 文件：
  - `web_frontend/src/modules/taskcenter/TaskCenterView.vue`
  - `web_frontend/src/modules/taskcenter/TaskDetailView.vue`
- 主要修改：
  - 修复“提交成功后看不到我的申请数据变动”的交互问题
  - 申请提交成功后，先刷新任务列表，再自动切换到 `我的申请`
  - 保留新创建任务的 `task_id` 作为当前选中项，进入历史页后直接看到刚提交的申请详情
  - 成功提示改为“已切换到我的申请”，让状态反馈更直接
  - 修复任务中心和任务详情页未正确读取当前登录用户的问题，避免 `我的申请` / `分配给我的任务` 因 `currentUser` 为空而筛选不到数据

## 16. 管理端顶部统计拆分为独立“总览”页

- 文件：
  - `web_frontend/src/router/index.js`
  - `web_frontend/src/views/AppShell.vue`
  - `web_frontend/src/modules/taskcenter/TaskCenterView.vue`
  - `web_frontend/src/styles.css`
- 主要修改：
  - 删除管理员工作页顶部原有的大面积统计 Hero，避免审核页一进入先被总览区占住
  - 新增独立页面 `总览`，承接原来的任务总数、执行中、已归档、待审核等统计信息
  - 管理员顶部分页调整为：
    - `总览`
    - `审核`
    - `执行`
    - `归档`
  - 将管理员页面切换改为真正的路由分页，避免标题、地址和内容不同步
  - 总览页改为紧凑卡片结构，并保留跳转到审核、执行、归档的快捷入口

## 17. 飞手页顶部统计迁入独立“总览”页

- 文件：
  - `web_frontend/src/router/index.js`
  - `web_frontend/src/views/AppShell.vue`
  - `web_frontend/src/modules/taskcenter/TaskCenterView.vue`
  - `web_frontend/src/modules/dashboard/OpsDashboardView.vue`
- 主要修改：
  - 删除飞手任务中心顶部原有的“我的任务队列”大统计区，避免任务页首屏被概览信息占满
  - 将飞手导航改为：
    - `总览`
    - `任务中心`
  - 新增飞手侧独立 `总览` 路由，原 `executor/dashboard` 兼容跳转到 `executor/overview`
  - 飞手总览改为只统计“分配给当前飞手”的任务，不再展示全局任务汇总
  - 总览卡片改为任务总数、待执行、执行中、已结束，并保留焦点任务和任务快照

## 18. 任务卡点击恢复跳转详情页

- 文件：
  - `web_frontend/src/modules/taskcenter/TaskCenterView.vue`
- 主要修改：
  - 修复飞手任务中心点击任务卡无跳转的问题
  - 修复申请人“我的申请”列表点击记录无跳转的问题
  - 将这两处点击行为从组件内 `selectTask` 改回路由跳转到 `/task/:id`
  - 跳转时保留角色和来源分页参数，确保详情页上下文正确

## 19. 默认任务节拍统一调整为 600 ms

- 文件：
  - `web_demo/task_runtime.py`
  - `web_frontend/src/modules/taskcenter/TaskCenterView.vue`
  - `web_frontend/src/modules/taskcenter/TaskDetailView.vue`
  - `web_frontend/src/modules/operations/OperationsModeView.vue`
  - `web_frontend/src/modules/shared/templateStore.js`
- 主要修改：
  - 将系统默认任务节拍从 `320 ms/步` 统一调整为 `600 ms/步`
  - 前端管理员创建/审核表单默认节拍改为 `600`
  - 联合运行视图中新建任务默认节拍改为 `600`
  - 模板读取与保存的默认节拍兜底改为 `600`
  - 后端任务创建、申请创建、任务恢复与参数归一化的默认节拍兜底统一改为 `600`

## 20. 修复“开始执行后 2D/3D 无动画”

- 文件：
  - `web_demo/task_runtime.py`
  - `web_frontend/src/modules/taskcenter/TaskDetailView.vue`
- 主要修改：
  - 去掉后端对未来 `scheduled_start_at` 的启动阻断，允许手动点击后立即进入运行态
  - 修复飞手与管理员详情页控制按钮状态，改为按任务阶段禁用无效动作
  - `READY` 仅允许开始，`RUNNING` 仅允许暂停/停止，`PAUSED` 仅允许继续/停止，终态全部禁用
  - 修复前端动作提示误导问题，不再只显示“操作已执行”，而是根据刷新后的真实任务状态反馈结果
  - 让详情页顶部状态与执行区提示统一基于实际状态，避免“提示成功但任务仍停留在待执行”

## 21. 新增论文系统用例图素材（2026-04-07）

本轮补充了可直接用于毕业论文的系统用例图，并保留了可编辑源文件，方便后续继续微调版式或文案。

### 21.1 新增图文件

- 文件：
  - `thesis_assets/diagrams/system_usecase_diagram.drawio`
  - `thesis_assets/diagrams/system_usecase_diagram.png`

### 21.2 图面内容

- 系统边界名称：
  - `多无人机协同调度与动态路径规划系统`
- 参与者：
  - 申请人
  - 管理员
  - 飞手
- 核心用例覆盖：
  - 登录系统
  - 提交任务申请
  - 查看申请状态
  - 查看任务回放/结果
  - 审核/创建任务
  - 分配执行者
  - 导入地图与模板
  - 监控任务运行
  - 处理反馈与告警
  - 复盘已完成任务
  - 查看运营大屏
  - 研究/推理配置
  - 查看分配任务
  - 任务启动/暂停/继续/停止
  - 查看 2D/3D 联合运行
  - 上报反馈与异常
  - 查看任务回放

### 21.3 生成方式

- 使用本机已安装的 `cli-anything-drawio` 创建和编辑 `.drawio` 源文件；
- 使用本机 `/Applications/draw.io.app` 的 CLI 导出高清 PNG；
- 导出参数以论文插图清晰度为目标，使用了较高缩放倍率并裁剪到图内容区域。

### 21.4 本次附带文档同步

- 文件：
  - `解疑.md`
- 主要补充：
  - 解释为什么论文用例图采用“申请人 / 管理员 / 飞手”三类参与者；
  - 解释本次用例图纳入的核心功能边界；
  - 记录新增图文件的存放位置和用途。

### 21.5 按 UML 规范二次整理图面

- 针对上一版用例图继续做了论文正式稿优化，重点是提升 UML 规范一致性与可读性。
- 主要调整：
  - 删除偏“页面入口”语义的用例：
    - `查看运营大屏`
    - `研究/推理配置`
  - 将部分名称收敛为更标准的动宾结构：
    - `查看任务回放/结果` -> `查看任务结果`
    - `审核/创建任务` -> `创建任务`
    - `导入地图与模板` -> `导入地图模板`
    - `处理反馈与告警` -> `处理任务告警`
    - `复盘已完成任务` -> `复盘任务执行`
    - `任务启动/暂停/继续/停止` -> `管理任务执行`
    - `查看2D/3D联合运行` -> `查看联合运行视图`
    - `上报反馈与异常` -> `提交异常反馈`
  - 删除冗余用例 `查看任务回放`，避免与 `查看任务结果` 语义重叠并增加线条交叉
  - 重新按“申请人区 / 管理员区 / 飞手区 / 共享登录”布局，用更少的用例覆盖更清晰的核心功能
- 结果：
  - 当前图面更贴近 UML 用例图命名规范；
  - 线条交叉和压线情况进一步减少；
  - 更适合作为毕业论文中的正式插图使用。

## 22. 在同步空间新增 `cli-anything-drawio` 使用说明（2026-04-11）

本轮按用户要求，在同步空间的 `tools` 目录中新增了一份关于 `drawio CLI` 的完整中文使用说明。

### 22.1 新增文件

- 文件：
  - `/Users/eller/Downloads/同步空间/tools/cli-anything-drawio-使用说明.md`

### 22.2 文档内容范围

- 主要覆盖：
  - 工具定位与适用场景
  - 安装方式与前置依赖
  - `cli-anything-drawio` 顶层命令结构
  - `project` 项目管理
  - `shape` 图形增删改查与样式设置
  - `connect` 连线与标签设置
  - `export` 导出图片、PDF、SVG、XML
  - `page` 多页管理
  - `session` 会话管理
  - `repl` 交互模式
  - UML 用例图典型写法
  - 论文绘图推荐导出参数
  - 常见问题与排查方法

### 22.3 命名与放置原因

- 文档放在同步空间的 `tools` 目录，是为了和现有工具说明集中放在一起，便于后续查阅和复用。
- 文件名采用 `cli-anything-drawio-使用说明.md`，与目录内已有的 `cli-anything-downkyi-使用说明.md` 风格保持一致。

### 22.4 本次附带同步

- 已将“drawio CLI 的使用方法和文档路径”同步补充进：
  - `解疑.md`

### 22.5 按 AI Agent 使用场景重写说明文档

- 用户进一步说明：这份教程主要是给 AI agent 编写，因此本轮对文档结构和措辞继续做了重写，不再只是普通用户手册。
- 主要调整：
  - 将文档定位明确为“面向 AI Agent 的操作规约”
  - 增加“最重要的规则”章节，强调：
    - 除 `project new` 外优先显式带 `--project`
    - 所有关键图元应显式设置 `--id`
    - 修改前先查，修改后再查
    - 不要假设图元、页码或项目状态
  - 增加“固定工作流”章节，明确从零绘图、修改已有图、只导出的推荐顺序
  - 增加“给 AI Agent 的 ID 命名规则”
  - 增加“给 AI Agent 的常见误判”
  - 增加“最小可靠模板”和“最后的执行原则”
- 结果：
  - 当前文档比上一版更适合 agent 直接照着执行；
  - 能明显降低因状态误判、ID 不稳定、导出前未检查等问题导致的失败概率。

## 23. 新增毕业论文规范化数据库ER图素材

本轮继续围绕论文数据库设计章节补充了一张“规范化数据库 ER 图”，重点不是复刻当前 SQLite 的物理实现，而是基于现有系统业务链路整理出更适合论文表达的关系型数据库设计方案。

### 23.1 新增数据库 ER 图源文件与导出文件

- 文件：
  - `thesis_assets/diagrams/system_database_er_diagram.drawio`
  - `thesis_assets/diagrams/system_database_er_diagram.png`
  - `thesis_assets/diagrams/system_database_er_diagram.svg`
  - `thesis_assets/diagrams/system_database_er_diagram.pdf`
  - `thesis_assets/diagrams/system_database_er_diagram_notes.md`
- 主要内容：
  - 使用数据库 ER 图风格绘制任务管理主链路
  - 以 `execution_tasks` 为中心表，关联 `task_requests`、`task_assignments`、`uavs`、`maps`、`planned_paths`、`task_alerts`、`task_feedback`、`task_results`
  - 通过 `PK` / `FK` 标识突出主外键关系
  - 用 `1:1`、`1:N`、`1:0..1` 标签表达主要基数

### 23.2 对真实 SQLite 结构做规范化重组

- 当前真实实现中的 `tasks + params_json` 被提升为论文中的规范化表设计：
  - `tasks` 拆分为 `task_requests` 与 `execution_tasks`
  - 新增 `task_assignments` 作为任务与无人机之间的分配中间表
  - 将申请人、地图、分配人、计划时间等信息改为结构化字段或显式外键
- 同时明确不把以下对象纳入主图核心版面：
  - `task_events`
  - `app_state`
  - 训练实验记录、模型权重、回放文件

### 23.3 同步补充论文说明与答疑记录

- 文件：
  - `解疑.md`
  - `thesis_assets/diagrams/system_database_er_diagram_notes.md`
- 主要内容：
  - 解释为什么数据库 ER 图不能直接照搬真实 SQLite 表
  - 给出从当前运行库到论文规范化设计的映射关系
  - 补充可直接用于论文的图名、正文引用语句、图注说明和表关系摘要

## 24. 论文概念ER图修订为“精简但更合理”版本

本轮对已有论文概念 ER 图做了克制型修订，重点吸收合理建模建议，但避免继续把概念图扩张成过重的分析图。

### 24.1 修订的核心方向

- 保留概念图服务论文正文的定位，不转向数据库图
- 对明显不合理的部分做收敛修正：
  - 将 `调度` 从普通联系升级为实体 `任务调度`
  - 将混合语义的 `审核分配` 改为单一语义的 `审批`
  - 将 `无人机` 的动态属性替换为稳定设备属性
- 不新增 `审批记录` 等更多实体，保持图面克制

### 24.2 更新后的图文件

- 文件：
  - `thesis_assets/diagrams/system_er_diagram.drawio`
  - `thesis_assets/diagrams/system_er_diagram.png`
  - `thesis_assets/diagrams/system_er_diagram.svg`
  - `thesis_assets/diagrams/system_er_diagram.pdf`
  - `thesis_assets/diagrams/system_er_diagram_notes.md`
- 主要修改：
  - 标题更新为“修订版”
  - 新增实体 `任务调度`
  - 删除旧关系 `用户 审核/分配 执行任务`
  - 删除旧关系 `执行任务 调度 无人机`
  - 新增关系 `任务申请 审批 执行任务`
  - 新增关系 `执行任务 关联 任务调度`
  - 新增关系 `无人机 参与 任务调度`

### 24.3 无人机属性归属修正

- 从 `无人机` 主实体中移除：
  - `当前位置`
  - `目标位置`
  - `运行状态`
- 替换为：
  - `无人机编号`
  - `无人机型号`
  - `最大载重`
  - `最大续航`
  - `设备状态`

### 24.4 文档同步

- 文件：
  - `解疑.md`
  - `thesis_assets/diagrams/system_er_diagram_notes.md`
- 主要内容：
  - 解释为什么“调度”需要实体化
  - 解释为什么不再使用“审核分配”这个混合词
  - 解释为什么无人机不再直接挂当前位置和目标位置

### 24.5 概念 ER 图连线样式修正

- 文件：
  - `thesis_assets/diagrams/system_er_diagram.drawio`
  - `thesis_assets/diagrams/system_er_diagram.png`
  - `thesis_assets/diagrams/system_er_diagram.svg`
  - `thesis_assets/diagrams/system_er_diagram.pdf`
- 主要修改：
  - 将概念 ER 图中的全部实体连线、属性连线和联系连线统一改为无箭头线条
  - 保持 Chen 概念模型的图面表达，不再使用带方向性的箭头视觉
  - 同步重新导出 PNG、SVG、PDF 版本，保证论文插图与源文件一致

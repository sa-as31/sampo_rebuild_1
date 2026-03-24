<template>
  <section v-if="isAdmin" class="admin-task-shell">
    <article class="panel admin-task-hero">
      <div>
        <p class="section-kicker">ADMIN WORKSPACE</p>
        <h2>管理员任务中心</h2>
        <p class="legend">管理员工作流收敛为三件事：创建任务、查看执行中任务、复盘已完成任务。</p>
      </div>
      <div class="admin-summary-row">
        <div class="status-card">
          <p>任务总数</p>
          <strong>{{ adminTaskStats.total }}</strong>
        </div>
        <div class="status-card">
          <p>执行中</p>
          <strong>{{ adminTaskStats.active }}</strong>
        </div>
        <div class="status-card">
          <p>已完成</p>
          <strong>{{ adminTaskStats.completed }}</strong>
        </div>
        <div class="status-card">
          <p>待审核申请</p>
          <strong>{{ adminTaskStats.pending }}</strong>
        </div>
      </div>
    </article>

    <nav class="admin-workspace-tabs">
      <button class="tab-btn" :class="{ active: adminSection === 'create' }" @click="adminSection = 'create'">申请审核</button>
      <button class="tab-btn" :class="{ active: adminSection === 'active' }" @click="adminSection = 'active'">执行中任务</button>
      <button class="tab-btn" :class="{ active: adminSection === 'completed' }" @click="adminSection = 'completed'">已完成任务</button>
    </nav>

    <section v-if="adminSection === 'create'" class="admin-workspace-grid admin-dispatch-grid">
      <article class="panel">
        <div class="admin-panel-head">
          <div>
            <h2>待审核任务申请</h2>
            <p class="legend">申请人提交指定时间、地点和任务类型后，由管理员在此审核并指派飞手。</p>
          </div>
          <button class="btn" @click="refreshTasks">刷新任务状态</button>
        </div>

        <div class="admin-overview-list">
          <button
            v-for="task in pendingReviewTasks"
            :key="task.task_id"
            class="admin-task-card"
            :class="{ active: task.task_id === selectedTaskId }"
            @click="selectTask(task.task_id)"
          >
            <span class="admin-task-card-top">
              <strong>{{ task.mission_name }}</strong>
              <em>{{ taskCategoryLabel(task.params?.task_category) }}</em>
            </span>
            <span class="admin-task-card-meta">{{ requesterLabel(task) }} · {{ task.params?.requested_location || task.params?.map_name || "-" }}</span>
            <span class="admin-task-card-meta">申请时间 {{ fmtDateTime(task.created_at) }} · 期望执行 {{ fmtDateTime(task.params?.scheduled_start_at) }}</span>
          </button>
          <div v-if="pendingReviewTasks.length === 0" class="ops-alert-empty">当前没有待审核申请。</div>
        </div>
      </article>

      <article class="panel">
        <div class="admin-panel-head">
          <div>
            <h2>审核与飞手指派</h2>
            <p class="legend">管理员审核申请后，选择飞手并确认执行参数，任务才会进入待执行。</p>
          </div>
        </div>

        <template v-if="selectedTask && selectedTask.status === 'PENDING_REVIEW'">
          <div class="task-meta-grid">
            <div class="task-meta"><span>申请人</span><strong>{{ requesterLabel(selectedTask) }}</strong></div>
            <div class="task-meta"><span>任务类别</span><strong>{{ taskCategoryLabel(selectedTask.params?.task_category) }}</strong></div>
            <div class="task-meta"><span>申请地点</span><strong>{{ selectedTask.params?.requested_location || "-" }}</strong></div>
            <div class="task-meta"><span>申请时间</span><strong>{{ fmtDateTime(selectedTask.params?.scheduled_start_at) }}</strong></div>
          </div>

          <div class="field-grid">
            <label>分配飞手
              <select v-model="assignForm.assignee_user_id" @change="syncAssigneeDisplayName">
                <option value="">请选择飞手</option>
                <option v-for="user in assignees" :key="user.user_id" :value="user.user_id">{{ user.display_name }} ({{ user.username }})</option>
              </select>
            </label>
            <label>执行数据源
              <select v-model="assignForm.source">
                <option value="sample">sample</option>
                <option value="model">model</option>
              </select>
            </label>
            <label>使用地图
              <select v-model="assignForm.map_name">
                <option v-for="item in availableMapChoices" :key="item.value" :value="item.value">{{ item.label }}</option>
              </select>
            </label>
            <label>执行时间
              <input v-model="assignForm.scheduled_start_input" type="datetime-local" />
            </label>
            <label>无人机数量
              <input v-model.number="assignForm.num_agents" min="1" type="number" />
            </label>
            <label>最大帧数
              <input v-model.number="assignForm.max_frames" min="4" type="number" />
            </label>
            <label>节拍(ms)
              <input v-model.number="assignForm.tick_ms" min="120" step="20" type="number" />
            </label>
            <label>审核备注
              <input v-model="assignForm.review_note" placeholder="可填写审核意见" />
            </label>
          </div>

          <div class="field-grid admin-map-import-grid">
            <label>导入地图(JSON)
              <input accept=".json,application/json" type="file" @change="onImportMapFile" />
            </label>
          </div>

          <div class="admin-highlight-card">
            <p>审核结果预览</p>
            <strong>{{ selectedTask.mission_name }}</strong>
            <span>{{ taskCategoryLabel(selectedTask.params?.task_category) }} · {{ selectedAssigneeLabel }} · {{ assignForm.map_name || "未选地图" }}</span>
            <span>计划开始：{{ scheduledPreviewText }}</span>
          </div>

          <div class="btn-row" style="margin-top: 12px">
            <button class="btn" @click="approveTaskRequest">审核通过并分配飞手</button>
            <button class="btn secondary" @click="rejectTaskRequest">驳回申请</button>
          </div>
          <div class="status-chip">{{ assignStatus }}</div>
        </template>
        <div v-else class="ops-alert-empty">请先从左侧选择一条待审核任务申请。</div>
      </article>
    </section>

    <section v-else-if="adminSection === 'active'" class="admin-workspace-grid admin-active-grid">
      <article class="panel">
        <div class="admin-panel-head">
          <div>
            <h2>执行中任务</h2>
            <p class="legend">只显示准备中、待开始、执行中、暂停中的任务，减少干扰。</p>
          </div>
          <button class="btn" @click="refreshTasks">刷新列表</button>
        </div>

        <label class="admin-search">
          <span>搜索任务</span>
          <input v-model="adminFilters.activeKeyword" placeholder="任务名 / task_id / 飞手" />
        </label>
        <label class="admin-search">
          <span>按日期筛选</span>
          <div class="date-picker-trigger" @click="openDatePicker(adminActiveDateInputRef)">
            <input
              ref="adminActiveDateInputRef"
              v-model="adminFilters.activeDate"
              class="date-picker-input"
              type="date"
              @keydown.prevent
              @beforeinput.prevent
            />
            <button class="date-picker-button" type="button" @click.stop="openDatePicker(adminActiveDateInputRef)">选择日期</button>
          </div>
        </label>

        <div class="admin-overview-list">
          <button
            v-for="task in filteredActiveTasks"
            :key="task.task_id"
            class="admin-task-card"
            :class="{ active: task.task_id === selectedTaskId }"
            @click="selectTask(task.task_id)"
          >
            <span class="admin-task-card-top">
              <strong>{{ task.mission_name }}</strong>
              <em>{{ taskStageLabel(task.status) }}</em>
            </span>
            <span class="admin-task-card-meta">{{ templateLabel(task.template) }} · {{ assigneeLabel(task) }} · 原始状态 {{ task.status }}</span>
            <span class="admin-task-card-meta">计划开始 {{ fmtDateTime(task.params?.scheduled_start_at) }}</span>
          </button>
          <div v-if="filteredActiveTasks.length === 0" class="ops-alert-empty">当前没有执行中任务。</div>
        </div>
      </article>

      <article class="panel">
        <div class="admin-panel-head">
          <div>
            <h2>任务实时详情</h2>
            <p class="legend">查看当前任务运行状态，并直接在当前任务页完成必要操作。</p>
          </div>
          <div class="btn-row">
            <button class="btn secondary" @click="runTaskAction('start')">立即开始</button>
            <button class="btn secondary" @click="runTaskAction('pause')">暂停</button>
            <button class="btn secondary" @click="runTaskAction('resume')">继续</button>
            <button class="btn secondary" @click="runTaskAction('stop')">停止</button>
          </div>
        </div>

        <div class="task-meta-grid">
          <div class="task-meta"><span>任务ID</span><strong>{{ selectedTask?.task_id || "-" }}</strong></div>
          <div class="task-meta"><span>任务状态</span><strong>{{ selectedTask?.status || "-" }}</strong></div>
          <div class="task-meta"><span>累计任务数</span><strong>{{ selectedSnapshot?.metrics?.tasks_completed ?? selectedTask?.metrics?.tasks_completed ?? "-" }}</strong></div>
          <div class="task-meta"><span>吞吐量</span><strong>{{ fmtNumber(selectedSnapshot?.metrics?.throughput ?? selectedTask?.metrics?.throughput, 4) }}</strong></div>
        </div>

        <div class="admin-detail-grid">
          <div class="admin-highlight-card compact">
            <p>调度信息</p>
            <strong>{{ selectedTask?.mission_name || "未选择任务" }}</strong>
            <span>{{ selectedTask ? `${assigneeLabel(selectedTask)} · ${selectedTask.params?.map_name || "-"}` : "从左侧列表选择任务" }}</span>
            <span>计划开始：{{ fmtDateTime(selectedTask?.params?.scheduled_start_at) }}</span>
          </div>
          <div class="admin-highlight-card compact">
            <p>当前状态</p>
            <strong>{{ selectedTask?.status || "-" }}</strong>
            <span>更新时间：{{ fmtDateTime(selectedTask?.updated_at) }}</span>
            <span>{{ status }}</span>
          </div>
        </div>

        <section class="admin-active-embedded" style="margin-top: 12px">
          <OperationsModeView embedded :current-user="currentUser" :focus-task-id="selectedTaskId" :role="props.role" />
        </section>
      </article>
    </section>

    <section v-else class="admin-workspace-grid admin-completed-grid">
      <article class="panel">
        <div class="admin-panel-head">
          <div>
            <h2>已完成任务</h2>
            <p class="legend">查看已完成、失败或停止的任务，并追踪告警和飞手反馈。</p>
          </div>
          <button class="btn" @click="refreshTasks">刷新历史</button>
        </div>

        <label class="admin-search">
          <span>搜索任务</span>
          <input v-model="adminFilters.completedKeyword" placeholder="任务名 / task_id / 飞手" />
        </label>
        <label class="admin-search">
          <span>按日期筛选</span>
          <div class="date-picker-trigger" @click="openDatePicker(adminCompletedDateInputRef)">
            <input
              ref="adminCompletedDateInputRef"
              v-model="adminFilters.completedDate"
              class="date-picker-input"
              type="date"
              @keydown.prevent
              @beforeinput.prevent
            />
            <button class="date-picker-button" type="button" @click.stop="openDatePicker(adminCompletedDateInputRef)">选择日期</button>
          </div>
        </label>

        <div class="admin-overview-list">
          <button
            v-for="task in filteredCompletedTasks"
            :key="task.task_id"
            class="admin-task-card"
            :class="{ active: task.task_id === selectedTaskId }"
            @click="selectTask(task.task_id)"
          >
            <span class="admin-task-card-top">
              <strong>{{ task.mission_name }}</strong>
              <em>{{ taskStageLabel(task.status) }}</em>
            </span>
            <span class="admin-task-card-meta">{{ assigneeLabel(task) }} · {{ fmtDateTime(task.ended_at || task.updated_at) }} · 原始状态 {{ task.status }}</span>
            <span class="admin-task-card-meta">系统告警 {{ selectedTaskId === task.task_id ? selectedAlerts.length : Number(task.metrics?.alerts || 0) }}</span>
          </button>
          <div v-if="filteredCompletedTasks.length === 0" class="ops-alert-empty">当前没有已完成任务。</div>
        </div>
      </article>

      <article class="panel">
        <div class="admin-panel-head">
          <div>
            <h2>复盘与问题记录</h2>
            <p class="legend">系统告警和飞手反馈分开展示，便于毕业设计中的问题复盘。</p>
          </div>
          <div class="btn-row">
            <button class="btn secondary" @click="loadReplay">加载历史回放</button>
            <button class="btn secondary" @click="togglePlayback">{{ replay.playing ? "暂停回放" : "播放回放" }}</button>
            <button class="btn secondary" @click="exportReport">导出任务报告</button>
          </div>
        </div>

        <div class="task-meta-grid">
          <div class="task-meta"><span>任务ID</span><strong>{{ selectedTask?.task_id || "-" }}</strong></div>
          <div class="task-meta"><span>任务状态</span><strong>{{ selectedTask?.status || "-" }}</strong></div>
          <div class="task-meta"><span>累计任务数</span><strong>{{ selectedSnapshot?.metrics?.tasks_completed ?? selectedTask?.metrics?.tasks_completed ?? "-" }}</strong></div>
          <div class="task-meta"><span>飞手反馈</span><strong>{{ selectedFeedback.length }}</strong></div>
        </div>

        <div class="admin-slider-row">
          <span>回放进度</span>
          <input
            v-model.number="replay.frameIndex"
            :max="Math.max(0, replay.frames.length - 1)"
            min="0"
            type="range"
            @input="drawReplayFrame"
          />
          <strong>{{ replay.frameIndex }}/{{ Math.max(0, replay.frames.length - 1) }}</strong>
        </div>

        <div class="ops-dual-view-grid history-dual-view-grid" style="margin-top: 10px">
          <section class="ops-view-card history-view-card">
            <h3>2D 历史回放</h3>
            <div class="legend">用于查看俯视轨迹、目标点和障碍布局</div>
            <div class="canvas-wrap history-canvas-wrap history-canvas-wrap-2d" style="margin-top: 8px">
              <canvas ref="historyCanvasRef" width="920" height="460"></canvas>
            </div>
          </section>
          <section class="ops-view-card history-view-card">
            <h3>3D 历史回放</h3>
            <div class="legend">与左侧使用同一任务、同一帧历史数据</div>
            <div class="canvas-wrap history-canvas-wrap history-canvas-wrap-3d" style="margin-top: 8px">
              <canvas ref="history3dCanvasRef" width="920" height="460"></canvas>
            </div>
          </section>
        </div>

        <div class="admin-recap-grid">
          <div class="ops-alerts">
            <h3>系统告警</h3>
            <div v-if="selectedAlerts.length === 0" class="ops-alert-empty">无告警记录</div>
            <div
              v-for="alert in selectedAlerts"
              :key="`${alert.ts}-${alert.code}`"
              class="ops-alert-item"
              :class="`level-${alert.level}`"
            >
              <span class="ops-alert-code">[{{ alert.code }}]</span>
              <span>{{ alert.message }}</span>
              <span class="ops-alert-step">step {{ alert.frame_step }}</span>
            </div>
          </div>

          <div class="ops-alerts">
            <h3>飞手反馈</h3>
            <div v-if="selectedFeedback.length === 0" class="ops-alert-empty">当前没有飞手反馈。</div>
            <div v-for="item in selectedFeedback" :key="`${item.created_at}-${item.username}-${item.message}`" class="feedback-item">
              <div class="feedback-head">
                <strong>{{ item.display_name || item.username || "未知用户" }}</strong>
                <span>{{ feedbackCategoryLabel(item.category) }}</span>
                <em>{{ fmtDateTime(item.created_at) }}</em>
              </div>
              <p>{{ item.message }}</p>
            </div>
          </div>
        </div>
      </article>
    </section>
  </section>

  <section v-else-if="isRequester" class="admin-task-shell">
    <article class="panel admin-task-hero">
      <div>
        <p class="section-kicker">REQUEST WORKSPACE</p>
        <h2>任务申请中心</h2>
        <p class="legend">申请人提交指定时间、地点和任务类型的无人机任务申请，等待管理员审核与飞手指派。</p>
      </div>
      <div class="admin-summary-row">
        <div class="status-card">
          <p>我的申请</p>
          <strong>{{ requesterTaskStats.total }}</strong>
        </div>
        <div class="status-card">
          <p>待审核</p>
          <strong>{{ requesterTaskStats.pending }}</strong>
        </div>
        <div class="status-card">
          <p>已通过</p>
          <strong>{{ requesterTaskStats.approved }}</strong>
        </div>
        <div class="status-card">
          <p>已驳回</p>
          <strong>{{ requesterTaskStats.rejected }}</strong>
        </div>
      </div>
    </article>

    <section class="admin-workspace-grid admin-dispatch-grid">
      <article class="panel">
        <div class="admin-panel-head">
          <div>
            <h2>提交无人机任务申请</h2>
            <p class="legend">填写任务名称、类别、地点和执行时间。提交后交由管理员审核。</p>
          </div>
        </div>

        <div class="field-grid">
          <label>任务名称
            <input v-model="requestForm.mission_name" placeholder="如：north_zone_patrol_request" />
          </label>
          <label>任务类别
            <select v-model="requestForm.task_category">
              <option value="patrol">巡逻</option>
              <option value="show">表演</option>
              <option value="transport">运输</option>
            </select>
          </label>
          <label>执行地点
            <input v-model="requestForm.requested_location" placeholder="如：北区 3 号楼天台 / 仓库 A 区" />
          </label>
          <label>申请执行时间
            <input v-model="requestForm.scheduled_start_input" type="datetime-local" />
          </label>
        </div>

        <div class="admin-highlight-card">
          <p>申请预览</p>
          <strong>{{ requestForm.mission_name }}</strong>
          <span>{{ taskCategoryLabel(requestForm.task_category) }} · {{ requestForm.requested_location || "未填写地点" }}</span>
          <span>申请执行时间：{{ requesterScheduledPreview }}</span>
        </div>

        <div class="btn-row" style="margin-top: 12px">
          <button class="btn" @click="submitTaskRequest">提交任务申请</button>
        </div>
        <div class="status-chip">{{ requestStatus }}</div>
      </article>

      <article class="panel">
        <div class="admin-panel-head">
          <div>
            <h2>我的申请记录</h2>
            <p class="legend">查看管理员审核状态、飞手指派情况和任务执行进展。</p>
          </div>
          <button class="btn" @click="refreshTasks">刷新列表</button>
        </div>

        <div class="admin-overview-list">
          <button
            v-for="task in requesterTasks"
            :key="task.task_id"
            class="admin-task-card"
            :class="{ active: task.task_id === selectedTaskId }"
            @click="selectTask(task.task_id)"
          >
            <span class="admin-task-card-top">
              <strong>{{ task.mission_name }}</strong>
              <em>{{ taskStageLabel(task.status) }}</em>
            </span>
            <span class="admin-task-card-meta">{{ taskCategoryLabel(task.params?.task_category) }} · {{ task.params?.requested_location || "-" }}</span>
            <span class="admin-task-card-meta">飞手：{{ assigneeLabel(task) }} · 时间 {{ fmtDateTime(task.params?.scheduled_start_at) }}</span>
          </button>
          <div v-if="requesterTasks.length === 0" class="ops-alert-empty">当前还没有提交任务申请。</div>
        </div>
      </article>
    </section>
  </section>

  <section v-else class="executor-task-shell" :class="{ 'detail-open': hasExecutorSelection }">
    <article class="panel executor-task-list">
      <div class="admin-panel-head">
        <div>
          <h2>任务中心</h2>
          <p class="legend">这里只显示分配给当前飞手的任务，选中后再进入任务执行页。</p>
        </div>
        <button class="btn" @click="refreshTasks">刷新列表</button>
      </div>

      <div class="field-grid">
        <label>状态筛选
          <select v-model="filters.status">
            <option value="ALL">全部</option>
            <option value="PREPARING">PREPARING</option>
            <option value="READY">READY</option>
            <option value="RUNNING">RUNNING</option>
            <option value="PAUSED">PAUSED</option>
            <option value="COMPLETED">COMPLETED</option>
            <option value="FAILED">FAILED</option>
            <option value="STOPPED">STOPPED</option>
          </select>
        </label>
        <label>模板筛选
          <select v-model="filters.template">
            <option value="ALL">全部</option>
            <option value="warehouse">仓储巡检</option>
            <option value="campus">园区配送</option>
            <option value="emergency">应急调度</option>
          </select>
        </label>
        <label>关键词
          <input v-model="filters.keyword" placeholder="任务名 / task_id" />
        </label>
        <label>按日期筛选
          <div class="date-picker-trigger" @click="openDatePicker(executorDateInputRef)">
            <input
              ref="executorDateInputRef"
              v-model="filters.date"
              class="date-picker-input"
              type="date"
              @keydown.prevent
              @beforeinput.prevent
            />
            <button class="date-picker-button" type="button" @click.stop="openDatePicker(executorDateInputRef)">选择日期</button>
          </div>
        </label>
      </div>

      <div class="status-chip">{{ status }}</div>
      <p class="legend">日期筛选规则：待执行看计划时间，执行中看计划/开始时间，已完成优先看完成时间。</p>

      <div class="executor-task-stack">
        <button
          v-for="task in filteredTasks"
          :key="task.task_id"
          class="admin-task-card"
          :class="{ active: task.task_id === selectedTaskId }"
          @click="selectTask(task.task_id)"
        >
          <span class="admin-task-card-top">
            <strong>{{ task.mission_name }}</strong>
            <em>{{ taskStageLabel(task.status) }}</em>
          </span>
          <span class="admin-task-card-meta">{{ templateLabel(task.template) }} · {{ fmtDateTime(task.params?.scheduled_start_at) }}</span>
          <span class="admin-task-card-meta">任务ID {{ task.task_id }}</span>
        </button>
        <div v-if="filteredTasks.length === 0" class="ops-alert-empty">当前没有分配给你的任务。</div>
      </div>
    </article>

    <article class="panel executor-task-detail" :class="{ visible: hasExecutorSelection }">
      <template v-if="selectedTask">
        <div class="admin-panel-head">
          <div>
            <h2>{{ selectedTask.mission_name }}</h2>
            <p class="legend">任务已进入执行页，联合运行、回放和反馈都在这里处理。</p>
          </div>
          <div class="btn-row">
            <button class="btn secondary" @click="exportReport">导出任务报告</button>
            <button class="btn secondary" @click="closeExecutorDetail">收起详情</button>
          </div>
        </div>

        <div class="task-meta-grid">
          <div class="task-meta"><span>任务ID</span><strong>{{ selectedTask.task_id }}</strong></div>
          <div class="task-meta"><span>任务阶段</span><strong>{{ taskStageLabel(selectedTask.status) }}</strong></div>
          <div class="task-meta"><span>计划开始</span><strong>{{ fmtDateTime(selectedTask.params?.scheduled_start_at) }}</strong></div>
          <div class="task-meta"><span>累计任务数</span><strong>{{ selectedSnapshot?.metrics?.tasks_completed ?? selectedTask?.metrics?.tasks_completed ?? "-" }}</strong></div>
        </div>

        <div class="admin-workspace-tabs" style="margin-top: 12px">
          <button class="tab-btn" :class="{ active: executorView === 'execute' }" @click="executorView = 'execute'">任务执行</button>
          <button class="tab-btn" :class="{ active: executorView === 'feedback' }" @click="executorView = 'feedback'">反馈与操作</button>
          <button class="tab-btn" :class="{ active: executorView === 'history' }" @click="executorView = 'history'">回放与告警</button>
        </div>

        <section v-if="executorView === 'execute'" class="executor-embedded-run">
          <div class="btn-row" style="margin-top: 12px">
            <button class="btn" @click="startAssignedTask">开始执行</button>
            <button class="btn secondary" @click="runTaskAction('pause')">暂停</button>
            <button class="btn secondary" @click="runTaskAction('resume')">继续</button>
            <button class="btn secondary" @click="runTaskAction('stop')">停止</button>
          </div>
          <div class="btn-row" style="margin-top: 10px">
            <button class="btn secondary" @click="setPilotTaskSpeed(1200)">演示减速</button>
            <button class="btn secondary" @click="setPilotTaskSpeed(700)">标准速度</button>
            <button class="btn secondary" @click="setPilotTaskSpeed(360)">加快一点</button>
          </div>
          <div class="legend" style="margin-top: 8px">
            当前飞行节拍：{{ selectedTask?.tick_ms || selectedTask?.params?.tick_ms || 320 }} ms/步
          </div>
          <div class="status-chip">{{ feedbackStatus }}</div>
          <OperationsModeView embedded :current-user="currentUser" :focus-task-id="selectedTaskId" :role="props.role" />
        </section>

        <section v-else-if="executorView === 'feedback'" class="executor-feedback-panel">
          <div class="admin-highlight-card compact">
            <p>当前任务</p>
            <strong>{{ selectedTask.mission_name }}</strong>
            <span>{{ taskStageLabel(selectedTask.status) }} · {{ fmtDateTime(selectedTask.params?.scheduled_start_at) }}</span>
          </div>

          <label class="login-label">
            反馈类型
            <select v-model="feedbackForm.category">
              <option value="issue">问题</option>
              <option value="risk">风险</option>
              <option value="note">备注</option>
            </select>
          </label>
          <label class="login-label">
            反馈内容
            <textarea v-model="feedbackForm.message" class="feedback-textarea" placeholder="例如：地图障碍与实际现场不一致，导致第 3 架无人机多次停滞。"></textarea>
          </label>

          <div class="btn-row" style="margin-top: 12px">
            <button class="btn secondary" @click="requestTaskDelay">申请延期</button>
            <button class="btn secondary" @click="reportTaskAnomaly">标记异常</button>
            <button class="btn" @click="submitExecutorFeedback">提交备注</button>
          </div>
          <div class="status-chip">{{ feedbackStatus }}</div>

          <div class="ops-alerts" style="margin-top: 12px">
            <h3>已提交反馈</h3>
            <div v-if="selectedFeedback.length === 0" class="ops-alert-empty">当前没有反馈记录。</div>
            <div v-for="item in selectedFeedback" :key="`${item.created_at}-${item.username}-${item.message}`" class="feedback-item">
              <div class="feedback-head">
                <strong>{{ item.display_name || item.username || "未知用户" }}</strong>
                <span>{{ feedbackCategoryLabel(item.category) }}</span>
                <em>{{ fmtDateTime(item.created_at) }}</em>
              </div>
              <p>{{ item.message }}</p>
            </div>
          </div>
        </section>

        <section v-else class="executor-history-panel">
          <div class="btn-row" style="margin-top: 12px">
            <button class="btn secondary" @click="loadReplay">加载历史回放</button>
            <button class="btn secondary" @click="togglePlayback">{{ replay.playing ? "暂停回放" : "播放回放" }}</button>
            <input
              v-model.number="replay.frameIndex"
              :max="Math.max(0, replay.frames.length - 1)"
              min="0"
              type="range"
              @input="drawReplayFrame"
            />
          </div>

          <div class="ops-dual-view-grid history-dual-view-grid" style="margin-top: 10px">
            <section class="ops-view-card history-view-card">
              <h3>2D 历史回放</h3>
              <div class="legend">查看任务轨迹、目标点和障碍分布</div>
              <div class="canvas-wrap history-canvas-wrap history-canvas-wrap-2d" style="margin-top: 8px">
                <canvas ref="executorHistoryCanvasRef" width="920" height="460"></canvas>
              </div>
            </section>
            <section class="ops-view-card history-view-card">
              <h3>3D 历史回放</h3>
              <div class="legend">与左侧使用同一帧历史任务数据</div>
              <div class="canvas-wrap history-canvas-wrap history-canvas-wrap-3d" style="margin-top: 8px">
                <canvas ref="executorHistory3dCanvasRef" width="920" height="460"></canvas>
              </div>
            </section>
          </div>

          <div class="ops-alerts" style="margin-top: 10px">
            <h3>任务告警</h3>
            <div v-if="selectedAlerts.length === 0" class="ops-alert-empty">无告警记录</div>
            <div
              v-for="alert in selectedAlerts"
              :key="`${alert.ts}-${alert.code}`"
              class="ops-alert-item"
              :class="`level-${alert.level}`"
            >
              <span class="ops-alert-code">[{{ alert.code }}]</span>
              <span>{{ alert.message }}</span>
              <span class="ops-alert-step">step {{ alert.frame_step }}</span>
            </div>
          </div>
        </section>
      </template>

      <template v-else>
        <div class="executor-empty-state">
          <p class="section-kicker">TASK DETAIL</p>
          <h2>选择一个任务进入执行页</h2>
          <p class="legend">左侧任务列表只负责展示任务。点选后，右侧会展开该任务的执行、反馈和回放界面。</p>
        </div>
      </template>
    </article>
  </section>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import OperationsModeView from "../operations/OperationsModeView.vue";
import {
  controlOpsTask,
  createOpsTask,
  fetchAuthOptions,
  fetchOpsAlerts,
  fetchOpsTasks,
  fetchTaskFeedback,
  fetchTaskReplay,
  getOpsTask,
  submitTaskFeedback,
} from "../../services/api";
import { createRenderer, drawScene3D, resizeCanvasToDisplaySize } from "../shared/renderer";

const TEMPLATE_MAP_OPTIONS = [
  { value: "warehouse-grid-v1", label: "仓储巡检默认地图", source: "template" },
  { value: "campus-road-v1", label: "园区配送默认地图", source: "template" },
  { value: "emergency-block-v1", label: "应急调度默认地图", source: "template" },
];

const ACTIVE_STATUSES = new Set(["PREPARING", "READY", "RUNNING", "PAUSED"]);
const FINAL_STATUSES = new Set(["COMPLETED", "FAILED", "STOPPED", "REJECTED"]);

const props = defineProps({
  role: {
    type: String,
    default: "executor",
  },
  currentUser: {
    type: Object,
    default: null,
  },
});

const renderer = createRenderer();
const liveCanvasRef = ref(null);
const historyCanvasRef = ref(null);
const history3dCanvasRef = ref(null);
const executorHistoryCanvasRef = ref(null);
const executorHistory3dCanvasRef = ref(null);
const executorDateInputRef = ref(null);
const adminActiveDateInputRef = ref(null);
const adminCompletedDateInputRef = ref(null);
const status = ref("任务中心初始化中...");
const assignStatus = ref("管理员可审核任务申请并分配飞手。");
const feedbackStatus = ref("飞手可以提交现场问题与备注。");
const requestStatus = ref("请填写任务时间、地点和类别后提交申请。");
const tasks = ref([]);
const selectedTaskId = ref("");
const selectedTask = ref(null);
const selectedSnapshot = ref(null);
const selectedAlerts = ref([]);
const selectedFeedback = ref([]);
const assignees = ref([]);
const importedMaps = ref(loadImportedMaps());
const replayTimer = ref(null);
const replayVisualTimer = ref(null);
const adminSection = ref("create");
let pollTimer = null;

const filters = reactive({
  status: "ALL",
  template: "ALL",
  keyword: "",
  date: "",
});

const adminFilters = reactive({
  activeKeyword: "",
  completedKeyword: "",
  activeDate: "",
  completedDate: "",
});

const assignForm = reactive({
  mission_name: "dispatch_batch_001",
  template: "warehouse",
  source: "sample",
  assignee_user_id: "",
  assignee_display_name: "",
  map_name: "warehouse-grid-v1",
  num_agents: 16,
  max_frames: 64,
  tick_ms: 320,
  scheduled_start_input: buildDefaultScheduleInput(),
  review_note: "",
});

const requestForm = reactive({
  mission_name: "north_zone_patrol_request",
  task_category: "patrol",
  requested_location: "北区 3 号楼天台",
  scheduled_start_input: buildDefaultScheduleInput(),
});

const feedbackForm = reactive({
  category: "issue",
  message: "",
});
const executorView = ref("execute");

const replay = reactive({
  available: false,
  frames: [],
  environment: null,
  frameIndex: 0,
  playing: false,
  reason: "",
});

const replayViewState = reactive({
  selectedDroneId: 0,
});

const isAdmin = computed(() => props.role === "admin");
const isRequester = computed(() => props.role === "requester");
const currentUserId = computed(() => props.currentUser?.user_id || "");
const currentUser = computed(() => props.currentUser);
const hasExecutorSelection = computed(() => !isAdmin.value && !!selectedTaskId.value && !!selectedTask.value);

const filteredTasks = computed(() => {
  const keyword = filters.keyword.trim().toLowerCase();
  return tasks.value.filter((task) => {
    if (!isAdmin.value) {
      const assignee = String(task?.params?.assignee_user_id || "");
      if (!assignee || assignee !== currentUserId.value) return false;
    }
    if (filters.status !== "ALL" && task.status !== filters.status) return false;
    if (filters.template !== "ALL" && task.template !== filters.template) return false;
    if (filters.date && !matchTaskDate(task, filters.date)) return false;
    if (!keyword) return true;
    return matchTaskKeyword(task, keyword);
  });
});

const availableMapChoices = computed(() => {
  const imported = importedMaps.value.map((item) => ({
    value: item.map_name,
    label: `${item.map_name}（已导入）`,
    source: "imported",
  }));
  const unique = new Map();
  [...imported, ...TEMPLATE_MAP_OPTIONS].forEach((item) => {
    if (!unique.has(item.value)) unique.set(item.value, item);
  });
  return Array.from(unique.values());
});

const selectedAssigneeLabel = computed(() => {
  const target = assignees.value.find((item) => item.user_id === assignForm.assignee_user_id);
  return target ? `${target.display_name}（${target.username}）` : "未指定飞手";
});

const scheduledPreviewText = computed(() => {
  const ts = parseScheduledInput(assignForm.scheduled_start_input);
  return ts ? fmtDateTime(ts) : "未设置";
});
const requesterScheduledPreview = computed(() => {
  const ts = parseScheduledInput(requestForm.scheduled_start_input);
  return ts ? fmtDateTime(ts) : "未设置";
});

const pendingReviewTasks = computed(() => tasks.value.filter((task) => task.status === "PENDING_REVIEW"));
const activeTasks = computed(() => tasks.value.filter((task) => ACTIVE_STATUSES.has(task.status)));
const completedTasks = computed(() => tasks.value.filter((task) => FINAL_STATUSES.has(task.status)));
const requesterTasks = computed(() =>
  tasks.value.filter((task) => String(task?.params?.requester_user_id || "") === currentUserId.value),
);

const filteredActiveTasks = computed(() => filterAdminTasks(activeTasks.value, adminFilters.activeKeyword, adminFilters.activeDate));
const filteredCompletedTasks = computed(() => filterAdminTasks(completedTasks.value, adminFilters.completedKeyword, adminFilters.completedDate));

const adminTaskStats = computed(() => ({
  total: tasks.value.length,
  active: activeTasks.value.length,
  completed: completedTasks.value.length,
  pending: pendingReviewTasks.value.length,
}));
const requesterTaskStats = computed(() => ({
  total: requesterTasks.value.length,
  pending: requesterTasks.value.filter((task) => task.status === "PENDING_REVIEW").length,
  approved: requesterTasks.value.filter((task) => ACTIVE_STATUSES.has(task.status) || task.status === "COMPLETED").length,
  rejected: requesterTasks.value.filter((task) => task.status === "REJECTED").length,
}));

function fmtNumber(value, digits = 2) {
  if (value == null || Number.isNaN(Number(value))) return "-";
  return Number(value).toFixed(digits);
}

function fmtTime(ts) {
  if (!ts) return "-";
  const d = new Date(Number(ts) * 1000);
  return `${d.getHours().toString().padStart(2, "0")}:${d.getMinutes().toString().padStart(2, "0")}:${d.getSeconds().toString().padStart(2, "0")}`;
}

function fmtDateTime(ts) {
  if (!ts) return "-";
  const d = new Date(Number(ts) * 1000);
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  const hh = String(d.getHours()).padStart(2, "0");
  const mi = String(d.getMinutes()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd} ${hh}:${mi}`;
}

function buildDefaultScheduleInput() {
  const d = new Date(Date.now() + 10 * 60 * 1000);
  d.setSeconds(0, 0);
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  const hh = String(d.getHours()).padStart(2, "0");
  const mi = String(d.getMinutes()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}T${hh}:${mi}`;
}

function parseScheduledInput(value) {
  if (!value) return null;
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return null;
  return Math.floor(parsed.getTime() / 1000);
}

function buildDateTimeLocalInput(ts) {
  if (!ts) return "";
  const d = new Date(Number(ts) * 1000);
  if (Number.isNaN(d.getTime())) return "";
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  const hh = String(d.getHours()).padStart(2, "0");
  const mi = String(d.getMinutes()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}T${hh}:${mi}`;
}

function templateLabel(key) {
  if (key === "campus") return "园区配送";
  if (key === "emergency") return "应急调度";
  return "仓储巡检";
}

function taskCategoryLabel(value) {
  if (value === "show") return "表演";
  if (value === "transport") return "运输";
  return "巡逻";
}

function assigneeLabel(task) {
  const params = task?.params || {};
  return params.assignee_display_name || params.assignee_user_id || "待分配";
}

function requesterLabel(task) {
  const params = task?.params || {};
  return params.requester_display_name || params.requester_username || "-";
}

function feedbackCategoryLabel(category) {
  if (category === "delay_request") return "延期申请";
  if (category === "anomaly") return "异常上报";
  if (category === "risk") return "风险";
  if (category === "note") return "备注";
  return "问题";
}

function taskStageLabel(status) {
  const value = String(status || "").toUpperCase();
  if (value === "PENDING_REVIEW") return "待审核";
  if (value === "REJECTED") return "已驳回";
  if (["PREPARING", "READY"].includes(value)) return "待执行";
  if (["RUNNING", "PAUSED"].includes(value)) return "执行中";
  return "已完成";
}

function matchTaskKeyword(task, keyword) {
  return [
    task.task_id,
    task.mission_name,
    assigneeLabel(task),
    task.params?.map_name,
  ]
    .filter(Boolean)
    .some((value) => String(value).toLowerCase().includes(keyword));
}

function filterAdminTasks(list, keyword, dateValue) {
  const normalized = String(keyword || "").trim().toLowerCase();
  return list.filter((task) => {
    if (dateValue && !matchTaskDate(task, dateValue)) return false;
    if (!normalized) return true;
    return matchTaskKeyword(task, normalized);
  });
}

function matchTaskDate(task, dateValue) {
  if (!dateValue) return true;
  const candidates = collectTaskDateCandidates(task);
  return candidates.some((candidate) => formatDateOnly(candidate) === dateValue);
}

function collectTaskDateCandidates(task) {
  const status = String(task?.status || "").toUpperCase();
  const params = task?.params || {};
  const rawCandidates = [];

  if (["COMPLETED", "FAILED", "STOPPED"].includes(status)) {
    rawCandidates.push(task?.ended_at, task?.updated_at, params?.scheduled_start_at, task?.created_at);
  } else if (["RUNNING", "PAUSED"].includes(status)) {
    rawCandidates.push(params?.scheduled_start_at, task?.started_at, task?.created_at, task?.updated_at);
  } else {
    rawCandidates.push(params?.scheduled_start_at, task?.created_at, task?.updated_at);
  }

  return rawCandidates
    .map((value) => Number(value || 0))
    .filter((value, index, list) => value > 0 && list.indexOf(value) === index);
}

function formatDateOnly(ts) {
  if (!ts) return "";
  const d = new Date(Number(ts) * 1000);
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

function openDatePicker(inputRef) {
  const input = inputRef?.value;
  if (!input) return;
  if (typeof input.showPicker === "function") {
    input.showPicker();
    return;
  }
  input.focus();
  input.click();
}

function ensureVersionedMapName(baseName) {
  const normalized = String(baseName || "imported-map").trim() || "imported-map";
  const existing = new Set(importedMaps.value.map((item) => item.map_name));
  if (!existing.has(normalized)) return normalized;
  let version = 2;
  while (existing.has(`${normalized}-v${version}`)) version += 1;
  return `${normalized}-v${version}`;
}

function loadImportedMaps() {
  try {
    const raw = window.localStorage.getItem("OPS_IMPORTED_MAPS");
    const parsed = JSON.parse(raw || "[]");
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function saveImportedMaps() {
  window.localStorage.setItem("OPS_IMPORTED_MAPS", JSON.stringify(importedMaps.value.slice(-20)));
}

function drawEmptyCanvas(canvas, message) {
  if (!canvas) return;
  resizeCanvasToDisplaySize(canvas);
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = "#061327";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = "rgba(205,225,255,0.84)";
  ctx.font = '15px "PingFang SC", "Noto Sans SC", sans-serif';
  ctx.textAlign = "center";
  ctx.fillText(message, canvas.width / 2, canvas.height / 2);
}

function drawTaskSnapshotTo(canvas) {
  if (selectedSnapshot.value?.environment && selectedSnapshot.value?.frame && canvas) {
    resizeCanvasToDisplaySize(canvas);
    renderer.draw(canvas, selectedSnapshot.value.environment, selectedSnapshot.value.frame);
    return;
  }
  drawEmptyCanvas(canvas, "暂无实时任务画面");
}

async function refreshAssignees() {
  if (!isAdmin.value) return;
  try {
    const payload = await fetchAuthOptions();
    assignees.value = (payload?.accounts || []).filter((item) => item.role === "executor");
    if (!assignForm.assignee_user_id && assignees.value.length) {
      assignForm.assignee_user_id = assignees.value[0].user_id;
      assignForm.assignee_display_name = assignees.value[0].display_name;
    }
  } catch (error) {
    assignStatus.value = `飞手列表加载失败：${error.message}`;
  }
}

async function refreshTasks() {
  try {
    const data = await fetchOpsTasks(100);
    tasks.value = data.tasks || [];
    ensureSelectedTask();
    if (selectedTaskId.value) {
      await loadTaskDetail(selectedTaskId.value, false);
    } else {
      selectedTask.value = null;
      selectedSnapshot.value = null;
      selectedAlerts.value = [];
      selectedFeedback.value = [];
    }
    if (isAdmin.value) {
      status.value = `任务已刷新：待审核 ${pendingReviewTasks.value.length}，执行中 ${activeTasks.value.length}，已完成 ${completedTasks.value.length}`;
    } else if (isRequester.value) {
      status.value = `申请列表已更新：待审核 ${requesterTaskStats.value.pending}，已通过 ${requesterTaskStats.value.approved}`;
    } else {
      status.value = `任务列表已更新，可见 ${filteredTasks.value.length} 条（总 ${tasks.value.length} 条）`;
    }
  } catch (error) {
    status.value = `刷新失败：${error.message}`;
  }
}

function ensureSelectedTask() {
  const pool = isAdmin.value ? tasks.value : isRequester.value ? requesterTasks.value : filteredTasks.value;
  if (pool.some((task) => task.task_id === selectedTaskId.value)) return;
  if (isAdmin.value) {
    selectedTaskId.value =
      pendingReviewTasks.value[0]?.task_id ||
      activeTasks.value[0]?.task_id ||
      completedTasks.value[0]?.task_id ||
      tasks.value[0]?.task_id ||
      "";
    return;
  }
  if (isRequester.value) {
    selectedTaskId.value = requesterTasks.value[0]?.task_id || "";
    return;
  }
  selectedTaskId.value = "";
  selectedTask.value = null;
  selectedSnapshot.value = null;
  selectedAlerts.value = [];
  selectedFeedback.value = [];
  stopReplayTimer();
  stopReplayVisualTimer();
  drawEmptyCanvas(liveCanvasRef.value, "请选择左侧任务以展开执行详情");
}

async function selectTask(taskId) {
  stopReplayTimer();
  replay.available = false;
  replay.frames = [];
  replay.environment = null;
  replay.frameIndex = 0;
  replay.reason = "";
  selectedTaskId.value = taskId;
  if (!isAdmin.value) executorView.value = "execute";
  await loadTaskDetail(taskId, true);
}

function closeExecutorDetail() {
  if (isAdmin.value) return;
  selectedTaskId.value = "";
  selectedTask.value = null;
  selectedSnapshot.value = null;
  selectedAlerts.value = [];
  selectedFeedback.value = [];
  stopReplayTimer();
  stopReplayVisualTimer();
  drawEmptyCanvas(liveCanvasRef.value, "请选择左侧任务以展开执行详情");
  drawEmptyCanvas(executorHistoryCanvasRef.value, "请选择左侧任务以查看历史回放");
  drawEmptyCanvas(executorHistory3dCanvasRef.value, "请选择左侧任务以查看历史回放");
  status.value = `任务列表已更新，可见 ${filteredTasks.value.length} 条（总 ${tasks.value.length} 条）`;
}

async function loadTaskDetail(taskId, withStatusText) {
  try {
    const [detail, alerts, feedback] = await Promise.all([
      getOpsTask(taskId),
      fetchOpsAlerts(taskId, 30),
      fetchTaskFeedback(taskId, 30),
    ]);
    selectedTask.value = detail.task || null;
    selectedSnapshot.value = detail.snapshot || null;
    selectedAlerts.value = alerts.alerts || [];
    selectedFeedback.value = feedback.feedback || [];
    if (isAdmin.value && adminSection.value === "create" && selectedTask.value?.status === "PENDING_REVIEW") {
      syncReviewFormFromTask(selectedTask.value);
    }
    if (withStatusText) status.value = `已加载任务：${taskId}`;
    await nextTick();
    drawTaskSnapshotTo(liveCanvasRef.value);
    if (isAdmin.value && adminSection.value === "completed") {
      await loadReplay({ silent: true });
      drawReplayFrame();
    }
  } catch (error) {
    status.value = `加载任务失败：${error.message}`;
  }
}

async function loadReplay(options = {}) {
  const { silent = false } = options;
  if (!selectedTaskId.value) {
    if (!silent) status.value = "请先选择一个任务";
    return;
  }
  stopReplayTimer();
  try {
    const payload = await fetchTaskReplay(selectedTaskId.value);
    replay.available = Boolean(payload.available);
    replay.frames = payload.frames || [];
    replay.environment = payload.environment || null;
    replay.frameIndex = 0;
    replay.reason = payload.reason || "";
    await nextTick();
    if (!replay.available || !replay.frames.length || !replay.environment) {
      if (!silent) status.value = replay.reason || "当前任务无法提供历史回放";
      drawReplayFrame();
      ensureReplayVisualTimer();
      return;
    }
    if (!silent) status.value = `历史回放已加载，帧数 ${replay.frames.length}`;
    drawReplayFrame();
    ensureReplayVisualTimer();
  } catch (error) {
    if (!silent) status.value = `加载回放失败：${error.message}`;
  }
}

function drawReplayFrame() {
  const canvases = getReplayCanvasTargets();
  if (replay.available && replay.environment && replay.frames.length) {
    const frame = replay.frames[Math.min(replay.frameIndex, replay.frames.length - 1)];
    syncReplaySelectedDrone(frame);
    if (canvases.canvas2d) {
      resizeCanvasToDisplaySize(canvases.canvas2d);
      renderer.draw(canvases.canvas2d, replay.environment, frame);
    }
    if (canvases.canvas3d) {
      drawScene3D(canvases.canvas3d, replay.environment, frame, {
        cameraMode: "orbit",
        zoomScale: 1,
        orbitAngle: replay.frameIndex * 0.14,
        selectedDroneId: replayViewState.selectedDroneId,
      });
    }
    return;
  }
  if (selectedSnapshot.value?.environment && selectedSnapshot.value?.frame) {
    syncReplaySelectedDrone(selectedSnapshot.value.frame);
    if (canvases.canvas2d) {
      resizeCanvasToDisplaySize(canvases.canvas2d);
      renderer.draw(canvases.canvas2d, selectedSnapshot.value.environment, selectedSnapshot.value.frame);
    }
    if (canvases.canvas3d) {
      drawScene3D(canvases.canvas3d, selectedSnapshot.value.environment, selectedSnapshot.value.frame, {
        cameraMode: "orbit",
        zoomScale: 1,
        orbitAngle: 0.2,
        selectedDroneId: replayViewState.selectedDroneId,
      });
    }
    return;
  }
  if (canvases.canvas2d) drawEmptyCanvas(canvases.canvas2d, "暂无可展示回放");
  if (canvases.canvas3d) drawEmptyCanvas(canvases.canvas3d, "暂无可展示回放");
}

function getReplayCanvasTargets() {
  if (isAdmin.value) {
    return {
      canvas2d: historyCanvasRef.value || liveCanvasRef.value,
      canvas3d: history3dCanvasRef.value || null,
    };
  }
  return {
    canvas2d: executorHistoryCanvasRef.value || liveCanvasRef.value,
    canvas3d: executorHistory3dCanvasRef.value || null,
  };
}

function syncReplaySelectedDrone(frame) {
  const agents = frame?.agents || [];
  if (!agents.length) {
    replayViewState.selectedDroneId = 0;
    return;
  }
  if (!agents.some((agent) => agent.id === replayViewState.selectedDroneId)) {
    replayViewState.selectedDroneId = agents[0].id;
  }
}

async function togglePlayback() {
  if (replay.playing) {
    stopReplayTimer();
    return;
  }
  if (!replay.available || !replay.frames.length) {
    await loadReplay({ silent: true });
    if (!replay.available || !replay.frames.length) {
      status.value = replay.reason || "请先加载历史回放";
      return;
    }
  }
  replay.playing = true;
  replayTimer.value = window.setInterval(() => {
    if (replay.frameIndex >= replay.frames.length - 1) {
      stopReplayTimer();
      return;
    }
    replay.frameIndex += 1;
    drawReplayFrame();
  }, 220);
}

function stopReplayTimer() {
  replay.playing = false;
  if (replayTimer.value) {
    window.clearInterval(replayTimer.value);
    replayTimer.value = null;
  }
}

function shouldAnimateReplayCanvas() {
  if (isAdmin.value) return adminSection.value === "completed" && !!selectedTaskId.value;
  if (isRequester.value) return false;
  return executorView.value === "history" && !!selectedTaskId.value;
}

function ensureReplayVisualTimer() {
  if (!shouldAnimateReplayCanvas()) {
    stopReplayVisualTimer();
    return;
  }
  if (replayVisualTimer.value) return;
  replayVisualTimer.value = window.setInterval(() => {
    drawReplayFrame();
  }, 140);
}

function stopReplayVisualTimer() {
  if (replayVisualTimer.value) {
    window.clearInterval(replayVisualTimer.value);
    replayVisualTimer.value = null;
  }
}

function exportReport() {
  if (!selectedTask.value) {
    status.value = "请先选择一个任务";
    return;
  }
  const task = selectedTask.value;
  const metrics = selectedSnapshot.value?.metrics || task.metrics || {};
  const lines = [
    `# 任务报告`,
    ``,
    `- 任务ID: ${task.task_id}`,
    `- 任务名: ${task.mission_name}`,
    `- 模板: ${templateLabel(task.template)}`,
    `- 数据源: ${task.source}`,
    `- 状态: ${task.status}`,
    `- 飞手: ${assigneeLabel(task)}`,
    `- 地图: ${task.params?.map_name || "-"}`,
    `- 计划开始: ${fmtDateTime(task.params?.scheduled_start_at)}`,
    `- 创建时间: ${fmtDateTime(task.created_at)}`,
    `- 更新时间: ${fmtDateTime(task.updated_at)}`,
    ``,
    `## 核心指标`,
    `- 在线无人机数: ${metrics.online ?? "-"}`,
    `- 累计完成任务数: ${metrics.tasks_completed ?? "-"}`,
    `- 吞吐量: ${fmtNumber(metrics.throughput, 4)}`,
    `- 累计冲突数: ${metrics.cumulative_conflicts ?? metrics.vertex_conflicts ?? "-"}`,
    `- 平均时延(步): ${metrics.avg_latency ?? "-"}`,
    ``,
    `## 系统告警`,
  ];
  if (!selectedAlerts.value.length) {
    lines.push("- 无告警");
  } else {
    selectedAlerts.value.forEach((alert) => {
      lines.push(`- [${alert.level}] ${alert.code} | step ${alert.frame_step} | ${alert.message}`);
    });
  }
  lines.push("", "## 飞手反馈");
  if (!selectedFeedback.value.length) {
    lines.push("- 无反馈");
  } else {
    selectedFeedback.value.forEach((item) => {
      lines.push(`- [${feedbackCategoryLabel(item.category)}] ${item.display_name || item.username} | ${fmtDateTime(item.created_at)} | ${item.message}`);
    });
  }

  const blob = new Blob([lines.join("\n")], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `task-report-${task.task_id}.md`;
  a.click();
  URL.revokeObjectURL(url);
  status.value = `已导出报告：task-report-${task.task_id}.md`;
}

function syncAssigneeDisplayName() {
  const target = assignees.value.find((item) => item.user_id === assignForm.assignee_user_id);
  assignForm.assignee_display_name = target?.display_name || "";
}

function syncReviewFormFromTask(task) {
  const params = task?.params || {};
  assignForm.assignee_user_id = String(params.assignee_user_id || "");
  syncAssigneeDisplayName();
  assignForm.source = task?.source || "sample";
  assignForm.map_name = String(params.map_name || params.requested_location || "warehouse-grid-v1");
  assignForm.num_agents = Number(params.num_agents || 16);
  assignForm.max_frames = Number(params.max_frames || 64);
  assignForm.tick_ms = Number(task?.tick_ms || 320);
  assignForm.scheduled_start_input = buildDateTimeLocalInput(params.scheduled_start_at) || buildDefaultScheduleInput();
  assignForm.review_note = String(params.review_note || "");
}

async function createAndAssignTask() {
  if (!isAdmin.value) {
    assignStatus.value = "仅管理员可创建和分配任务";
    return;
  }
  if (!assignForm.assignee_user_id) {
    assignStatus.value = "请先选择飞手";
    return;
  }
  const scheduledStartAt = parseScheduledInput(assignForm.scheduled_start_input);
  if (!scheduledStartAt) {
    assignStatus.value = "请设置有效的计划执行时间";
    return;
  }
  syncAssigneeDisplayName();
  try {
    const created = await createOpsTask({
      mission_name: assignForm.mission_name,
      template: assignForm.template,
      source: assignForm.source,
      map_name: assignForm.map_name,
      num_agents: assignForm.num_agents,
      max_frames: assignForm.max_frames,
      tick_ms: assignForm.tick_ms,
      assignee_user_id: assignForm.assignee_user_id,
      assignee_display_name: assignForm.assignee_display_name,
      scheduled_start_at: scheduledStartAt,
      scheduled_start_label: fmtDateTime(scheduledStartAt),
    });
    selectedTaskId.value = created?.task?.task_id || "";
    await refreshTasks();
    assignStatus.value = `任务已分配给 ${assignForm.assignee_display_name}，计划于 ${fmtDateTime(scheduledStartAt)} 执行`;
  } catch (error) {
    assignStatus.value = `任务创建失败：${error.message}`;
  }
}

async function approveTaskRequest() {
  if (!selectedTaskId.value || selectedTask.value?.status !== "PENDING_REVIEW") {
    assignStatus.value = "请先选择待审核申请";
    return;
  }
  if (!assignForm.assignee_user_id) {
    assignStatus.value = "请先选择飞手";
    return;
  }
  const scheduledStartAt = parseScheduledInput(assignForm.scheduled_start_input);
  syncAssigneeDisplayName();
  try {
    await controlOpsTask(selectedTaskId.value, "approve", {
      assignee_user_id: assignForm.assignee_user_id,
      assignee_display_name: assignForm.assignee_display_name,
      source: assignForm.source,
      map_name: assignForm.map_name,
      num_agents: assignForm.num_agents,
      max_frames: assignForm.max_frames,
      tick_ms: assignForm.tick_ms,
      scheduled_start_at: scheduledStartAt,
      scheduled_start_label: scheduledStartAt ? fmtDateTime(scheduledStartAt) : "",
      review_note: assignForm.review_note,
    });
    await refreshTasks();
    assignStatus.value = `审核通过，已为 ${selectedTask.value?.mission_name || "该任务"} 指派飞手 ${assignForm.assignee_display_name}`;
    adminSection.value = "active";
  } catch (error) {
    assignStatus.value = `审核通过失败：${error.message}`;
  }
}

async function rejectTaskRequest() {
  if (!selectedTaskId.value || selectedTask.value?.status !== "PENDING_REVIEW") {
    assignStatus.value = "请先选择待审核申请";
    return;
  }
  try {
    await controlOpsTask(selectedTaskId.value, "reject", {
      review_note: assignForm.review_note,
    });
    await refreshTasks();
    assignStatus.value = "申请已驳回。";
  } catch (error) {
    assignStatus.value = `驳回失败：${error.message}`;
  }
}

async function runTaskAction(action) {
  if (!selectedTaskId.value) {
    status.value = "请先选择任务";
    return;
  }
  try {
    await controlOpsTask(selectedTaskId.value, action);
    await refreshTasks();
    status.value = `任务操作已执行：${action}`;
  } catch (error) {
    status.value = `任务操作失败：${error.message}`;
  }
}

function onImportMapFile(event) {
  if (!isAdmin.value) return;
  const file = event?.target?.files?.[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = () => {
    try {
      const parsed = JSON.parse(String(reader.result || "{}"));
      const rawMapName = String(parsed.map_name || file.name.replace(/\.[^.]+$/, "") || "imported-map");
      const mapName = ensureVersionedMapName(rawMapName);
      const item = {
        id: `${Date.now()}-${Math.random().toString(16).slice(2, 8)}`,
        map_name: mapName,
        file_name: file.name,
        ts: Date.now() / 1000,
      };
      importedMaps.value = [item, ...importedMaps.value].slice(0, 20);
      saveImportedMaps();
      assignForm.map_name = mapName;
      assignStatus.value = `地图已导入：${mapName}`;
    } catch (error) {
      assignStatus.value = `地图导入失败：${error.message}`;
    }
  };
  reader.readAsText(file, "utf-8");
}

function applyImportedMap(item) {
  assignForm.map_name = item.map_name;
  assignStatus.value = `已选择地图：${item.map_name}`;
}

async function submitExecutorFeedback() {
  if (!selectedTaskId.value) {
    feedbackStatus.value = "请先选择一个任务";
    return;
  }
  if (!feedbackForm.message.trim()) {
    feedbackStatus.value = "请先填写反馈内容";
    return;
  }
  try {
    await submitTaskFeedback(selectedTaskId.value, {
      category: feedbackForm.category,
      message: feedbackForm.message.trim(),
    });
    feedbackForm.message = "";
    await loadTaskDetail(selectedTaskId.value, false);
    feedbackStatus.value = "反馈已提交，管理员可在已完成任务中查看。";
  } catch (error) {
    feedbackStatus.value = `提交失败：${error.message}`;
  }
}

async function requestTaskDelay() {
  if (!selectedTaskId.value) {
    feedbackStatus.value = "请先选择一个任务";
    return;
  }
  const message = feedbackForm.message.trim() || "申请延期，请管理员确认新的执行时间。";
  try {
    await submitTaskFeedback(selectedTaskId.value, {
      category: "delay_request",
      message,
    });
    feedbackForm.message = "";
    await loadTaskDetail(selectedTaskId.value, false);
    feedbackStatus.value = "延期申请已提交，等待管理员处理。";
  } catch (error) {
    feedbackStatus.value = `提交延期申请失败：${error.message}`;
  }
}

async function reportTaskAnomaly() {
  if (!selectedTaskId.value) {
    feedbackStatus.value = "请先选择一个任务";
    return;
  }
  const message = feedbackForm.message.trim() || "发现执行异常，请管理员关注。";
  try {
    await submitTaskFeedback(selectedTaskId.value, {
      category: "anomaly",
      message,
    });
    feedbackForm.message = "";
    await loadTaskDetail(selectedTaskId.value, false);
    feedbackStatus.value = "异常已上报，管理员可在复盘界面查看。";
  } catch (error) {
    feedbackStatus.value = `异常上报失败：${error.message}`;
  }
}

async function startAssignedTask() {
  if (!selectedTaskId.value) {
    feedbackStatus.value = "请先选择一个任务";
    return;
  }
  try {
    await controlOpsTask(selectedTaskId.value, "start");
    await refreshTasks();
    feedbackStatus.value = "任务已开始执行。";
  } catch (error) {
    feedbackStatus.value = `开始执行失败：${error.message}`;
  }
}

async function setPilotTaskSpeed(tickMs) {
  if (!selectedTaskId.value) {
    feedbackStatus.value = "请先选择一个任务";
    return;
  }
  try {
    await controlOpsTask(selectedTaskId.value, "set_speed", {
      tick_ms: tickMs,
    });
    await refreshTasks();
    feedbackStatus.value = `已将飞行节拍调整为 ${tickMs} ms/步。`;
  } catch (error) {
    feedbackStatus.value = `调整速度失败：${error.message}`;
  }
}

async function submitTaskRequest() {
  const scheduledStartAt = parseScheduledInput(requestForm.scheduled_start_input);
  if (!requestForm.mission_name.trim()) {
    requestStatus.value = "请填写任务名称";
    return;
  }
  if (!requestForm.requested_location.trim()) {
    requestStatus.value = "请填写执行地点";
    return;
  }
  if (!scheduledStartAt) {
    requestStatus.value = "请填写有效的执行时间";
    return;
  }
  try {
    const created = await createOpsTask({
      mission_name: requestForm.mission_name.trim(),
      task_category: requestForm.task_category,
      requested_location: requestForm.requested_location.trim(),
      scheduled_start_at: scheduledStartAt,
      scheduled_start_label: fmtDateTime(scheduledStartAt),
    });
    selectedTaskId.value = created?.task?.task_id || "";
    requestStatus.value = `申请已提交，等待管理员审核。申请编号 ${selectedTaskId.value}`;
    await refreshTasks();
  } catch (error) {
    requestStatus.value = `提交申请失败：${error.message}`;
  }
}

watch(adminSection, async (section) => {
  if (!isAdmin.value) return;
  stopReplayTimer();
  if (section !== "completed") stopReplayVisualTimer();
  if (section === "create" && !pendingReviewTasks.value.some((task) => task.task_id === selectedTaskId.value)) {
    selectedTaskId.value = pendingReviewTasks.value[0]?.task_id || "";
  }
  if (section === "active" && !filteredActiveTasks.value.some((task) => task.task_id === selectedTaskId.value)) {
    selectedTaskId.value = filteredActiveTasks.value[0]?.task_id || "";
  }
  if (section === "completed" && !filteredCompletedTasks.value.some((task) => task.task_id === selectedTaskId.value)) {
    selectedTaskId.value = filteredCompletedTasks.value[0]?.task_id || "";
  }
  await nextTick();
  if (selectedTaskId.value) {
    await loadTaskDetail(selectedTaskId.value, false);
    ensureReplayVisualTimer();
    return;
  }
  drawEmptyCanvas(liveCanvasRef.value, "暂无实时任务画面");
  drawEmptyCanvas(historyCanvasRef.value, "暂无可展示回放");
  drawEmptyCanvas(history3dCanvasRef.value, "暂无可展示回放");
});

watch(executorView, async (view) => {
  if (isAdmin.value || isRequester.value) return;
  if (view !== "history") {
    stopReplayVisualTimer();
    return;
  }
  await loadReplay({ silent: true });
  await nextTick();
  drawReplayFrame();
  ensureReplayVisualTimer();
});

onMounted(async () => {
  await refreshAssignees();
  await refreshTasks();
  pollTimer = window.setInterval(() => refreshTasks(), 3200);
  drawEmptyCanvas(executorHistoryCanvasRef.value, "请选择左侧任务以查看历史回放");
  drawEmptyCanvas(executorHistory3dCanvasRef.value, "请选择左侧任务以查看历史回放");
  drawEmptyCanvas(history3dCanvasRef.value, "暂无可展示回放");
  ensureReplayVisualTimer();
});

onUnmounted(() => {
  stopReplayTimer();
  stopReplayVisualTimer();
  if (pollTimer) window.clearInterval(pollTimer);
});
</script>

<template>
  <section class="layout-grid">
    <article class="panel">
      <h2>管理员 / 研究配置</h2>
      <div class="btn-row">
        <button class="btn secondary" @click="applyPreset('maze')">迷宫预设</button>
        <button class="btn secondary" @click="applyPreset('dense')">高密度预设</button>
        <button class="btn secondary" @click="loadSample">示例数据</button>
      </div>
      <form class="field-grid" @submit.prevent="onRun">
        <label>cfg_dir <input v-model="form.cfg_dir" /></label>
        <label>checkpoint_path <input v-model="form.checkpoint_path" /></label>
        <label>device
          <select v-model="form.device">
            <option value="cpu">cpu</option>
            <option value="gpu">gpu</option>
          </select>
        </label>
        <label>map_name <input v-model="form.map_name" /></label>
        <label>num_agents <input v-model.number="form.num_agents" type="number" min="1" /></label>
        <label>max_episode_steps <input v-model.number="form.max_episode_steps" type="number" min="1" /></label>
        <label>max_frames <input v-model.number="form.max_frames" type="number" min="1" /></label>
        <label>seed <input v-model.number="form.seed" type="number" /></label>
        <label>save_svg <input v-model="form.save_svg" /></label>
        <button class="btn" type="submit">运行推理</button>
      </form>
      <div class="status-chip">{{ status }}</div>
    </article>

    <article class="panel">
      <h2>轨迹回放</h2>
      <div class="canvas-wrap">
        <div class="canvas-overlay">
          <span class="chip">Step {{ currentStep }}</span>
          <span class="chip">Device: {{ playback.meta?.actual_device || "sample" }}</span>
          <span class="chip">Map: {{ playback.meta?.map_name || "-" }}</span>
        </div>
        <canvas ref="canvasRef" width="900" height="620"></canvas>
      </div>
      <div class="btn-row" style="margin-top: 10px">
        <button class="btn secondary" @click="togglePlay">{{ playing ? "暂停" : "播放" }}</button>
        <input v-model.number="frameIndex" :max="maxFrameIndex" min="0" type="range" @input="drawCurrentFrame" />
      </div>

      <div class="metrics">
        <div class="metric"><span>平均奖励</span><strong>{{ fmt(playback.metrics?.mean_reward) }}</strong></div>
        <div class="metric"><span>累计完成任务数</span><strong>{{ fmt(playback.metrics?.tasks_completed) }}</strong></div>
        <div class="metric"><span>吞吐量</span><strong>{{ fmt(playback.metrics?.throughput) }}</strong></div>
        <div class="metric"><span>顶点冲突</span><strong>{{ fmt(playback.metrics?.vertex_conflicts) }}</strong></div>
      </div>
    </article>

    <article class="panel">
      <h2>运行日志</h2>
      <div class="log-box">{{ logText }}</div>
    </article>
  </section>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref } from "vue";
import { fetchDefaults, runInference } from "../../services/api";
import { buildSampleRun, createRenderer } from "../shared/renderer";

const renderer = createRenderer();
const canvasRef = ref(null);
const playing = ref(false);
const timer = ref(null);
const frameIndex = ref(0);
const status = ref("初始化中...");

const form = reactive({
  cfg_dir: "results/train_dir/0001/exp",
  checkpoint_path: "results/train_dir/0001/exp/checkpoint_p0/best/best_model_obj_+0000000.000000_step_000921600_1772213120.pth",
  device: "cpu",
  map_name: "mazes-s0_wc8_od55",
  num_agents: 16,
  max_episode_steps: 64,
  max_frames: 48,
  seed: 7,
  save_svg: "results/mac_eval/vue-demo.svg",
  render: false,
});

const playback = reactive(buildSampleRun());
const presets = {
  maze: { map_name: "mazes-s0_wc8_od55", num_agents: 16, max_episode_steps: 64, max_frames: 48, seed: 7 },
  dense: { map_name: "mazes-s1_wc3_od70", num_agents: 32, max_episode_steps: 96, max_frames: 72, seed: 11 },
};

const maxFrameIndex = computed(() => Math.max(0, (playback.frames?.length || 1) - 1));
const currentStep = computed(() => playback.frames?.[frameIndex.value]?.step ?? 0);
const logText = computed(() => {
  const meta = playback.meta || {};
  const metrics = playback.metrics || {};
  return [
    `cfg_dir: ${meta.cfg_dir || "sample"}`,
    `checkpoint: ${meta.checkpoint_path || "sample"}`,
    `device: ${meta.actual_device || "sample"}`,
    `map_name: ${meta.map_name || "sample"}`,
    `frames: ${meta.frames || 0}`,
    `svg: ${meta.save_svg || "未输出"}`,
    "",
    `mean_reward: ${fmt(metrics.mean_reward)}`,
    `tasks_completed: ${fmt(metrics.tasks_completed)}`,
    `throughput: ${fmt(metrics.throughput)}`,
    `total_steps: ${fmt(metrics.total_steps)}`,
    `vertex_conflicts: ${fmt(metrics.vertex_conflicts)}`,
  ].join("\n");
});

function fmt(v) {
  return v == null || Number.isNaN(Number(v)) ? "-" : String(v);
}

function applyPreset(key) {
  Object.assign(form, presets[key]);
  status.value = `已应用${key === "maze" ? "迷宫" : "高密度"}预设`;
}

function loadSample() {
  stopTimer();
  Object.assign(playback, buildSampleRun());
  frameIndex.value = 0;
  drawCurrentFrame();
  status.value = "已加载前端示例数据";
}

async function onRun() {
  stopTimer();
  status.value = "正在请求后端推理...";
  try {
    const payload = await runInference({ ...form });
    Object.assign(playback, payload);
    frameIndex.value = 0;
    drawCurrentFrame();
    status.value = "推理完成";
  } catch (error) {
    status.value = `推理失败：${error.message}`;
  }
}

function drawCurrentFrame() {
  const frame = playback.frames?.[frameIndex.value];
  renderer.draw(canvasRef.value, playback.environment, frame);
}

function togglePlay() {
  if (!playback.frames?.length) return;
  if (playing.value) {
    stopTimer();
    return;
  }
  playing.value = true;
  timer.value = window.setInterval(() => {
    if (frameIndex.value >= maxFrameIndex.value) {
      stopTimer();
      return;
    }
    frameIndex.value += 1;
    drawCurrentFrame();
  }, 240);
}

function stopTimer() {
  playing.value = false;
  if (timer.value) {
    window.clearInterval(timer.value);
    timer.value = null;
  }
}

onMounted(async () => {
  try {
    const defaults = await fetchDefaults();
    Object.assign(form, defaults.defaults || {});
    status.value = "默认参数加载完成";
  } catch {
    status.value = "后端默认参数不可用，已使用本地默认值";
  }
  drawCurrentFrame();
});

onUnmounted(() => stopTimer());
</script>

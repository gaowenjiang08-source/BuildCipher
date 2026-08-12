import { MotionCard, MotionReveal, MotionStatus } from "../../components/Motion";
import { Panel } from "../../components/Panel";

const PROVIDERS = [
  {
    id: "openai",
    label: "OpenAI",
    region: "国际模型",
    mode: "官方或兼容网关",
    keyField: "openaiApiKey",
    modelField: "openaiModel",
    baseUrlField: "openaiBaseUrl",
    envKey: "openai_api_key",
    modelPlaceholder: "gpt-4-turbo-preview",
    modelPresets: ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo-preview"],
    basePlaceholder: "官方默认可留空，或填写 OpenAI-compatible 中转地址",
  },
  {
    id: "anthropic",
    label: "Claude",
    region: "国际模型",
    mode: "Anthropic API",
    keyField: "anthropicApiKey",
    modelField: "anthropicModel",
    baseUrlField: "anthropicBaseUrl",
    envKey: "anthropic_api_key",
    modelPlaceholder: "claude-3-opus-20240229",
    modelPresets: ["claude-3-5-sonnet-latest", "claude-3-opus-20240229", "claude-3-haiku-20240307"],
    basePlaceholder: "官方默认可留空，或填写 Claude 中转地址",
  },
  {
    id: "gemini",
    label: "Gemini",
    region: "国际模型",
    mode: "Google Gemini API",
    keyField: "geminiApiKey",
    modelField: "geminiModel",
    baseUrlField: "geminiBaseUrl",
    envKey: "gemini_api_key",
    modelPlaceholder: "gemini-1.5-pro",
    modelPresets: ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-pro"],
    basePlaceholder: "官方默认可留空，或填写 Gemini 兼容网关",
  },
  {
    id: "zhipuai",
    label: "智谱 GLM",
    region: "中国模型",
    mode: "智谱官方 API",
    keyField: "zhipuaiApiKey",
    modelField: "zhipuaiModel",
    baseUrlField: "zhipuaiBaseUrl",
    envKey: "zhipuai_api_key",
    modelPlaceholder: "glm-4",
    modelPresets: ["glm-4", "glm-4-plus", "glm-3-turbo"],
    basePlaceholder: "官方默认可留空",
  },
  {
    id: "deepseek",
    label: "DeepSeek",
    region: "中国模型",
    mode: "OpenAI-compatible",
    keyField: "deepseekApiKey",
    modelField: "deepseekModel",
    baseUrlField: "deepseekBaseUrl",
    envKey: "deepseek_api_key",
    modelPlaceholder: "deepseek-chat",
    modelPresets: ["deepseek-chat", "deepseek-reasoner"],
    basePlaceholder: "https://api.deepseek.com",
  },
  {
    id: "qwen",
    label: "通义千问",
    region: "中国模型",
    mode: "DashScope 兼容模式",
    keyField: "qwenApiKey",
    modelField: "qwenModel",
    baseUrlField: "qwenBaseUrl",
    envKey: "qwen_api_key",
    modelPlaceholder: "qwen-plus",
    modelPresets: ["qwen-plus", "qwen-turbo", "qwen-max"],
    basePlaceholder: "https://dashscope.aliyuncs.com/compatible-mode/v1",
  },
  {
    id: "baidu",
    label: "百度千帆",
    region: "中国模型",
    mode: "OpenAI-compatible",
    keyField: "baiduApiKey",
    modelField: "baiduModel",
    baseUrlField: "baiduBaseUrl",
    envKey: "baidu_api_key",
    modelPlaceholder: "ernie-4.0-turbo-8k",
    modelPresets: ["ernie-4.0-turbo-8k", "ernie-3.5-8k", "ernie-speed"],
    basePlaceholder: "填写千帆 OpenAI-compatible 接入地址",
  },
  {
    id: "relay",
    label: "第三方中转",
    region: "自定义网关",
    mode: "OpenAI-compatible",
    keyField: "relayApiKey",
    modelField: "relayModel",
    baseUrlField: "relayBaseUrl",
    envKey: "relay_api_key",
    modelPlaceholder: "gpt-4o-mini",
    modelPresets: ["gpt-4o-mini", "claude-3-5-sonnet-latest", "gemini-1.5-pro", "deepseek-chat"],
    basePlaceholder: "必须填写中转平台的 OpenAI-compatible Base URL",
  },
];

function cn(...values) {
  return values.filter(Boolean).join(" ");
}

function providerLabel(value) {
  return PROVIDERS.find((item) => item.id === value)?.label || value || "--";
}

function looksConfigured(value) {
  return Boolean(String(value || "").trim());
}

function statusToneClass(status) {
  if (status === "ok") return "border-emerald-200 bg-emerald-50 text-emerald-800";
  if (status === "bad") return "border-rose-200 bg-rose-50 text-rose-800";
  if (status === "checking") return "border-sky-200 bg-sky-50 text-sky-800";
  return "border-slate-200 bg-white text-slate-700";
}

function statusLabel(status, okText, badText, checkingText = "校验中", pendingText = "待校验") {
  if (status === "ok") return okText;
  if (status === "bad") return badText;
  if (status === "checking") return checkingText;
  return pendingText;
}

function FieldShell({ label, hint, children }) {
  return (
    <label className="block text-sm font-semibold text-slate-700">
      <span>{label}</span>
      {hint ? <span className="mt-1 block text-xs font-medium leading-5 text-slate-500">{hint}</span> : null}
      <div className="mt-2">{children}</div>
    </label>
  );
}

function TextInput(props) {
  return (
    <input
      {...props}
      className={cn(
        "min-h-11 w-full rounded-2xl border border-slate-300 bg-sky-50/65 px-3.5 py-2.5 text-sm font-semibold text-slate-900 shadow-inner outline-none transition focus:border-sky-400 focus:bg-white focus:shadow-[var(--cg-focus-ring)]",
        props.className
      )}
    />
  );
}

function SecretInput({ value, onChange, revealed, onToggleReveal, placeholder, configured }) {
  return (
    <div className="relative">
      <TextInput
        type={revealed ? "text" : "password"}
        value={value}
        placeholder={configured ? "后端已保存，留空不会覆盖" : placeholder}
        onChange={onChange}
        autoComplete="off"
        spellCheck={false}
        className="pr-24"
      />
      <button
        type="button"
        onClick={onToggleReveal}
        className="absolute right-2 top-1/2 -translate-y-1/2 rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs font-bold text-slate-600 hover:bg-slate-50"
      >
        {revealed ? "隐藏" : "显示"}
      </button>
    </div>
  );
}

function Metric({ label, value, tone = "neutral" }) {
  const toneClass = {
    neutral: "border-slate-200 bg-white text-slate-900",
    ok: "border-emerald-200 bg-emerald-50 text-emerald-900",
    warn: "border-amber-200 bg-amber-50 text-amber-900",
    info: "border-sky-200 bg-sky-50 text-sky-900",
  };

  return (
    <div className={cn("rounded-[1.25rem] border px-4 py-3", toneClass[tone] || toneClass.neutral)}>
      <p className="text-[11px] font-extrabold uppercase tracking-[0.12em] opacity-70">{label}</p>
      <p className="mt-2 text-lg font-extrabold tracking-[-0.02em]">{value}</p>
    </div>
  );
}

export default function SettingsView({
  settings,
  setSettings,
  showSecrets,
  setShowSecrets,
  backendEnv,
  connectionStatus = "unknown",
  connectionMessage = "",
  llmStatus = "unknown",
  llmMessage = "",
  testConnection,
  testLlmConnection,
  syncEnv,
  refreshEnvSettings,
  resetAllSettings,
  redactSensitiveObject,
}) {
  const backendValues = backendEnv?.values || {};
  const configuredProviderCount = PROVIDERS.filter(
    (provider) => looksConfigured(settings[provider.keyField]) || looksConfigured(backendValues[provider.envKey])
  ).length;
  const activeProvider = PROVIDERS.find((provider) => provider.id === settings.provider) || PROVIDERS[0];
  const hasApiBase = looksConfigured(settings.apiBaseUrl);
  const nextStep = !hasApiBase
    ? "填写后端地址"
    : configuredProviderCount === 0
      ? "录入模型密钥"
      : llmStatus !== "ok"
        ? "校验当前模型"
        : "保存配置";

  function updateSettings(patch) {
    setSettings((prev) => ({ ...prev, ...patch }));
  }

  function toggleSecret(key) {
    setShowSecrets((prev) => ({ ...prev, [key]: !prev[key] }));
  }

  return (
    <Panel
      title="系统连接与模型配置"
      subtitle="配置后端地址、模型供应商、模型名称和第三方中转地址。所有密钥保存到后端环境，前端只展示脱敏状态。"
    >
      <MotionReveal className="rounded-[1.6rem] border border-slate-200 bg-[linear-gradient(135deg,#ffffff_0%,#f8fbff_52%,#eef6ff_100%)] p-5 shadow-sm">
        <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_24rem]">
          <div>
            <div className="flex flex-wrap gap-2">
              <MotionStatus className={cn("rounded-full border px-3 py-1 text-xs font-bold", hasApiBase ? "border-emerald-200 bg-emerald-50 text-emerald-700" : "border-amber-200 bg-amber-50 text-amber-700")}>
                {hasApiBase ? "后端地址已填写" : "需要填写后端地址"}
              </MotionStatus>
              <span className="rounded-full border border-sky-200 bg-sky-50 px-3 py-1 text-xs font-bold text-sky-700">
                默认模型：{providerLabel(settings.provider)}
              </span>
              <span className={cn("rounded-full border px-3 py-1 text-xs font-bold", configuredProviderCount ? "border-emerald-200 bg-emerald-50 text-emerald-700" : "border-amber-200 bg-amber-50 text-amber-700")}>
                已保存密钥：{configuredProviderCount} / {PROVIDERS.length}
              </span>
            </div>

            <div className="mt-5 max-w-[62ch]">
              <p className="text-[2rem] font-extrabold leading-tight tracking-[-0.04em] text-slate-950">
                模型服务接入
              </p>
              <p className="mt-3 text-base leading-7 text-slate-600">
                当前平台可接入 OpenAI、Claude、Gemini、中国模型 API，以及 OpenAI-compatible 第三方中转。请先校验连接，再保存为后端运行配置。
              </p>
            </div>

            <div className="mt-5 grid max-w-4xl grid-cols-1 gap-3 md:grid-cols-3">
              {[
                { label: "当前步骤", value: nextStep },
                { label: "保存位置", value: "后端 .env" },
                { label: "密钥显示", value: "仅脱敏展示" },
              ].map((item, index) => (
                <MotionReveal key={item.label} delay={80 + index * 60} className="rounded-2xl border border-slate-200 bg-white/80 px-4 py-3" variant="soft">
                  <p className="text-[11px] font-extrabold uppercase tracking-[0.12em] text-slate-500">{item.label}</p>
                  <p className="mt-2 text-sm font-extrabold text-slate-900">{item.value}</p>
                </MotionReveal>
              ))}
            </div>
          </div>

          <div className="grid gap-3">
            <Metric
              label="后端连接"
              value={statusLabel(connectionStatus, "可用", "异常")}
              tone={connectionStatus === "ok" ? "ok" : connectionStatus === "bad" ? "warn" : "neutral"}
            />
            <Metric
              label="模型连接"
              value={statusLabel(llmStatus, "可用", "失败")}
              tone={llmStatus === "ok" ? "ok" : llmStatus === "bad" ? "warn" : "neutral"}
            />
            <Metric label="环境项" value={Object.keys(backendValues).length || "--"} tone={backendEnv ? "info" : "neutral"} />
          </div>
        </div>
      </MotionReveal>

      <div className="mt-5 grid grid-cols-1 gap-4 xl:grid-cols-[1fr_0.85fr]">
        <MotionReveal delay={90} className="rounded-[1.5rem] border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-base font-extrabold text-slate-950">连接参数</p>
              <p className="mt-1 text-sm leading-6 text-slate-500">先确认前端连到正确后端，再选择默认模型服务。</p>
            </div>
            <span className={cn("rounded-full border px-3 py-1 text-xs font-bold", statusToneClass(connectionStatus))}>
              {connectionMessage || "尚未校验后端连接"}
            </span>
          </div>

          <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-3">
            <FieldShell label="后端 API 地址" hint="例如 http://127.0.0.1:8000">
              <TextInput
                value={settings.apiBaseUrl}
                onChange={(event) => updateSettings({ apiBaseUrl: event.target.value })}
                placeholder="http://127.0.0.1:8000"
              />
            </FieldShell>
            <FieldShell label="默认模型服务" hint="MAS、技能执行和结构化评估默认使用它">
              <select
                className="min-h-11 w-full rounded-2xl border border-slate-300 bg-sky-50/65 px-3.5 py-2.5 text-sm font-semibold text-slate-900 outline-none transition focus:border-sky-400 focus:bg-white focus:shadow-[var(--cg-focus-ring)]"
                value={settings.provider}
                onChange={(event) => updateSettings({ provider: event.target.value })}
              >
                {PROVIDERS.map((provider) => (
                  <option key={provider.id} value={provider.id}>
                    {provider.label}
                  </option>
                ))}
              </select>
            </FieldShell>
            <FieldShell label="请求超时" hint="单位：毫秒">
              <TextInput
                type="number"
                min="5000"
                step="1000"
                value={settings.timeoutMs}
                onChange={(event) => updateSettings({ timeoutMs: Number(event.target.value) })}
              />
            </FieldShell>
          </div>
        </MotionReveal>

        <MotionReveal delay={140} className="rounded-[1.5rem] border border-slate-200 bg-[linear-gradient(135deg,#ffffff_0%,#f8fafc_55%,#ecfeff_100%)] p-5 shadow-sm">
          <p className="text-base font-extrabold text-slate-950">建议顺序</p>
          <div className="mt-4 space-y-3">
            {["填写后端地址并校验健康状态", "选择模型服务，填写密钥、模型和 Base URL", "先校验当前模型，再保存到后端 .env"].map((item, index) => (
              <MotionReveal key={item} delay={200 + index * 60} className="flex gap-3 rounded-2xl border border-slate-200 bg-white/85 p-3" variant="soft">
                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-slate-900 text-xs font-extrabold text-white">
                  {index + 1}
                </span>
                <p className="text-sm font-semibold leading-6 text-slate-700">{item}</p>
              </MotionReveal>
            ))}
          </div>
        </MotionReveal>
      </div>

      <MotionReveal delay={160} className="mt-5 rounded-[1.5rem] border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-base font-extrabold text-slate-950">模型服务与中转网关</p>
            <p className="mt-1 text-sm leading-6 text-slate-500">每个服务可单独配置密钥、模型名称和 Base URL。第三方中转请使用 OpenAI-compatible 地址。</p>
          </div>
          <span className={cn("rounded-full border px-3 py-1 text-xs font-bold", statusToneClass(llmStatus))}>
            {llmMessage || `当前待校验：${activeProvider.label}`}
          </span>
        </div>

        <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-2 2xl:grid-cols-4">
          {PROVIDERS.map((provider, index) => {
            const configured = looksConfigured(settings[provider.keyField]) || looksConfigured(backendValues[provider.envKey]);
            const selected = settings.provider === provider.id;
            return (
              <MotionCard
                key={provider.id}
                delay={220 + index * 45}
                selected={selected}
                className={cn(
                  "rounded-[1.35rem] border p-4",
                  selected ? "border-sky-300 bg-sky-50/70 shadow-[var(--cg-shadow-soft)]" : "border-slate-200 bg-slate-50/60"
                )}
              >
                <div className="mb-4 flex items-start justify-between gap-3">
                  <div>
                    <button
                      type="button"
                      onClick={() => updateSettings({ provider: provider.id })}
                      className={cn(
                        "rounded-full border px-3 py-1.5 text-xs font-extrabold",
                        selected ? "border-sky-300 bg-white text-sky-800" : "border-slate-200 bg-white text-slate-600"
                      )}
                    >
                      {provider.label}
                    </button>
                    <p className="mt-2 text-xs font-semibold leading-5 text-slate-500">{provider.region} · {provider.mode}</p>
                  </div>
                  <span className={cn("rounded-full border px-2.5 py-1 text-[11px] font-bold", configured ? "border-emerald-200 bg-emerald-50 text-emerald-700" : "border-amber-200 bg-amber-50 text-amber-700")}>
                    {configured ? "已配置" : "未配置"}
                  </span>
                </div>

                <div className="space-y-4">
                  <FieldShell label="API Key" hint="留空保存时不会覆盖后端已保存密钥">
                    <SecretInput
                      value={settings[provider.keyField] || ""}
                      configured={configured}
                      placeholder={`输入 ${provider.label} API Key`}
                      revealed={Boolean(showSecrets[provider.id])}
                      onToggleReveal={() => toggleSecret(provider.id)}
                      onChange={(event) => updateSettings({ [provider.keyField]: event.target.value })}
                    />
                  </FieldShell>
                  <FieldShell label="模型名称" hint="可手动指定，也可点选常用值">
                    <TextInput
                      value={settings[provider.modelField] || ""}
                      placeholder={provider.modelPlaceholder}
                      list={`${provider.id}-model-presets`}
                      onChange={(event) => updateSettings({ [provider.modelField]: event.target.value })}
                    />
                    <datalist id={`${provider.id}-model-presets`}>
                      {provider.modelPresets.map((model) => (
                        <option key={model} value={model} />
                      ))}
                    </datalist>
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {provider.modelPresets.slice(0, 3).map((model) => (
                        <button
                          key={model}
                          type="button"
                          onClick={() => updateSettings({ [provider.modelField]: model })}
                          className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-[11px] font-bold text-slate-600 hover:border-sky-300 hover:text-sky-700"
                        >
                          {model}
                        </button>
                      ))}
                    </div>
                  </FieldShell>
                  <FieldShell label="Base URL" hint={provider.basePlaceholder}>
                    <TextInput
                      value={settings[provider.baseUrlField] || ""}
                      placeholder={provider.basePlaceholder}
                      onChange={(event) => updateSettings({ [provider.baseUrlField]: event.target.value })}
                    />
                  </FieldShell>
                </div>
              </MotionCard>
            );
          })}
        </div>
      </MotionReveal>

      <MotionReveal delay={220} className="mt-5 rounded-[1.5rem] border border-slate-200 bg-[linear-gradient(135deg,#ffffff_0%,#f8fafc_50%,#fff7ed_100%)] p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-base font-extrabold text-slate-950">配置动作</p>
            <p className="mt-1 text-sm leading-6 text-slate-500">模型校验会使用当前表单里的临时 key、模型和 Base URL；保存后才写入后端环境。</p>
          </div>
          <span className="rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-bold text-amber-700">
            保存后立即刷新配置缓存
          </span>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <button type="button" onClick={testConnection} className="cg-button cg-button-secondary">
            校验后端连接
          </button>
          <button type="button" onClick={testLlmConnection} className="cg-button cg-button-secondary">
            校验当前模型
          </button>
          <button type="button" onClick={syncEnv} className="cg-button cg-button-primary">
            保存到后端 .env
          </button>
          <button type="button" onClick={refreshEnvSettings} className="cg-button cg-button-secondary">
            刷新后端配置
          </button>
          <button type="button" onClick={resetAllSettings} className="cg-button cg-button-ghost">
            恢复前端默认
          </button>
        </div>
      </MotionReveal>

      {backendEnv ? (
        <MotionReveal delay={260} className="mt-5 rounded-[1.5rem] border border-slate-200 bg-white p-5 shadow-sm">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-base font-extrabold text-slate-950">后端环境快照</p>
              <p className="mt-1 text-sm leading-6 text-slate-500">确认后端当前读取到的 provider、模型、Base URL 和脱敏密钥状态。</p>
            </div>
            <button
              type="button"
              onClick={() => setShowSecrets((prev) => ({ ...prev, backendEnv: !prev.backendEnv }))}
              className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs font-bold text-slate-700 hover:bg-slate-50"
            >
              {showSecrets.backendEnv ? "脱敏显示" : "查看完整快照"}
            </button>
          </div>
          <pre className="max-h-72 overflow-auto rounded-2xl border border-slate-200 bg-slate-950 p-4 text-xs leading-6 text-slate-100">
            {JSON.stringify(showSecrets.backendEnv ? backendValues : redactSensitiveObject(backendValues), null, 2)}
          </pre>
        </MotionReveal>
      ) : null}
    </Panel>
  );
}

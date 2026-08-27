export const CONSTRUCTION_ATTACKS = [
  { id: "ifc_content_tamper", label: "IFC 内容篡改", asset: "主模型 IFC", control: "内容摘要 + 签名清单" },
  { id: "signed_old_version_rollback", label: "合法旧版本回滚", asset: "批准版本链", control: "当前批准版本指针" },
  { id: "full_model_overprivilege", label: "分包完整模型越权", asset: "专业交付包", control: "角色范围 + 最小披露" },
  { id: "unregistered_device_impersonation", label: "未注册设备冒充", asset: "工地传感器", control: "设备注册 + 独立凭据" },
  { id: "valid_signed_telemetry_replay", label: "有效签名遥测重放", asset: "验收遥测", control: "计数器 + nonce + 时间窗" },
];

export const CONSTRUCTION_VALIDATION_CONTROLS = {
  ifc_content_tamper: {
    attackMethod: "保持 manifest 与文件身份不变，只修改 IFC DATA 段中的一个字节。",
    primitive: "SHA-256 内容摘要 + HMAC-SHA256 manifest 签名/验签",
    invariant: "observed_content_sha256 必须等于 manifest 中的 expected_content_sha256。",
    controlKey: "content_hash_enforced",
    acceptance: "篡改文件拒绝，原始文件在相同签名与角色下通过。",
  },
  signed_old_version_rollback: {
    attackMethod: "提交签名仍有效的父版本，尝试覆盖当前批准版本。",
    primitive: "签名 manifest + parent_version + current_approved_version 指针",
    invariant: "requested_version 必须等于服务端 latest_approved[asset_id]。",
    controlKey: "current_version_enforced",
    acceptance: "旧签名版本拒绝，当前批准版本通过。",
  },
  full_model_overprivilege: {
    attackMethod: "以 specialty_subcontractor 身份请求只允许总包和监理访问的完整模型。",
    primitive: "交付包 allowed_roles 与 requester_role 的 RBAC 判定",
    invariant: "requester_role 必须出现在签名 manifest 的 allowed_roles 中。",
    controlKey: "role_scope_enforced",
    acceptance: "专业分包完整模型请求拒绝，并转向专业过滤交付包。",
  },
  unregistered_device_impersonation: {
    attackMethod: "使用攻击者自有密钥构造未注册 device_id 的遥测消息。",
    primitive: "设备注册表 + 独立 credential_ref + HMAC-SHA256 MAC 验证",
    invariant: "device_id 必须已注册，且 MAC 必须由该设备绑定凭据验证通过。",
    controlKey: "device_registration_enforced",
    acceptance: "未知设备拒绝，已注册设备的新消息通过。",
  },
  valid_signed_telemetry_replay: {
    attackMethod: "原样重放一条 MAC 仍有效的历史遥测消息。",
    primitive: "单调 counter + 一次性 nonce + ±300 秒时间窗",
    invariant: "counter 递增、nonce 未使用且 timestamp 位于 freshness_window 内。",
    controlKey: "telemetry_replay_guard_enforced",
    acceptance: "历史消息因新鲜度失败被拒绝，后续新 counter/nonce 消息通过。",
  },
};

export const CONSTRUCTION_TEMPLATES = [
  {
    title: "BIM/IFC 可信交付",
    tags: ["IFC", "版本防回滚", "分包最小披露"],
    requirement:
      "为建筑工程项目设计 BIM/IFC 可信交付方案：验证模型内容篡改、合法旧版本回滚和专业分包越权，绑定设计、总包、监理的签批身份与证据链。",
  },
  {
    title: "工地 IoT 验收证据",
    tags: ["设备身份", "防重放", "隐蔽工程验收"],
    requirement:
      "为施工现场传感器与隐蔽工程验收设计可信数据链：验证未注册设备冒充和有效签名遥测重放，保留设备身份、时间、签批人与检测结果证据。",
  },
  {
    title: "项目签批证据链",
    tags: ["签批", "验收", "可追溯"],
    requirement:
      "为建筑项目设计跨参与方签批与验收证据链：覆盖建设单位、设计、总包、分包和监理，确保模型、图纸、检测报告和签批记录可验真、可追溯、可回放。",
  },
];

export const CONSTRUCTION_INPUT_DIMENSIONS = [
  {
    title: "1. 工程资产",
    prefix: "工程资产",
    options: ["BIM/IFC 模型", "施工图纸", "检测报告", "工地设备遥测", "签批记录", "竣工档案"],
  },
  {
    title: "2. 可信目标",
    prefix: "可信目标",
    options: ["内容防篡改", "版本防回滚", "参与方身份", "最小权限交付", "设备防冒充", "证据可追溯"],
  },
  {
    title: "3. 项目约束",
    prefix: "项目约束",
    options: ["多参与方协同", "离线工地网络", "长期归档", "ISO 19650 参考", "国产密码迁移", "后量子迁移"],
  },
];

const CONSTRUCTION_VIEW_LABELS = {
  overview: "工程总览",
  workbench: "项目工作台",
  context: "可信协同",
  validation: "攻防验证",
  delivery: "交付中心",
};

const CONSTRUCTION_SECTION_LABELS = {
  overview: { journey: "可信交付主线" },
  context: { participants: "参与方责任边界", evidence: "证据链结构" },
  validation: { attacks: "五类攻击验证" },
  delivery: { conclusion: "交付结论", boundaries: "能力边界" },
};

export function getConstructionViewLabel(view = "") {
  return CONSTRUCTION_VIEW_LABELS[String(view || "").trim()] || "工程业务页面";
}

export function getConstructionSectionLabel(view = "", sectionId = "") {
  return CONSTRUCTION_SECTION_LABELS[String(view || "").trim()]?.[String(sectionId || "").trim()] || "";
}

function asArray(value) {
  return Array.isArray(value) ? value : [];
}

export function buildConstructionState({ attackLoop = {}, delivery = {}, currentCaseSummary = {} } = {}) {
  const baseline = asArray(attackLoop.attack_results);
  const regression = asArray(attackLoop.regression_attack_results);
  const evidenceRefs = new Set();
  [...baseline, ...regression].forEach((item) => {
    asArray(item?.artifact_refs).forEach((ref) => evidenceRefs.add(ref));
    asArray(item?.metrics?.evidence_refs).forEach((ref) => evidenceRefs.add(ref));
  });
  const target = attackLoop.target_service || {};
  return {
    caseId: currentCaseSummary?.case_id || "待创建工程项目",
    statusLabel: currentCaseSummary?.status_label || delivery?.status_label || "待启动",
    targetLabel: target.template_label || target.service_name || "BIM/IFC 可信交付目标",
    targetTemplate: target.template_id || "bim_package_exchange_v1",
    baseline,
    regression,
    baselineBlocked: baseline.filter((item) => item?.metrics?.blocked).length,
    regressionBlocked: regression.filter((item) => item?.metrics?.blocked).length,
    evidenceCount: evidenceRefs.size,
    patchApplied: Boolean(attackLoop.patch_spec),
    ledgerValid: regression.length > 0 && regression.every((item) => asArray(item?.artifact_refs).some((ref) => String(ref).includes("project_evidence_ledger"))),
  };
}

export function attackResultByType(results = [], attackType) {
  return asArray(results).find(
    (item) => item?.attack_type === attackType || item?.metrics?.attack_type === attackType
  );
}

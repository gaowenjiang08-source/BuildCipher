export const CONSTRUCTION_ATTACKS = [
  { id: "ifc_content_tamper", label: "IFC 内容篡改", asset: "主模型 IFC", control: "内容摘要 + 签名清单" },
  { id: "signed_old_version_rollback", label: "合法旧版本回滚", asset: "批准版本链", control: "当前批准版本指针" },
  { id: "full_model_overprivilege", label: "分包完整模型越权", asset: "专业交付包", control: "角色范围 + 最小披露" },
  { id: "unregistered_device_impersonation", label: "未注册设备冒充", asset: "工地传感器", control: "设备注册 + 独立凭据" },
  { id: "valid_signed_telemetry_replay", label: "有效签名遥测重放", asset: "验收遥测", control: "计数器 + nonce + 时间窗" },
];

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
  validation: "安全验证",
  delivery: "可信交付",
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
  return asArray(results).find((item) => item?.metrics?.attack_type === attackType);
}

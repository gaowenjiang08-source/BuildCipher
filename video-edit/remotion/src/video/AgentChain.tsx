import {Easing, interpolate, useCurrentFrame} from "remotion";

const agents = [
  ["01", "需求结构化"],
  ["02", "密码方案设计"],
  ["03", "合规审计"],
  ["04", "攻击规划"],
  ["05", "漏洞评估"],
  ["06", "专家裁决"],
  ["07", "补丁规划"],
  ["08", "反思与回归"],
  ["09", "可信交付"],
];

export const AgentChain: React.FC = () => {
  const frame = useCurrentFrame();

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        padding: "94px 110px",
        background: "linear-gradient(135deg, rgba(3, 12, 27, 0.97), rgba(7, 31, 52, 0.95))",
        color: "white",
        opacity: interpolate(frame, [0, 18, 202, 232], [0, 1, 1, 0], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: Easing.bezier(0.16, 1, 0.3, 1),
        }),
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "flex-end",
          justifyContent: "space-between",
          gap: 40,
        }}
      >
        <div>
          <div style={{fontFamily: "Arial, sans-serif", fontSize: 30, fontWeight: 800, letterSpacing: 6, color: "#67e8f9"}}>
            BUILDCIPHER ORCHESTRATION
          </div>
          <div style={{fontFamily: "Microsoft YaHei, Arial, sans-serif", fontSize: 74, fontWeight: 900, marginTop: 12}}>
            多 Agent 可信交付链路
          </div>
        </div>
        <div style={{fontFamily: "Arial, sans-serif", fontSize: 32, fontWeight: 800, color: "#a5f3fc"}}>
          结构化交接 · 工具执行 · 失败纠偏
        </div>
      </div>

      <div
        style={{
          marginTop: 68,
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: 28,
        }}
      >
        {agents.map(([number, label], index) => {
          const activeFrame = 22 + index * 19;
          return (
            <div
              key={number}
              style={{
                minHeight: 178,
                borderRadius: 28,
                border: `2px solid ${frame >= activeFrame ? "rgba(103, 232, 249, 0.9)" : "rgba(148, 163, 184, 0.22)"}`,
                background: frame >= activeFrame
                  ? "linear-gradient(135deg, rgba(8, 145, 178, 0.28), rgba(15, 23, 42, 0.92))"
                  : "rgba(15, 23, 42, 0.72)",
                boxShadow: frame >= activeFrame ? "0 18px 60px rgba(6, 182, 212, 0.18)" : "none",
                padding: "30px 34px",
                display: "flex",
                alignItems: "center",
                gap: 28,
                opacity: interpolate(frame, [activeFrame - 12, activeFrame], [0.35, 1], {
                  extrapolateLeft: "clamp",
                  extrapolateRight: "clamp",
                  easing: Easing.bezier(0.16, 1, 0.3, 1),
                }),
                translate: interpolate(frame, [activeFrame - 12, activeFrame], ["0px 24px", "0px 0px"], {
                  extrapolateLeft: "clamp",
                  extrapolateRight: "clamp",
                  easing: Easing.bezier(0.16, 1, 0.3, 1),
                }),
              }}
            >
              <div
                style={{
                  width: 82,
                  height: 82,
                  flex: "0 0 auto",
                  borderRadius: 24,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  backgroundColor: frame >= activeFrame ? "#06b6d4" : "rgba(51, 65, 85, 0.75)",
                  fontFamily: "Arial, sans-serif",
                  fontSize: 34,
                  fontWeight: 900,
                }}
              >
                {number}
              </div>
              <div style={{fontFamily: "Microsoft YaHei, Arial, sans-serif", fontSize: 46, fontWeight: 900}}>{label}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

import {Video} from "@remotion/media";
import {AbsoluteFill, Sequence, staticFile} from "remotion";
import {AgentChain} from "../AgentChain";

export const AgentScene: React.FC = () => {
  return (
    <AbsoluteFill style={{backgroundColor: "#07111f", overflow: "hidden"}}>
      <Video
        name="06 专家模式"
        src={staticFile("raw/6.mp4")}
        muted
        objectFit="cover"
        style={{width: "100%", height: "100%"}}
      />
      <Sequence name="多 Agent 链路图" from={26} durationInFrames={240}>
        <AgentChain />
      </Sequence>
    </AbsoluteFill>
  );
};

import {TransitionSeries, linearTiming} from "@remotion/transitions";
import {fade} from "@remotion/transitions/fade";
import {slide} from "@remotion/transitions/slide";
import {AgentScene} from "./scenes/AgentScene";
import {CodeScene} from "./scenes/CodeScene";
import {CollaborationScene} from "./scenes/CollaborationScene";
import {DeliveryScene} from "./scenes/DeliveryScene";
import {IfcScene} from "./scenes/IfcScene";
import {OverviewScene} from "./scenes/OverviewScene";
import {ValidationScene} from "./scenes/ValidationScene";

const transitionTiming = linearTiming({durationInFrames: 20});

export const BuildCipherDemo: React.FC = () => {
  return (
    <TransitionSeries name="BuildCipher 两分钟演示">
      <TransitionSeries.Sequence name="01 工程总览" durationInFrames={496}>
        <OverviewScene />
      </TransitionSeries.Sequence>
      <TransitionSeries.Transition presentation={fade()} timing={transitionTiming} />
      <TransitionSeries.Sequence name="02 IFC 导入" durationInFrames={552}>
        <IfcScene />
      </TransitionSeries.Sequence>
      <TransitionSeries.Transition presentation={fade()} timing={transitionTiming} />
      <TransitionSeries.Sequence name="03 可信协同" durationInFrames={312}>
        <CollaborationScene />
      </TransitionSeries.Sequence>
      <TransitionSeries.Transition presentation={slide({direction: "from-right"})} timing={transitionTiming} />
      <TransitionSeries.Sequence name="04 方案与代码生成" durationInFrames={811}>
        <CodeScene />
      </TransitionSeries.Sequence>
      <TransitionSeries.Transition presentation={slide({direction: "from-bottom"})} timing={transitionTiming} />
      <TransitionSeries.Sequence name="05 攻防验证" durationInFrames={882}>
        <ValidationScene />
      </TransitionSeries.Sequence>
      <TransitionSeries.Transition presentation={fade()} timing={transitionTiming} />
      <TransitionSeries.Sequence name="06 多 Agent 专家模式" durationInFrames={354}>
        <AgentScene />
      </TransitionSeries.Sequence>
      <TransitionSeries.Transition presentation={fade()} timing={transitionTiming} />
      <TransitionSeries.Sequence name="07 可信交付" durationInFrames={305}>
        <DeliveryScene />
      </TransitionSeries.Sequence>
    </TransitionSeries>
  );
};

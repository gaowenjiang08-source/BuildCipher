import {Composition, Folder} from "remotion";
import {ContactSheet} from "./storyboard/ContactSheet";
import {BuildCipherDemo} from "./video/BuildCipherDemo";
import {AgentScene} from "./video/scenes/AgentScene";
import {CodeScene} from "./video/scenes/CodeScene";
import {CollaborationScene} from "./video/scenes/CollaborationScene";
import {DeliveryScene} from "./video/scenes/DeliveryScene";
import {IfcScene} from "./video/scenes/IfcScene";
import {OverviewScene} from "./video/scenes/OverviewScene";
import {ValidationScene} from "./video/scenes/ValidationScene";

export const MyComposition = () => {
  return (
    <>
      <Composition
        id="BuildCipherDemo"
        component={BuildCipherDemo}
        durationInFrames={3592}
        fps={30}
        width={1920}
        height={1080}
      />
      <Folder name="可独立编辑的七段场景">
        <Composition id="Scene01Overview" component={OverviewScene} durationInFrames={496} fps={30} width={1920} height={1080} />
        <Composition id="Scene02Ifc" component={IfcScene} durationInFrames={552} fps={30} width={1920} height={1080} />
        <Composition id="Scene03Collaboration" component={CollaborationScene} durationInFrames={312} fps={30} width={1920} height={1080} />
        <Composition id="Scene04Code" component={CodeScene} durationInFrames={811} fps={30} width={1920} height={1080} />
        <Composition id="Scene05Validation" component={ValidationScene} durationInFrames={882} fps={30} width={1920} height={1080} />
        <Composition id="Scene06Agents" component={AgentScene} durationInFrames={354} fps={30} width={1920} height={1080} />
        <Composition id="Scene07Delivery" component={DeliveryScene} durationInFrames={305} fps={30} width={1920} height={1080} />
      </Folder>
      <Composition
        id="ContactSheet"
        component={ContactSheet}
        durationInFrames={30}
        fps={30}
        width={1920}
        height={1080}
      />
    </>
  );
};

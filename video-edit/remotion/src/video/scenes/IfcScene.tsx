import {Video} from "@remotion/media";
import {AbsoluteFill, Easing, interpolate, staticFile, useCurrentFrame} from "remotion";
import {FocusRing} from "../FocusRing";

export const IfcScene: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{backgroundColor: "#07111f", overflow: "hidden"}}>
      <Video
        name="02 IFC 导入"
        src={staticFile("raw/2.mp4")}
        muted
        objectFit="cover"
        style={{
          width: "100%",
          height: "100%",
          scale: interpolate(frame, [0, 72, 490, 551], [1, 1.09, 1.09, 1.015], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.bezier(0.16, 1, 0.3, 1),
            output: "perceptual-scale",
          }),
          translate: interpolate(frame, [0, 72, 490, 551], ["0px 0px", "-22px 32px", "-22px 32px", "0px 0px"], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
        }}
      />
      <FocusRing x={560} y={248} width={1270} height={420} startFrame={70} endFrame={492} />
    </AbsoluteFill>
  );
};

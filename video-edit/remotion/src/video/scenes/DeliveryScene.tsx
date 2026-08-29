import {Video} from "@remotion/media";
import {AbsoluteFill, Easing, interpolate, staticFile, useCurrentFrame} from "remotion";
import {FocusRing} from "../FocusRing";

export const DeliveryScene: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{backgroundColor: "#07111f", overflow: "hidden"}}>
      <Video
        name="07 可信交付"
        src={staticFile("raw/7.mp4")}
        muted
        objectFit="cover"
        style={{
          width: "100%",
          height: "100%",
          scale: interpolate(frame, [0, 42, 270, 304], [1, 1.07, 1.07, 1.015], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.bezier(0.16, 1, 0.3, 1),
            output: "perceptual-scale",
          }),
          translate: interpolate(frame, [0, 42, 270, 304], ["0px 0px", "-24px 16px", "-24px 16px", "0px 0px"], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
        }}
      />
      <FocusRing x={540} y={250} width={1300} height={650} startFrame={40} endFrame={272} />
    </AbsoluteFill>
  );
};

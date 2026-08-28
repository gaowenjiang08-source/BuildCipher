import {Video} from "@remotion/media";
import {AbsoluteFill, Easing, interpolate, staticFile, useCurrentFrame} from "remotion";
import {FocusRing} from "../FocusRing";

export const ValidationScene: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{backgroundColor: "#07111f", overflow: "hidden"}}>
      <Video
        name="05 攻防验证"
        src={staticFile("raw/5.mp4")}
        muted
        objectFit="cover"
        style={{
          width: "100%",
          height: "100%",
          scale: interpolate(frame, [0, 78, 812, 881], [1, 1.095, 1.095, 1.015], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.bezier(0.16, 1, 0.3, 1),
            output: "perceptual-scale",
          }),
          translate: interpolate(frame, [0, 78, 812, 881], ["0px 0px", "-32px -28px", "-32px -28px", "0px 0px"], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
        }}
      />
      <FocusRing x={500} y={232} width={1370} height={790} startFrame={76} endFrame={816} />
    </AbsoluteFill>
  );
};

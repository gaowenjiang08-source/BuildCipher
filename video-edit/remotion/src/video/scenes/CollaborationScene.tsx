import {Video} from "@remotion/media";
import {AbsoluteFill, Easing, interpolate, staticFile, useCurrentFrame} from "remotion";
import {FocusRing} from "../FocusRing";

export const CollaborationScene: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{backgroundColor: "#07111f", overflow: "hidden"}}>
      <Video
        name="03 可信协同"
        src={staticFile("raw/3.mp4")}
        muted
        objectFit="cover"
        style={{
          width: "100%",
          height: "100%",
          scale: interpolate(frame, [0, 44, 270, 311], [1, 1.07, 1.07, 1.01], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.bezier(0.16, 1, 0.3, 1),
            output: "perceptual-scale",
          }),
          translate: interpolate(frame, [0, 44, 270, 311], ["0px 0px", "-18px 18px", "-18px 18px", "0px 0px"], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
        }}
      />
      <FocusRing x={560} y={260} width={1280} height={650} startFrame={42} endFrame={272} />
    </AbsoluteFill>
  );
};

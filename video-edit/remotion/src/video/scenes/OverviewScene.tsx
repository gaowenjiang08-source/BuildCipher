import {Video} from "@remotion/media";
import {AbsoluteFill, Easing, interpolate, staticFile, useCurrentFrame} from "remotion";
import {FocusRing} from "../FocusRing";

export const OverviewScene: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{backgroundColor: "#07111f", overflow: "hidden"}}>
      <Video
        name="01 工程总览"
        src={staticFile("raw/1.mp4")}
        muted
        objectFit="cover"
        style={{
          width: "100%",
          height: "100%",
          scale: interpolate(frame, [0, 60, 430, 495], [1, 1.055, 1.055, 1.01], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.bezier(0.16, 1, 0.3, 1),
            output: "perceptual-scale",
          }),
          translate: interpolate(frame, [0, 60, 430, 495], ["0px 0px", "0px 18px", "0px 18px", "0px 0px"], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
        }}
      />
      <FocusRing x={560} y={280} width={1260} height={610} startFrame={56} endFrame={430} />
    </AbsoluteFill>
  );
};

import {Easing, interpolate, useCurrentFrame} from "remotion";

type FocusRingProps = {
  x: number;
  y: number;
  width: number;
  height: number;
  startFrame: number;
  endFrame: number;
};

export const FocusRing: React.FC<FocusRingProps> = ({
  x,
  y,
  width,
  height,
  startFrame,
  endFrame,
}) => {
  const frame = useCurrentFrame();

  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y,
        width,
        height,
        borderRadius: 28,
        border: "4px solid rgba(34, 211, 238, 0.92)",
        boxShadow: "0 0 0 9999px rgba(2, 8, 23, 0.08), 0 0 44px rgba(34, 211, 238, 0.5)",
        opacity: interpolate(
          frame,
          [startFrame, startFrame + 18, endFrame - 18, endFrame],
          [0, 1, 1, 0],
          {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.bezier(0.16, 1, 0.3, 1),
          },
        ),
        scale: interpolate(frame, [startFrame, startFrame + 18], [1.04, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: Easing.bezier(0.16, 1, 0.3, 1),
          output: "perceptual-scale",
        }),
        pointerEvents: "none",
      }}
    />
  );
};

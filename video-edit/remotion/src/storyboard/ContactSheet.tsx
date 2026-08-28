import {Video} from "@remotion/media";
import {AbsoluteFill, staticFile} from "remotion";

const clips = [
  {name: "01", src: "raw/1.mp4", trimBefore: 240},
  {name: "02", src: "raw/2.mp4", trimBefore: 270},
  {name: "03", src: "raw/3.mp4", trimBefore: 150},
  {name: "04", src: "raw/4.mp4", trimBefore: 390},
  {name: "05", src: "raw/5.mp4", trimBefore: 420},
  {name: "06", src: "raw/6.mp4", trimBefore: 150},
  {name: "07", src: "raw/7.mp4", trimBefore: 150},
];

export const ContactSheet: React.FC = () => {
  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#07111f",
        display: "grid",
        gridTemplateColumns: "repeat(3, 1fr)",
        gap: 18,
        padding: 30,
      }}
    >
      {clips.map((clip) => (
        <div
          key={clip.name}
          style={{
            border: "1px solid rgba(125, 211, 252, 0.35)",
            borderRadius: 18,
            overflow: "hidden",
            position: "relative",
            backgroundColor: "#0f172a",
          }}
        >
          <Video
            src={staticFile(clip.src)}
            trimBefore={clip.trimBefore}
            muted
            objectFit="cover"
            style={{width: "100%", height: "100%"}}
          />
          <div
            style={{
              position: "absolute",
              left: 14,
              top: 14,
              width: 48,
              height: 48,
              borderRadius: 14,
              backgroundColor: "rgba(2, 132, 199, 0.9)",
              color: "white",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontFamily: "Arial, sans-serif",
              fontSize: 22,
              fontWeight: 800,
            }}
          >
            {clip.name}
          </div>
        </div>
      ))}
    </AbsoluteFill>
  );
};

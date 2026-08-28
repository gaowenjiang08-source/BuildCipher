import {readFile, readdir} from "node:fs/promises";
import path from "node:path";
import {ALL_FORMATS, BlobSource, Input} from "mediabunny";

const sourceDirectory = path.resolve(process.argv[2] || "../assets/raw");
const filenames = (await readdir(sourceDirectory))
  .filter((name) => name.toLowerCase().endsWith(".mp4"))
  .sort((left, right) => left.localeCompare(right, undefined, {numeric: true}));

const metadata = [];

for (const filename of filenames) {
  const bytes = await readFile(path.join(sourceDirectory, filename));
  const input = new Input({
    formats: ALL_FORMATS,
    source: new BlobSource(new Blob([bytes])),
  });
  const videoTrack = await input.getPrimaryVideoTrack();
  const audioTrack = await input.getPrimaryAudioTrack();
  const frameRate = videoTrack ? await videoTrack.computeFrameRateMetrics() : null;

  metadata.push({
    filename,
    durationSeconds: Number((await input.computeDuration()).toFixed(3)),
    width: videoTrack ? await videoTrack.getDisplayWidth() : null,
    height: videoTrack ? await videoTrack.getDisplayHeight() : null,
    videoCodec: videoTrack ? await videoTrack.getCodec() : null,
    averageFrameRate: frameRate ? Number(frameRate.averageFrameRate.toFixed(3)) : null,
    hasAudio: Boolean(audioTrack),
    audioCodec: audioTrack ? await audioTrack.getCodec() : null,
  });
}

process.stdout.write(`${JSON.stringify(metadata, null, 2)}\n`);

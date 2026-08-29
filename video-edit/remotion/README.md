# BuildCipher Remotion demo

This project edits the seven BuildCipher screen recordings into one competition demo.

## Deliverable

- Composition: `BuildCipherDemo`
- Resolution: 1920 x 1080
- Frame rate: 30 fps
- Duration: about 119.8 seconds
- Captions: none
- Source audio: muted; the rendered MP4 contains a silent AAC track ready for later voice-over replacement
- Output: `out/BuildCipher-demo-no-captions.mp4`

## Timeline

1. Engineering overview
2. IFC import and verification
3. Trusted collaboration
4. Scheme and code generation
5. Deterministic attack validation
6. Expert mode with an animated nine-node multi-Agent workflow
7. Trusted delivery and export

The seven source clips are also registered as separate Remotion compositions so their timing and camera motion can be edited independently in Studio.

## Preview

```powershell
npm run dev
```

Open the `BuildCipherDemo` composition in Remotion Studio.

## Validate

```powershell
npm run lint
npx remotion compositions src/index.ts
```

## Render

```powershell
npx remotion render src/index.ts BuildCipherDemo out/BuildCipher-demo-no-captions.mp4 --codec=h264 --crf=18 --concurrency=2
```

## Add voice-over later

Replace or mix over the silent audio track in a video editor. Keep the master export at 1920 x 1080, 30 fps, and under two minutes. Captions can then be generated from the final narration.

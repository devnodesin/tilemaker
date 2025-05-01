# README

## Convert GIF to MP4

```bash
ffmpeg -i input.gif -movflags faststart -pix_fmt yuv420p -vf "scale=trunc(iw/2)*2:trunc(ih/2)*2" output.mp4
```

input.gif: your GIF file
output.mp4: your desired MP4 filename

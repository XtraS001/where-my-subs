

## Generate srt file from mp3
1. Run app.py and select mp3 file
    $ py app.py

2. Run the translator
Open PowerShell in the folder containing the script and your sample file.

Translate into Simplified Chinese:
py srt_translator.py sample.srt

The default output is:
sample.zh.srt


Translate into Japanese:
py srt_translator.py sample.srt -t ja


Translate into English:
py srt_translator.py sample.srt -t en


Specify an output filename:
py srt_translator.py sample.srt -t zh -o translated.srt


Change the batch size:
py srt_translator.py sample.srt -t zh -b 3

3. Add srt to mp4 using ffmpeg
- Soft subtitles
> ffmpeg -i input.mp4 -i subtitles.srt -c copy -c:s mov_text output.mp4

- Hard subtitles
> ffmpeg -i input.mp4 -vf "subtitles=subtitles.srt" output.mp4

4. Extract mp3 from mp4
The standard and highest-quality command to extract MP3 audio from an MP4 video using FFmpeg is:
> ffmpeg -i input.mp4 -vn -c:a libmp3lame -q:a 2 output.mp3


Flow
Select mp4
Extract mp3 from mp4
Extract srt from mp3
Translate srt
Add srt to mp4
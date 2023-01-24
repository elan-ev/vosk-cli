# vosk-cli

![Apache 2.0 License](https://img.shields.io/github/license/elan-ev/vosk-cli)
![PyPI](https://img.shields.io/pypi/v/vosk-cli)

This python package serves as an Vosk interface for Opencast. It allows to generate subtitles (WebVTT files) from Video and Audio sources via Vosk.

## Installation

### 1. Install vosk-cli
To install the [latest stable version of vosk-cli](https://pypi.org/project/vosk-cli/), run

```
pip install vosk-cli
```

Alternatively, to install the latest development version, clone this project and inside the project directory run

```
pip install .
```

### 2. Install dependencies

- FFmpeg
- ffprobe

Vosk-cli uses ffprobe to analyze and ffmpeg to preprocess input files.
The easiest way to install ffmpeg is by using a package manager.
If you want or need to install from source, visit
[FFmpeg.org/download.html](https://ffmpeg.org/download.html) and follow the instructions for your operating system.

### 3. Download the language model

Go to [https://alphacephei.com/vosk/models](https://alphacephei.com/vosk/models) and download at least the English language model. The larger models generally yield better results.

You can unzip the folder of the language model into any directory, but it is recommended to create and use a `./models` folder in the project directory.

## Usage

Now you are able to run `vosk-cli -i <input_file_path> -o <output_file_path> -m <model_name_or_path>`.

For example, if there is a `video.mp4` file in your download folder and a model named `vosk-model-en-us-0.22` in the `./models` folder you created, you can run

`vosk-cli -i ~/Downloads/video.mp4 -o text -m vosk-model-en-us-0.22`

This will create a `text.vtt` file (which contains the transcribed captions) in your current directory.

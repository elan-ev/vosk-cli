# vosk-cli

This python package serves as an Vosk interface for Opencast. It allows to generate subtitles (WebVVT files) from Video and Audio sources via Vosk.

## Installation

### 1. Install vosk-cli

Clone this project and run

```
python setup.py install
```

### 2. Install dependencies

- FFmpeg
- `pip install -r requirements.txt`

### 3. Download the language model

Go to `https://alphacephei.com/vosk/models` and download at least the English language model.

Unzip the folder of the language model into `/usr/share/vosk/language/***`, and rename the folder from `***` to `eng` for example.
Please use 3 digit language codes for the directory name. The default and fallback language directory of vosk-cli is `eng`.
The directory name should match the workflow operation field `language-code`.

Now you are able to run `vosk-cli -i <input_file_path> -o <output_file_path> -l <3_digit_language_code>`.

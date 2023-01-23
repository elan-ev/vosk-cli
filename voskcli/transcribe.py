'''
Copyright 2022, ELAN e.V. <kontakt-elan@elan-ev.de>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
'''

from vosk import Model, KaldiRecognizer, SetLogLevel
from webvtt import WebVTT, Caption
from glob import glob
import argparse
import os
import subprocess
import json

SetLogLevel(-1)

MAX_CHARS_PER_LINE = 35
MAX_LINES_IN_PARAGRAPH = 2

EXAMPLE_HELP_SECTION = '''
EXAMPLES

  Start speech recognition using model `vosk-model-en-us-0.22`:

    vosk-cli -m vosk-model-en-us-0.22 -i in.mp4 -o out.vtt

  Start speech recognition, automatically choosing the best model of either
  `vosk-model-en-us-0.22` or `vosk-model-de-0.21`:

    vosk-cli -m vosk-model-en-us-0.22 vosk-model-de-0.21 -i in.mp4 -o out.vtt

  Start speech recognition, automatically choosing the best of all models
  available in the default paths, probing the first 30 seconds of the input
  file:

    vosk-cli -t 30 -m auto -i in.mp4 -o out.vtt
'''


def time_string(seconds):
    '''
    Convert time in seconds to a string containing hours,
    minutes and seconds.

    :param seconds: Time in seconds
    :type seconds: float
    :return: Time in format h:mm:ss.f
    :rtype: str
    '''
    minutes = seconds / 60
    seconds = seconds % 60
    hours = int(minutes / 60)
    minutes = int(minutes % 60)
    return '%i:%02i:%06.3f' % (hours, minutes, seconds)


def model_path(model):
    '''
    Resolve the model path based on the model input argument.
    Resolution happens in the following order:

    1. Use value directly if it is an absolute directory path
    2. Probe for model in the local ./models folder
    3. Probe for model in /usr/share/vosk/models/

    :param model: model command line argument
    :type model: str
    :raises ValueError: If model does not map to a directory
    :return: Path to model directory
    '''
    # Do we have an absolute path to a directory?
    absmodel = os.path.abspath(model)
    if model.startswith(absmodel):
        if os.path.isdir(model):
            return model
        raise ValueError(f'Model path {model} does not exist')

    # Is it a model in the local `models` directory?
    if os.path.isdir('./models/' + model):
        return './models/' + model

    # Check the global models folder
    if os.path.isdir('/usr/share/vosk/models/' + model):
        return '/usr/share/vosk/models/' + model
    raise ValueError('Cannot resolve model path')


def write_captions_paragraph(vtt, paragraph):
    '''
    Append time-coded paragraphs to vtt file.

    :param vtt: Empty or partially filled WebVTT object to write
        transcriptions to
    :type vtt: WebVTT object
    :param paragraph: Transcription data segment representing a single
        paragraph as a list of lists, which contain python dictionaries.
        Each inner list represents a single line of a paragraph,
        while the dictionaries each represent a single word of that line.
        Dictionary entries contain the following keys:

        * conf: Confidence coefficient for the transcribed word (float)
        * end: End time of transcribed word in seconds (float)
        * start: Start time of transcribed word in seconds (float)
        * word: Transcribed word (string)

    :type paragraph: list
    '''
    start = time_string(paragraph[0][0]['start'])
    end = time_string(paragraph[-1][-1]['end'])
    content = ''
    for fin_line in paragraph:
        content += ' '.join([word['word'] for word in fin_line])
        content += '\n'
    content = content[:-1]
    caption = Caption(start, end, content)
    vtt.captions.append(caption)


def write_webvtt_captions(rec_results):
    '''
    Process transcription data.

    Split transcription data into lines of up to MAX_CHARS_PER_LINE chars
    and MAX_LINES_IN_PARAGRAPH lines, append paragraphs to vtt file and
    calculate the average confidence coefficient of the transcription.

    :param rec_results: Complete segmented list of python dictionaries,
        containing transcription data.
        Data includes nested lists of dictionaries,
        which contain time-coded entries for each transcribed word.
        To access these, use key `result`.
    :type rec_results: list
    :return vtt: WebVTT object containing formatted captions
    :rtype vtt: WebVTT object
    :return avg_confidence: Average confidence of the transcription
    :rtype avg_confidence: float
    '''
    vtt = WebVTT()
    line = []
    paragraph = []
    char_count = 0
    confidence = []
    for i, rec_result in enumerate(rec_results):
        result = json.loads(rec_result).get('result')
        if not result:
            continue

        # main logic for the captions "format"
        # (words per line and lines per paragraph)
        for entry in result:
            confidence.append(entry['conf'])
            char_count += len(entry['word'])
            if char_count > MAX_CHARS_PER_LINE and len(line) != 0:
                if len(paragraph) == MAX_LINES_IN_PARAGRAPH:
                    write_captions_paragraph(vtt, paragraph)
                    paragraph = [line]
                    line = [entry]
                    char_count = len(entry['word'])
                    continue
                else:
                    paragraph.append(line)
                    line = [entry]
                    char_count = len(entry['word'])
            else:
                line.append(entry)
                char_count += 1  # add 1 because of whitespace

    # write the remaining words into the captions file
    if len(paragraph) != 0:
        if len(paragraph) < MAX_LINES_IN_PARAGRAPH:
            paragraph.append(line)  # append the last line with remaining words
            line = []
        write_captions_paragraph(vtt, paragraph)
        paragraph = []
    if len(line) != 0:
        paragraph = [line]
        write_captions_paragraph(vtt, paragraph)

    # calculate average confidence coefficient
    avg_confidence = sum(confidence) / len(confidence)

    return vtt, avg_confidence


def transcribe(inputFile, outputFile, model):
    '''
    Produce transcription.

    Create transcription data from inputFile, process data
    and save finished transcription to outputFile.

    :param inputFile: Path to input file
    :type inputFile: str
    :param outputFile: Path to output file
    :type outputFile: str
    :param model: Path to model directory
    :type model: str
    '''
    print(f'Start transcribing with model {model}')
    sample_rate = 16000
    model = Model(model)
    rec = KaldiRecognizer(model, sample_rate)
    rec.SetWords(True)

    command = ['ffmpeg', '-nostdin', '-loglevel', 'quiet', '-i', inputFile,
               '-ar', str(sample_rate), '-ac', '1', '-f', 's16le', '-']
    process = subprocess.Popen(command, stdout=subprocess.PIPE)

    rec_results = []
    while True:
        data = process.stdout.read(4000)
        if len(data) == 0:
            break
        if rec.AcceptWaveform(data):
            rec_results.append(rec.Result())

    rec_results.append(rec.FinalResult())
    vtt, avg_confidence = write_webvtt_captions(rec_results)
    # save webvtt
    print('Finished transcribing with an average confidence '
          f'of {avg_confidence:.2f}. Saving WebVTT file...')
    vtt.save(outputFile)
    print('WebVTT saved.')


def detect_model(inputFile, try_models, probeTime):
    '''
    Detect best model to use.

    :param inputFile: Path to input file
    :type inputFile: str
    :param try_models: List of models to probe
    :type try_models: list of str
    :param probeTime: Probe time in seconds
    :type probeTime: int
    :return: Best model to use
    :type model: str
    '''
    # get all available models if we got the special value auto
    if try_models == ['auto']:
        try_models = glob('./models/*') + glob('/usr/share/vosk/models/*')
    else:
        try_models = [model_path(model) for model in try_models]

    best_model = None
    best_confidence = 0

    # Get input duration
    command = ['ffprobe', '-loglevel', 'quiet', '-show_format', '-of', 'json',
               inputFile]
    process = subprocess.Popen(command, stdout=subprocess.PIPE)
    duration = process.stdout.read(50000)
    duration = json.loads(duration).get('format', {}).get('duration', 0)

    # We want to seek about 10% into the input file
    seek = str(int(float(duration) * 0.1))

    for model in try_models:
        print(f'Probing model {model}')
        sample_rate = 16000
        try:
            rec = KaldiRecognizer(Model(model), sample_rate)
            rec.SetWords(True)
        except Exception:
            print('Does not seem to be a proper model. Skipping.')
            continue

        command = ['ffmpeg', '-nostdin', '-loglevel', 'quiet', '-ss', seek,
                   '-i', inputFile, '-t', str(probeTime), '-ac', '1',
                   '-ar', str(sample_rate), '-f', 's16le', '-']
        process = subprocess.Popen(command, stdout=subprocess.PIPE)

        rec_results = []
        while True:
            data = process.stdout.read(4000)
            if len(data) == 0:
                break
            if rec.AcceptWaveform(data):
                rec_results.append(rec.Result())

        rec_results.append(rec.FinalResult())

        confidence = []
        for rec_result in rec_results:
            for entry in json.loads(rec_result).get('result', []):
                confidence.append(entry['conf'])
        avg_confidence = sum(confidence) / len(confidence)
        print(f'Detected confidence: {avg_confidence}')

        if avg_confidence > best_confidence:
            best_confidence = avg_confidence
            best_model = model

    return os.path.abspath(best_model)


def match_language_to_model(lang):
    '''Try mapping a specified language to a language model

    :param lang: The language string to map
    :type lang: str
    :return: Absolute path to language model
    '''
    # check if we have an old language dir for this language first
    language_dir = f'/usr/share/vosk/language/{lang}/'
    if os.path.isdir(language_dir):
        print(f'Mapping language option to model {language_dir}')
        return language_dir

    # Map some common language codes
    language_mappings = {
            'eng': 'en',
            'deu': 'de',
            'ger': 'de',
            'spa': 'es',
            'zho': 'cn',
            'fra': 'fr',
            'rus': 'ru',
            'por': 'pt',
            'tur': 'tr'}
    lang = language_mappings.get(lang, lang)

    # Map to a 2 character code
    lang = lang[:2]

    # Try finding a matching module
    modules = glob(f'/usr/share/vosk/models/*-{lang}-*') \
        or glob(f'./models/*-{lang}-*')

    if not len(modules):
        raise ValueError('Unable to map language to model')

    model = os.path.abspath(modules[0])
    print(f'Mapping language {lang} to model {model}')
    return model


def main():
    '''
    Define arguments for command line usage and carry out transcription.
    '''
    parser = argparse.ArgumentParser(
        description='Creates WebVTT from media file using speech recognition.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=EXAMPLE_HELP_SECTION
    )
    parser.add_argument('-i', type=str, dest='inputFile', required=True,
                        help='Path to the media file to transcribed.')
    parser.add_argument('-o', type=str, dest='outputFile', required=True,
                        help='The path to the output file.')
    parser.add_argument('-l', type=str, dest='language', nargs='*',
                        help='The language code. It determines which model '
                        'will be used to transcribe the media file. '
                        'You can use multiple values or auto and vosk-cli '
                        'will try to determine the best model to use. '
                        'DEPRECATED: Use model (-m) instead.')
    parser.add_argument('-m', '--model', type=str, dest='model', nargs='*',
                        help='The language model to use for transcribing the '
                        'media file. Value will be checked in the following '
                        'order: 1. value as system path. 2. Value in local '
                        './model folder. 3. Value in /usr/share/vosk/models/.'
                        'If multiple values to this option are specified, '
                        'vosk-cli will automatically detect the best of the '
                        'specified models. If the special value `auto` is '
                        'given, vosk-cli will detect the best of all modules '
                        'in the default paths.')
    parser.add_argument('-t', '--probe-time', dest='probeTime', default=60,
                        type=int, help='Time in seconds to probe the input.')
    args = parser.parse_args()

    inputFile = args.inputFile
    outputFile = args.outputFile
    model = args.model or []

    # map languages to models
    if args.language:
        if args.language == ['auto']:
            model = ['auto']
        else:
            model = [match_language_to_model(lang) for lang in args.language]

    if model == ['auto'] or len(model) > 1:
        model = detect_model(inputFile, model, args.probeTime)
    else:
        model = model_path(args.model[0])

    transcribe(inputFile, outputFile, model)

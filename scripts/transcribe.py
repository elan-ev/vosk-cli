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
from argparse import ArgumentParser
import os
import subprocess
import json

SetLogLevel(-1)

MAX_CHARS_PER_LINE = 35
MAX_LINES_IN_PARAGRAPH = 2


def time_string(seconds):
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
    vtt = WebVTT()
    line = []
    paragraph = []
    char_count = 0
    for i, rec_result in enumerate(rec_results):
        result = json.loads(rec_result).get('result')
        if not result:
            continue

        # main logic for the captions "format"
        # (words per line and lines per paragraph)
        for entry in result:
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

    return vtt


def transcribe(inputFile, outputFile, model):

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
    vtt = write_webvtt_captions(rec_results)

    # save webvtt
    print('Finished transcribing. Saving WebVTT file...')
    vtt.save(outputFile)
    print('WebVTT saved.')
    # print(vtt.content)


def main():
    parser = ArgumentParser(description='Creates a WebVTT file out of a '
                            'media file with an audio track.')
    parser.add_argument('-i', type=str, dest='inputFile', required=True,
                        help='Path to the media file to transcribed.')
    parser.add_argument('-o', type=str, dest='outputFile', required=True,
                        help='The path to the output file.')
    parser.add_argument('-l', type=str, dest='language', required=False,
                        help='The language code. It determines which model '
                        'will be used to transcribe the media file. '
                        'DEPRECATED: Use model (-m) instead.')
    parser.add_argument('-m', '--model', type=str, dest='model',
                        help='The language model to use for transcribing the '
                        'media file. Value will be checked in the following '
                        'order: 1. value as system path. 2. Value in local '
                        './model folder. 3. Value in /usr/share/vosk/models/.')
    args = parser.parse_args()

    inputFile = args.inputFile
    outputFile = args.outputFile
    if args.language:
        model = '/usr/share/vosk/language/' + args.language
        print(f'WARNING: Mapping deprecated language option to model {model}')
    else:
        model = args.model
    model = model_path(model)

    transcribe(inputFile, outputFile, model)

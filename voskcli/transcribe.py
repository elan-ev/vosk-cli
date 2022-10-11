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
from recasepunc.recasepunc import CasePuncPredictor
import sys
import voskcli
import os
import subprocess
import json

SetLogLevel(-1)

MAX_CHARS_PER_LINE = 35
MAX_LINES_IN_PARAGRAPH = 2


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


def write_webvtt_captions(result_list):
    '''
    Process transcription data.

    Split transcription data into lines of up to MAX_CHARS_PER_LINE chars
    and MAX_LINES_IN_PARAGRAPH lines and append paragraphs to vtt file.

    :param rec_results: Complete segmented list of python dictionaries,
        containing transcription data.
        Data includes nested lists of dictionaries,
        which contain time-coded entries for each transcribed word.
        To access these, use key `result`.
    :type rec_results: list
    :return: WebVTT object containing formatted captions
    :rtype: WebVTT object
    '''
    vtt = WebVTT()
    line = []
    paragraph = []
    char_count = 0

    for i, result in enumerate(result_list):
        # main logic for the captions "format"
        # (words per line and lines per paragraph)
        char_count += len(result['word'])
        if char_count > MAX_CHARS_PER_LINE and len(line) != 0:
            if len(paragraph) == MAX_LINES_IN_PARAGRAPH:
                write_captions_paragraph(vtt, paragraph)
                paragraph = [line]
                line = [result]
                char_count = len(result['word'])
                continue
            else:
                paragraph.append(line)
                line = [result]
                char_count = len(result['word'])
        else:
            line.append(result)
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


def transcribe(inputFile, outputFile, model, punc):
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
    result_list = []
    case_result_list = []
    while True:
        data = process.stdout.read(4000)
        if len(data) == 0:
            break
        if rec.AcceptWaveform(data):
            rec_results.append(rec.Result())

    rec_results.append(rec.FinalResult())
    print('Finished transcribing...')
    print(rec_results)

    if punc != "":
        print(f'Start punctuating with model {punc}')
        # Punctuation
        # Load text from json
        text = ''
        for rec_result in rec_results:
            result = json.loads(rec_result).get('result')
            if not result:
                continue
            text += ' '.join([entry['word'] for entry in result])+' '

        print(text)
        print("==================================================")

        # Predicts Punctuation of text
        # Manipulate main to be able to load model
        old_main = sys.modules['__main__']
        sys.modules['__main__'] = voskcli
        predictor = CasePuncPredictor(punc + '/checkpoint')
        sys.modules['__main__'] = old_main

        # Beginning punctuation
        tokens = list(enumerate(predictor.tokenize(text)))
        case_result = ""
        predicted = predictor.predict(tokens, lambda x: x[1])
        for token, case_label, punc_label in predicted:
            map_label = predictor.map_case_label(token[1], case_label)
            prediction = predictor.map_punc_label(map_label, punc_label)
            if token[1][0] != '#' and prediction != '-' and not case_result.endswith('-'):
                case_result = case_result + ' ' + prediction
            else:
                case_result = case_result + prediction
        print(case_result)
        case_result_list = case_result.split(" ")
        print('Finished punctuating...')
    else:
        print('No punctuating wished...')

    # Creating array for next function
    word = 1
    for rec_result in rec_results:
        result = json.loads(rec_result).get('result')
        if not result:
            continue
        if punc != "":
            for entry in result:
                entry['word'] = case_result_list[word]
                word += 1
        result_list += result
    print(result_list)
    vtt = write_webvtt_captions(result_list)

    # save WebVTT
    print('Finished writing. Saving WebVTT file...')
    vtt.save(outputFile)
    print('WebVTT saved.')
    # print(vtt.content)


def main():
    '''
    Define arguments for command line usage and carry out transcription.
    '''
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
    parser.add_argument('-p', '--punctuation', type=str, dest='punc',
                        help='The punctuation model to use for punctuate the '
                        'media file. Value will be checked in the following '
                        'order: 1. value as system path. 2. Value in local '
                        './model folder. 3. Value in /usr/share/vosk/models/.')
    args = parser.parse_args()

    inputFile = args.inputFile
    puncuationFile = args.punc
    outputFile = args.outputFile
    if args.language:
        model = '/usr/share/vosk/language/' + args.language
        print(f'WARNING: Mapping deprecated language option to model {model}')
    else:
        model = args.model
    model = model_path(model)
    punc = ""
    if puncuationFile:
        punc = model_path(puncuationFile)

    transcribe(inputFile, outputFile, model, punc)

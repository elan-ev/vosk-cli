#!/usr/bin/env python3

from vosk import Model, KaldiRecognizer, SetLogLevel
from webvtt import WebVTT, Caption
from argparse import ArgumentParser
from recasepunc.utils import CasePuncPredictor
import os
import subprocess
import json

language_dir_path = "/usr/share/vosk/language/"
default_language = "eng"
SetLogLevel(-1)

MAX_CHARS_PER_LINE = 35
MAX_LINES_IN_PARAGRAPH = 2


def time_string(seconds):
    minutes = seconds / 60
    seconds = seconds % 60
    hours = int(minutes / 60)
    minutes = int(minutes % 60)
    return '%i:%02i:%06.3f' % (hours, minutes, seconds)


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


def transcribe(inputFile, outputFile, language):
    default_language_dir_path = language_dir_path + default_language
    chosen_language_dir_path = language_dir_path + language
    chosen_model = None

    # checks if there is a model directory with a language code as the name
    if not os.path.exists(chosen_language_dir_path):
        print('Did not find language model directory "%s".'
              % chosen_language_dir_path)
        print('Using default language model directory "%s".'
              % default_language_dir_path)
        if not os.path.exists(default_language_dir_path):
            print('Did not found default model directory "%s".'
                  % default_language_dir_path)
            exit(1)
        else:
            chosen_model = default_language_dir_path
    else:
        chosen_model = chosen_language_dir_path

    print('Start transcribing...')
    sample_rate = 16000
    model = Model(chosen_model)
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
    print('Finished transcribing...')
    print('Start punctuating...')

    # Punctuation
    # Load text from json
    text = ''
    for i, rec_result in enumerate(rec_results):
        result = json.loads(rec_result).get('result')
        if not result:
            continue
        text += ' '.join([entry['word'] for entry in result])

    # Predicts Punctuation of text
    predictor = CasePuncPredictor('scripts/checkpoint', lang="de")
    tokens = list(enumerate(predictor.tokenize(text)))
    case_result = ""
    for token, case_label, punc_label in predictor.predict(tokens, lambda x: x[1]):
        prediction = predictor.map_punc_label(predictor.map_case_label(token[1], case_label), punc_label)
        if token[1][0] != '#':
            case_result = case_result + ' ' + prediction
        else:
            case_result = case_result + prediction

    # Stores it back to json
    case_result_list = case_result.split(" ")
    case_rec_result = []
    word = 1
    for i, rec_result in enumerate(rec_results):
        result = json.loads(rec_result).get('result')
        if not result:
            continue
        for entry in result:
            entry['word'] = case_result_list[word]
            word += 1
        case_rec_result.append('{ "result" : ' + str(result).replace("'", '"') + '}')

    print('Finished punctuating...')

    vtt = write_webvtt_captions(case_rec_result)

    # save webvtt
    print('Finished writing. Saving WebVTT file...')
    vtt.save(outputFile)
    print('WebVTT saved.')


def main():
    parser = ArgumentParser(description='Creates a WebVTT file out of a '
                            'media file with an audio track.')
    parser.add_argument('-i', type=str, dest='inputFile', required=True,
                        help='Path to the media file to transcribed.')
    parser.add_argument('-o', type=str, dest='outputFile', required=True,
                        help='The path to the output file.')
    parser.add_argument('-l', type=str, dest='language', required=True,
                        help='The language code. It determines which model '
                        'will be used to transcribe the media file.')
    args = parser.parse_args()

    inputFile = args.inputFile
    outputFile = args.outputFile
    language = args.language

    transcribe(inputFile, outputFile, language)

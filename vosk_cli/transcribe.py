#!/usr/bin/env python3

from vosk import Model, KaldiRecognizer, SetLogLevel
from webvtt import WebVTT, Caption
from argparse import ArgumentParser
import os
import subprocess
import json
import textwrap

default_language = "eng"
SetLogLevel(-1)
WORDS_PER_LINE = 7


def timeString(seconds):
    minutes = seconds / 60
    seconds = seconds % 60
    hours = int(minutes / 60)
    minutes = int(minutes % 60)
    return '%i:%02i:%06.3f' % (hours, minutes, seconds)


def transcribe(inputFile, outputFile, language, vosk_root_directory):

    language_dir_path = vosk_root_directory + "/language_packs/" + language
    default_language_dir_path = vosk_root_directory + "/language_packs/"\
        + default_language
    choosen_model = None

    # checks if there is a model directory with a language code as the name
    # ('de' for example)
    if not os.path.exists(language_dir_path):
        print('Did not find language model directory "%s".'
              % language_dir_path)
        print('Using default language model directory "%s".'
              % default_language_dir_path)
        if not os.path.exists(default_language_dir_path):
            print('Did not found default model directory "%s".'
                  % default_language_dir_path)
            exit(1)
        else:
            choosen_model = default_language_dir_path
    else:
        choosen_model = language_dir_path

    print('Starting transcription with language model "%s"' % language)
    sample_rate = 16000
    model = Model(choosen_model)
    rec = KaldiRecognizer(model, sample_rate)
    rec.SetWords(True)

    command = ['ffmpeg', '-nostdin', '-loglevel', 'quiet', '-i', inputFile,
               '-ar', str(sample_rate), '-ac', '1', '-f', 's16le', '-']
    process = subprocess.Popen(command, stdout=subprocess.PIPE)

    results = []
    while True:
        data = process.stdout.read(4000)
        if len(data) == 0:
            break
        if rec.AcceptWaveform(data):
            results.append(rec.Result())
    results.append(rec.FinalResult())
    vtt = WebVTT()
    for i, res in enumerate(results):
        words = json.loads(res).get('result')
        if not words:
            continue

        start = timeString(words[0]['start'])
        end = timeString(words[-1]['end'])
        content = ' '.join([w['word'] for w in words])

        caption = Caption(start, end, textwrap.fill(content))
        vtt.captions.append(caption)

    # print(vtt.content)
    # save webvtt
    vtt.save(outputFile)


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

    vosk_root_directory = os.path.dirname(os.path.realpath(__file__))

    inputFile = args.inputFile
    outputFile = args.outputFile
    language = args.language

    transcribe(inputFile, outputFile, language, vosk_root_directory)

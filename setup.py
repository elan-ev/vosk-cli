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

from setuptools import setup
import os


def read(filename):
    path = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(path, filename), encoding='utf-8') as f:
        return f.read()


description_text = 'A command line interface for Vosk. '\
    'It generates subtitles (WebVTT files) from video and audio sources.'

setup(
    name='vosk-cli',
    version='0.2',
    description=description_text,
    long_description=description_text,
    url='https://github.com/elan-ev/vosk-cli',
    author='Martin Wygas',
    author_email='mwygas@uos.de',
    license='Apache-2.0',
    packages=['voskcli'],
    license_files=('LICENSE'),
    include_package_data=True,
    install_requires=read('requirements.txt').split(),
    entry_points={
        'console_scripts': ['vosk-cli = voskcli.transcribe:main'],
    })

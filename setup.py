from setuptools import setup
import os


def read(filename):
    path = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(path, filename), encoding='utf-8') as f:
        return f.read()


description_text = 'A command line interface for Vosk. '\
    'It generates subtitles (WebVVT files) from video and audio sources.'

setup(
    name='vosk-cli',
    version='0.1',
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

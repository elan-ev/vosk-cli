from setuptools import setup

description_text = 'This project serves as an Vosk interface for Opencast. It allows to generate subtitles (WebVVT files) from video and audio sources via Vosk.'

setup(name='vosk_cli',
      version='0.1',
      description=description_text,
      long_description=description_text,
      url='https://github.com/elan-ev/vosk-cli',
      author='Martin Wygas',
      author_email='mwygas@uos.de',
      license='Apache-2.0',
      packages=['vosk_cli'],
      license_files = ('LICENSE'),
      install_requires=[
		    'vosk>=0.3.30',
		    'webvtt-py>=0.4.6'
      ],
      include_package_data = True,
      zip_safe=False,
      entry_points = {
        'console_scripts': ['vosk-cli=vosk_cli.transcribe:main'],
    }
)

from setuptools import setup

description_text = 'This project serves as an Vosk interface for Opencast. It allows to generate subtitles (WebVVT files) from video and audio sources via Vosk.'

setup(name='vosk-cli',
      version='0.1',
      description=description_text,
      long_description=description_text,
      url='https://github.com/elan-ev/vosk-cli',
      author='Martin Wygas',
      author_email='mwygas@uos.de',
      license='Apache-2.0',
      packages=['transcriber', 'recasepunc'],
      license_files=('LICENSE'),
      include_package_data=True,
      zip_safe=False,
      entry_points={
          'console_scripts': ['vosk-cli=transcriber.utils:main'],
      })

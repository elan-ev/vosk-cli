# vosk-cli

This python package serves as an Vosk interface for Opencast, to generate subtitles (WebVVT files) from Video and Audio sources.

## installation

Go to the Website `https://alphacephei.com/vosk/models` to download a language model. 

Unzip the folder into the `language_pack` directory and rename it to the corresponding language. The default language directory vosk-cli will search for is `eng`.

Go into the root directory and run `pip install . `

Now you are able to run `vosk-cli -i <input_file_path> -o <output_file_path> -l <name_of_the_language_model_directory>`

The fallback for `name_of_the_language_model_directory` is `eng`.

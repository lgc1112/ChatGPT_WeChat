import logging

import azure.cognitiveservices.speech as speechsdk


# This example requires environment variables named "SPEECH_KEY" and "SPEECH_REGION"
cog_host = "https://koreacentral.api.cognitive.microsoft.com/sts/v1.0/issuetoken"
# speech_config = speechsdk.SpeechConfig(subscription="fd73253cf93e4834a976d11e2efe4509", region="eastus")
# speech_config = speechsdk.SpeechConfig(subscription="50a453ac1a3a47af9dd53094e9be3a23", region="koreacentral")
speech_config = speechsdk.SpeechConfig(subscription="50a453ac1a3a47af9dd53094e9be3a23", endpoint=cog_host)
speech_config.set_property(speechsdk.PropertyId.Speech_LogFilename, "LogfilePathAndName")
# audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)
audio_config = speechsdk.audio.AudioOutputConfig(filename=f"voice/q1qq.mp3")
# speech_config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3)

# The language of the voice that speaks.
speech_config.speech_synthesis_voice_name="zh-CN-YunxiNeural"
# speech_config.speech_synthesis_voice_name="en-US-AriaNeural"

speech_config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3)
speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)

# Get text from the console and synthesize to the default speaker.
print("Enter some text that you want to speak >")
text = " is a stupid dog"
text = "林海萍是小傻狗"

speech_synthesis_result = speech_synthesizer.speak_text_async(text).get()

if speech_synthesis_result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
    print("Speech synthesized for text [{}]".format(text))
elif speech_synthesis_result.reason == speechsdk.ResultReason.Canceled:
    cancellation_details = speech_synthesis_result.cancellation_details
    print("Speech synthesis canceled: {}".format(cancellation_details.reason))
    if cancellation_details.reason == speechsdk.CancellationReason.Error:
        if cancellation_details.error_details:
            print("Error details: {}".format(cancellation_details.error_details))
            print("Did you set the speech resource key and region values?")


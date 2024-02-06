import subprocess, re, sys

# nix-shell -p python311Packages.paho-mqtt python311Packages.pyaudio python311Packages.numpy python311Packages.faster-whisper espeak-classic

import pyaudio
import wave

import numpy


import faster_whisper

model = faster_whisper.WhisperModel("small.en")


CHUNK = 1024 
FORMAT = pyaudio.paInt16 #paInt8
CHANNELS = 2 
RATE = 44100 #sample rate
RECORD_SECONDS = 4
WAVE_OUTPUT_FILENAME = "recordingW.wav"

RATE, CHUNK = 16000, 2000 
p = pyaudio.PyAudio()

noisedetectionthreshold = 4000

import paho.mqtt.client as paho
broker, port = "mosquitto.doesliverpool.xyz", 1883
def on_publish(client, userdata, result):
    print(" -- data published to mqtt \n")
    pass
def on_message(client, userdata, message):
    print("{'" + message.payload.decode() + "', " + message.topic + "}")
    proc = subprocess.Popen(["espeak", "-p", "60", "-v", "en-german-5", message.payload.decode() ], stdout=subprocess.PIPE)
    print("endproc")

client1 = paho.Client("control1")
client1.on_publish = on_publish
client1.on_message = on_message
client1.connect(broker, port)
client1.subscribe("radio/speak")

def whispertomqtt():
    segments, info = model.transcribe(WAVE_OUTPUT_FILENAME)
    print(info)
    for s in segments:
        x = s.text.strip()
        if x:
            print("*** TRANS", x)
            ret = client1.publish("radio/whisper", x) 
            print("ret", ret)
        client1.loop(0)


def waitgetradio():
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
    i = 0
    sm = 0
    while True:
        data = stream.read(CHUNK) # 2 bytes(16 bits) per channel
        s = numpy.frombuffer(data, dtype=numpy.int16)
        ssm = max(s)
        if ssm > noisedetectionthreshold:
            break
        i += 1
        sm = max(sm, ssm)
        if (i%8) == 0:
            print("waiting", sm)
            sm = 0
        client1.loop(0)
    print("record now")
    frames = [ data ]
    lastnoise = len(frames)-1
    while len(frames) < 80 and len(frames) < lastnoise + 16:
        data = stream.read(CHUNK)
        s = numpy.frombuffer(data, dtype=numpy.int16)
        if (len(frames)%8) == 0:
            print("recording", len(frames)//8)
        frames.append(data)
        if max(s) > 700:
            lastnoise = len(frames)-1
            print("lastnoise", lastnoise/8)
        client1.loop(0)
    print("* done recording")

    stream.stop_stream()
    stream.close()
    #p.terminate()

    wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()





while 1:
    waitgetradio()
    whispertomqtt()


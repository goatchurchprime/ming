import subprocess, re, sys

# nix shell github:nixos/nixpkgs/nixos-unstable#openai-whisper-cpp
# nix-shell -p python311Packages.paho-mqtt
# nix-shell -p python311Packages.pyaudio
# nix-shell -p python311Packages.numpy

# nix-shell -p python311Packages.paho-mqtt python311Packages.pyaudio python311Packages.numpy

import pyaudio
import wave

import numpy

CHUNK = 1024 
FORMAT = pyaudio.paInt16 #paInt8
CHANNELS = 2 
RATE = 44100 #sample rate
RECORD_SECONDS = 4
WAVE_OUTPUT_FILENAME = "recording.wav"


import paho.mqtt.client as paho
broker = "mosquitto.doesliverpool.xyz"
port = 1883
def on_publish(client,userdata,result):             #create function for callback
    print(" -- data published to mqtt \n")
    pass
client1 = paho.Client("control1")                           #create client object
client1.on_publish = on_publish                          #assign function to callback
client1.connect(broker, port)                                 #establish connection


def whispertomqtt():
    if 1:
        proc = subprocess.Popen(["whisper-cpp", "-m", "ggml-small.en.bin", "-otxt", "-f", WAVE_OUTPUT_FILENAME], stdout=subprocess.PIPE)
        print(proc)
        for x in proc.stdout:
            x = x.decode()
            print(x)

    for x in open(WAVE_OUTPUT_FILENAME+".txt"):
        x = re.sub(".*\r", "", x)
        x = re.sub("\[.*?\]", "", x)
        x = re.sub("\(.*?\)", "", x)
        x = re.sub("\*.*?\*", "", x)

        # Remove leading and trailing whitespaces, including newlines
        x = x.strip()

        # Check if the resulting string is not empty before printing
        if x:
            print("*** TRANS", x)
            ret = client1.publish("radio/whisper", x) 
            print("ret", ret)
        client1.loop(0)


def waitgetradio():
    RATE, CHUNK = 16000, 2000 

    p = pyaudio.PyAudio()

    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK) #buffer

    i = 0
    sm = 0
    while True:
        data = stream.read(CHUNK) # 2 bytes(16 bits) per channel
        s = numpy.frombuffer(data, dtype=numpy.int16)
        ssm = max(s)
        if ssm > 4000:
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
    while len(frames) < 160 and len(frames) < lastnoise + 16:
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
    p.terminate()

    wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()





while 1:
    waitgetradio()
    whispertomqtt()


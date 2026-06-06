# Video Stream Processing - Radixweb

> Developed efficient code to identify an OCR method that works well with a variety of video sources.

**Source:** https://radixweb.com/case-studies/video-stream-processing

---

# Video Stream Processing

Radixweb was associated with an Italy-based client, who was akin to find a partner to help them with video and image processing solution for their existing system.

## The Problem

The client had two input video streams running on RTMP/HTTP video streaming server.

First, live video streaming had text code (ex. 000321FG4) masked on the video at any time and for any time duration.

Second stream is a simple black stream with same code masked on it at same position, same time and for same duration as live video stream.

The main objective of this project was to remove the masked code along with the code text detection using OCR in the live streaming video, re-encoding and re-streaming the resultant video on an RTMP server.

## The Solution

We created a Linux based C++ application that took various inputs in command line.

  * Iterate each frame in black input stream using FFmpeg library.
  * We work on LAMP configuration for development and the Linux Live CD provided us with the much need SDK that serve all its needs well.
  * For each frame, we processed them using OpenCV to detect text code in the frame image. We applied OCR on detected code to verify that the correct code is processed. We applied algorithms and configurations to the OpenCV provided OCR to improve the results.
  * When the code is detected, we created a blurred mask with the help of surrounding background for code and overlaid the mask on actual live streaming input wide. The team also applied different processing using OpenCV to blur the code area so that the code cannot be read in the video.
  * After the code is processed and removed from live video, we re-encoded frames into H.264 and streamed them live on RTMP server as final output video using FFmpeg. Syncing audio stream from input live stream with processed video stream was the crucial requirement to be fulfilled.
  * We re-encoded the output stream to different video resolution based on an input provided to the application.

## Highlights

Get in Touch

Let’s discuss your project and build something extraordinary

Start Conversation

We're offline

Leave a message

 __
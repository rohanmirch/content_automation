from dataclasses import dataclass
from typing import List
import string
import random
import os
import pprint
import json
import requests
import urllib.request
from datetime import datetime, date, timedelta
import upload_video

import pandas as pd
import numpy as np
import moviepy.editor as mpy
import moviepy.video.fx as vfx
from moviepy.video.VideoClip import ImageClip, TextClip
from moviepy.video.compositing import CompositeVideoClip
from moviepy.video.compositing.CompositeVideoClip import *
from moviepy.editor import *
from moviepy.audio.fx.all import *
from apiclient.http import MediaFileUpload

from gtts import gTTS


PEXEL_API_KEY = '563492ad6f917000010000011d2a823f8f9f41ecbd8ed2f5bcc381ab'
AUDIO_FPS = 44100
PUBLISH_TIME = 17 # 5 pm
UTC_TIME_DIFF = 8 # UTC is 8 hours ahead

# Youtube info for facts101 channel
CHANNEL_ID = "UCuvWt72OMRF5xp6H9VBdmLw"
OWNER_ID = "uvWt72OMRF5xp6H9VBdmLw" # Not needed


media_path = "../media/"
backgrounds_path = media_path + "backgrounds/"
audio_path = "../audio/"
clips_path = "../clips/"


class Video:
	def __init__(self, 
				 id = 0, 
				 post_date = None,
				 created_at = None,
				 uploaded_at = None,
				 music_file = "",
				 background = "",
				 video_file = "",
				 content = dict(title="",description="",texts=[],tags=[])):

		self.id = int(id)
		self.post_date = datetime.combine(post_date, datetime.min.time())
		self.created_at = created_at
		self.uploaded_at = uploaded_at
		self.music_file = music_file
		self.background = background
		self.video_file = f"video_{int(id)}.mp4"
		self.content = content


	def __str__(self):
		return f"{vars(self)}"

	def get_bg_clip_pexels(self, url):
		'''Gets the background clip from pexels given the URL, and saves the 
		   downloaded clip into the media/bg_clips folder. Then return background_file.
		   If the clip has already been downloaded, then just return background_file.'''
		
		pexel_video_id = int(url.replace("/", "").split("-")[-1])
		background_file = url.split("/")[-2] + ".mp4"
		#print(f'pexel_video_id: {pexel_video_id}')

		# If the file is already downloaded, we can end the function
		if os.path.exists(backgrounds_path + background_file):
			print(f"{background_file} already downloaded")
			return background_file
		
		# Get video info from Pexels API
		api_url = 'https://api.pexels.com/videos/videos/'
		headers = { 'content-type': 'application/json',
					'Authorization': PEXEL_API_KEY, 
				   }

		response = requests.get(f'{api_url}{pexel_video_id}', headers=headers)
		resp = json.loads(response.text)
		#pprint.pprint(resp)

		# Get the url to the video file that is the correct size.
		# Assumes a vertical video and seeks highest resolution (1080x1920)
		# TODO: Video creation code still doesn't work for 720x1080 because final size is the background size
		v_files = resp['video_files']
		v_link = ""
		v_links = [v["link"] for v in v_files]
		for v in v_files:
			if v["quality"] == "hd":
				v_link = v["link"]
				if  v["width"] == 1080:
					break

		# Download URL
		if v_link == "":
			print("No pexels video download link found from given URL")
		urllib.request.urlretrieve(v_link, backgrounds_path + background_file)
		print(f"Downloaded {background_file}")
		return background_file

	def get_bg_clip(self):
		''' Retrieved the background clip. Can either be an mp4 file or a pexels url.
			If self.background a pexels url, then it first downloads it.'''
		
		background_file = self.background
		select_random_start = True
		if "www.pexels.com" in self.background:
			# Call pexels helper function to process url
			background_file = self.get_bg_clip_pexels(self.background)
			select_random_start = False

	    # Open the background clip file
		bg_clip = mpy.VideoFileClip(backgrounds_path + background_file)
		duration = bg_clip.duration
		fps = bg_clip.fps
		width, height = bg_clip.size
		print("Retrieved background clip:")
		print(f"Width: {width}, Height {height}, fps: {fps},  duration: {duration}s")
		
		# Pre-processing
		bg_clip = bg_clip.without_audio()
		if select_random_start:
			bg_clip = bg_clip.subclip(random.random()*(bg_clip.duration-60))
		# Make infitely loopable in case it ends up being shorter than the text
		bg_clip = bg_clip.fx(vfx.make_loopable, 1).fx(vfx.loop)

		return bg_clip, fps, width, height


	def create_video(self, save_video = False):
		''' Creates and edits the video '''

		# Get music and background clip
		music = self.get_music_clip()
		bg_clip, fps, width, height = self.get_bg_clip()

		# Create text clip
		text_clip = self.__create_text_clip(self.content["texts"], width)		

		# Combine text clip with background video
		clip = CompositeVideoClip([bg_clip, text_clip.set_position(("center",height*0.17))], use_bgclip = True)

		# Add music to clip
		music = music.set_duration(clip.duration).fx(audio_fadein, 0.4)
		comp_audio = mpy.CompositeAudioClip([music, clip.audio.fx(volumex, 1.4)])
		comp_audio = comp_audio.set_duration(clip.duration).set_fps(AUDIO_FPS)
		clip = clip.set_audio(comp_audio)
		print("final_clip duration {}".format(clip.duration))

		if save_video:
			try:
				clip.write_videofile(clips_path + self.video_file, audio_codec='aac')
				self.created_at = datetime.now().replace(second=0, microsecond=0)
				print(f"Saved {clips_path + self.video_file}")
			except Exception as e:
				print("Error saving video: " + e)
		
	def __create_text_clip(self, texts, width):
		''' Creates a clip sequentially showing texts with a voiceover narrating each one'''
		text_clips = []
		title_is_first = True
		for i, t in enumerate(texts):
			size = 78
			bg_color = "transparent"
			color = "white" 
			stroke_width = 3
			stroke_color = "black"
			font='proximanova-extrabold'
			kerning=-4
			if i == 0 and title_is_first:
				size = 92
				bg_color = "AntiqueWhite"
				color = "black"
				stroke_width = 3
				stroke_color = "black"
				font='proximanova-semibold'
				kerning=-2
	
			text_width = width-175             
			t_clip = TextClip(txt = t, 
							size=(text_width, None), # Height will be auto-determined
							color=color, 
							bg_color=bg_color,
							fontsize=size, 
							font=font,
							stroke_color=stroke_color, 
							stroke_width=stroke_width, 
							method='caption', 
							kerning=kerning, 
							align='center')
			text_height = t_clip.size[1]
			# Add speech
			speech = gTTS(t, lang='en')
			speech.save(audio_path + f"speech_{i}.mp3")
			speech_clip = mpy.AudioFileClip(audio_path + f"speech_{i}.mp3")
			
			# Add a 1 second pause at the end of each speech clip
			empty_clip = AudioClip(lambda t: 0, duration=0.75)
			speech_clip = concatenate_audioclips([speech_clip, empty_clip]).set_fps(AUDIO_FPS)
			t_clip = t_clip.set_audio(speech_clip).set_duration(speech_clip.duration)
		   
			# Add effects
			# t_clip = t_clip.fx(vfx.fadeout, 0.75)
			#t_clip = t_clip.set_opacity(0.85)

			text_clips.append(t_clip)
			
		
		text_clip = mpy.concatenate_videoclips(text_clips, method = "compose", padding = 0.5)
		text_clip.audio = text_clip.audio.set_fps(AUDIO_FPS)
		print(f"text clip duration {text_clip.duration}")
		return text_clip

	def upload_to_youtube(self, schedule = True):
		# Create a YouTube service object
		youtube = upload_video.get_authenticated_service()

		# Set the video file and metadata
		title = self.content["title"]
		description = self.content["description"]
		tags = self.content["tags"]

		# Create the request body
		request_body = {
			'snippet': {
				'title': title,
				'description': description,
				'tags': tags,
				'channelId': CHANNEL_ID
			},
			'status': {
				'privacyStatus': 'private', # private, unlisted, public
				#'publishAt':  iso_datetime  # can be set if privacyStatus=private
				'selfDeclaredMadeForKids' : False
			}
		}

		video_file_path = clips_path + self.video_file
		if not os.path.exists(video_file_path):
			raise Exception (f"{video_file_path} doesn't exist.")

		# Schedule post time
		if self.post_date is not None:
			# publishAt takes UTC time, which is 8 hours ahead of PT
			rand_min = random.randint(40,57)
			scheduled_ts = self.post_date + timedelta(hours = UTC_TIME_DIFF + PUBLISH_TIME, minutes=rand_min)
			request_body["status"]["publishAt"] = scheduled_ts.isoformat()
			print(f"scheduled for UTC {scheduled_ts.isoformat()}")
			
			# TODO: Maybe update post_date if we post later than expected

		# Create the request
		request = youtube.videos().insert(
			part=",".join(request_body.keys()),
			body=request_body,
			media_body=MediaFileUpload(video_file_path, mimetype='video/mp4', resumable=True),
			#onBehalfOfContentOwnerChannel=CHANNEL_ID,
			#onBehalfOfContentOwner=OWNER_ID
		)
		# pprint.pprint(json.loads(request.to_json()))

		# Execute the request
		response = upload_video.resumable_upload(request)
		self.uploaded_at = datetime.now().replace(second=0, microsecond=0)
		print(f"Uploaded video title: {title}")

	def get_music_clip(self):
		# Settings for each song
		# file: (start_time, volume)
		music_config = {
			"default": (0, 0.5),
			"blade_runner_synth.mp3": (4, 0.5),
			"paris_drill_trimmed.mp3": (0, 0.3),
			"paris.mp3": (0, 0.55)
		}
		start, vol = music_config["default"]
		if self.music_file in music_config:
			start_vol = music_config[self.music_file]

		music = mpy.AudioFileClip(audio_path + self.music_file)
		music = music.subclip(start, None)
		music = music.fx(volumex, vol)
		print(f"loaded music: {self.music_file}")
		print(f"music duration: {music.duration}s")
		return music

	## Note: maybe these should go in the higher-level file
	@staticmethod
	def video_from_pd_row():
		''' Returns a new video object from a csv row from pandas'''
		pass
		return Video()

	def pd_row_from_video(self):
		''' Returns a new pd dataframe row from a video'''
		pass



		

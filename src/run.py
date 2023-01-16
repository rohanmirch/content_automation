from video import Video
from datetime import date, datetime
import pandas as pd
import argparse
from sheets import Sheets

db_path = "../db/"
csv_file = "fact_videos.csv"
DAILY_UPLOAD_LIMIT = 3

SPREADSHEET_ID = '1lm6ngv02kq97fprhbTa98lI3fI5U9Pr6dPweEkitZeo'
SHEET_NAME = 'fact_videos'

def run(run_uploads = False):

	# Get and filter csv from google sheets
	g_sheet =  Sheets(SPREADSHEET_ID)
	df = g_sheet.get_df_from_sheet(SHEET_NAME)
	df, non_empty_df = process_and_filter_df(df)

	# Get a list of all videos
	videos = []
	for index, row in non_empty_df.iterrows():
		try:
			videos.append(row_to_video(row))
		except Exception as e:
			print("Error converting row to video: {}".format(e))

	# Create videos that need to be created
	for v in videos:
		if v.created_at is None:
			try:
				v.create_video(save_video=True)
				update_row_from_video(df, v)
			except Exception as e:
				print("Error creating video: {}".format(e))
	
	# Upload the videos to youtube that havent been uploaded yet (up to 3)
	if run_uploads:
		print("Running upload loop")
		uploaded = get_uploaded_today_count(videos)
		print(f"Daily upload count before: {uploaded}")
		for v in videos:
			if uploaded >= 3:
				break
			if v.uploaded_at is None:
				try:
					v.upload_to_youtube(schedule = True)
					update_row_from_video(df, v)
				except Exception as e:
					print("Error uploading video: {}".format(e))

				uploaded += 1
		print(f"Daily upload count after: {uploaded}")

	# Update the csv and the google sheet
	df.to_csv(db_path + csv_file, index = False)
	g_sheet.update_sheet_from_df(df, SHEET_NAME)

def load_and_filter_csv(df):
	''' Helper function to load the csv and filter out the rows with empty entries.'''
	df = pd.read_csv(db_path + csv_file)
	return process_and_filter_df(df)

def process_and_filter_df(df):
	''' Helper function to process the timestamp rows and filter out the rows with empty entries.'''
	df["post_date"] = pd.to_datetime(df["post_date"]).dt.date
	df["created_at"] = pd.to_datetime(df["created_at"])
	df["uploaded_at"] = pd.to_datetime(df["uploaded_at"])
	df.index = df["id"]

	# Get a list of videos from the csv
	non_empty_df = df[~(pd.isnull(df["background"]) |
						pd.isnull(df["title"]) |
						pd.isnull(df["post_date"]) | 
						pd.isnull(df["music_file"]))]

	return df, non_empty_df


def row_to_video(row):
	'''Takes in a pd.Series row from a dataframe and returns a video object'''
	texts = []
	for key in row.index:
		if "text" in key and not pd.isnull(row[key]):
			texts.append(row[key])
			
	content_dict = {
		"title": row["title"],
		"description": row["description"],
		"tags": row["tags"].replace(", ", ",").split(","),
		"texts": texts
	}
	
	return Video( 
		id = 0 if pd.isnull(row["id"]) else int(row["id"]),
		post_date = row["post_date"],
		created_at = None if pd.isnull(row["created_at"]) else row["created_at"].to_pydatetime(),
		uploaded_at = None if pd.isnull(row["uploaded_at"]) else row["uploaded_at"].to_pydatetime(),
		music_file = row["music_file"],
		background = row["background"],
		content = content_dict  
	)

def update_row_from_video(df, video):
	video_id = str(video.id)
	if video.created_at is not None:
		df.loc[video_id, "created_at"] = video.created_at
	if video.uploaded_at is not None:
		df.loc[video_id, "uploaded_at"] = video.uploaded_at

def get_uploaded_today_count(videos):
	uploaded_today = 0
	for v in videos:
		if v.uploaded_at is not None:
			if v.uploaded_at.date() == date.today():
				uploaded_today += 1
	return uploaded_today

if __name__ == "__main__":
	
	print(f"\nRunning script {datetime.now()}")
	parser = argparse.ArgumentParser()
	parser.add_argument('--run-uploads', default="False")
	args = parser.parse_args()

	run(run_uploads=args.run_uploads == 'True')





import upload_video
import sys

if __name__ == "__main__":
	print("hello")
	print(sys.argv[0])
	# Create a YouTube service object
	youtube = upload_video.get_authenticated_service()
	youtube.youtubePartner.contentOwners.list(fetchMine=true)


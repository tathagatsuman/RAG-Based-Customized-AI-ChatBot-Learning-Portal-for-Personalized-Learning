from app import extract_video_transcripts


def start_transcript(content_id):
    extract_video_transcripts.delay(content_id)
    return {"message": "Transcript extraction task started!"}

if __name__ == "__main__":
    start_transcript(1)
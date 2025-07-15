from googleapiclient.discovery import build
import sys

# --- REPLACE THIS WITH YOUR ACTUAL YOUTUBE API KEY ---
YOUTUBE_API_KEY = 'AIzaSyD3L3TvxKsyWFcxPoDynigzey-cWyAjakE' 
# --- END REPLACE ---

# Test search query
TEST_QUERY = 'Python programming tutorial'
MAX_RESULTS = 3

def test_youtube_api(api_key, query, max_results):
    if api_key != 'AIzaSyD3L3TvxKsyWFcxPoDynigzey-cWyAjakE' or not api_key:
        print("ERROR: Please replace the API key with your actual YouTube API key.")
        return

    print(f"Attempting to search YouTube for: '{query}'")
    try:
        # Build the YouTube API service object
        youtube = build('youtube', 'v3', developerKey=api_key)

        # Perform the search
        search_response = youtube.search().list(
            q=query,
            type='video',
            part='id,snippet',
            maxResults=max_results
        ).execute()

        videos_found = search_response.get('items', [])

        if videos_found:
            print(f"\nSUCCESS! Found {len(videos_found)} videos:")
            for i, search_result in enumerate(videos_found):
                video_id = search_result['id']['videoId']
                title = search_result['snippet']['title']
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                print(f"  {i+1}. Title: {title}")
                print(f"     URL: {video_url}")
        else:
            print("\nSUCCESS, but no videos found for this specific query. (API key is likely working)")

    except Exception as e:
        print(f"\nERROR: Failed to connect to YouTube API or search for '{query}':")
        print(f"  Type: {type(e).__name__}")
        print(f"  Message: {e}")
        print("\nCommon reasons for failure:")
        print("  - Incorrect API key.")
        print("  - YouTube Data API v3 not enabled in your Google Cloud Project.")
        print("  - Daily quota exceeded (check Google Cloud Console Metrics for YouTube Data API).")
        print("  - Network issues.")

if __name__ == '__main__':
    test_youtube_api(YOUTUBE_API_KEY, TEST_QUERY, MAX_RESULTS)

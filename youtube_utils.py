# youtube_utils.py

from googleapiclient.discovery import build
from typing import List, Dict, Optional, Tuple
import re
from models import User, Course, StudentGrade

# Function to get configuration from Flask app context
def get_youtube_api_key(app_config):
    return app_config.get('AIzaSyD3L3TvxKsyWFcxPoDynigzey-cWyAjakE')

def search_youtube_videos(query: str, api_key: str, max_results: int = 3) -> List[Dict]:
    """
    Searches YouTube for videos related to the given query.
    Returns a list of dictionaries with video titles and URLs.
    """
    if not api_key:
        print("ERROR: YouTube API Key is not configured in config.py or is empty.")
        return []

    try:
        youtube = build('youtube', 'v3', developerKey=api_key)

        search_response = youtube.search().list(
            q=query,
            type='video',
            part='id,snippet',
            maxResults=max_results
        ).execute()

        videos = []
        for search_result in search_response.get('items', []):
            video_id = search_result['id']['videoId']
            title = search_result['snippet']['title']
            # --- THE CORRECTED AND WORKING URL CONSTRUCTION ---
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            # --- END CORRECTED URL FIX ---
            
            thumbnail_url = search_result['snippet']['thumbnails']['medium']['url'] # Using 'medium' quality
            
            videos.append({
                'title': title,
                'url': video_url,
                'thumbnail': thumbnail_url
            })
        
        print(f"DEBUG: YOUTUBE_API: Found {len(videos)} YouTube videos for query: '{query}'")
        return videos

    except Exception as e:
        print(f"ERROR: YOUTUBE_API: Failed to search YouTube for '{query}': {e}")
        # Check for common API key errors
        if "API key not valid" in str(e) or "quotaExceeded" in str(e) or "invalid_grant" in str(e):
             print("Please double-check your YouTube API key configuration, ensure 'YouTube Data API v3' is enabled, and check your daily quota in Google Cloud Console.")
        return []

def recommend_youtube_videos(
    user_id: int, 
    course_id: int, 
    chapter_name: str, 
    exam_mark: float, 
    llm_instance,
    app_config
) -> Tuple[str, List[Dict]]:
    print(f"DEBUG: YT_RECO: Function called for user_id={user_id}, course_id={course_id}, chapter={chapter_name}, mark={exam_mark}")

    user_data = User.find_by_id(user_id)
    course_data = Course.get_course_by_id(course_id)
    grades_for_course = StudentGrade.get_grades_by_user_course(user_id, course_id)

    if not user_data or not course_data:
        print("DEBUG: YT_RECO: User or course data not found. Returning error message.")
        return "Could not retrieve user or course information. Please check if user and course exist and are correctly linked.", []

    grades_context = ""
    if grades_for_course:
        grades_context = "\nPrevious Grades:\n"
        for grade_entry in grades_for_course:
            grades_context += f"- Chapter: {grade_entry['chapter_name']}, Mark: {grade_entry['exam_mark']}%\n"

    try: 
        prompt = f"""
You are an AI tutor specializing in personalized learning. Your goal is to suggest highly relevant YouTube tutorials or channels to help a student improve.

Here is the student's information:
- Student Name: {user_data.name}
- Course: {course_data['name']}
- Specific Chapter/Topic they are struggling with: {chapter_name}
- Their recent exam mark for this course/topic: {exam_mark}%
{grades_context}

Based on this information, provide a concise explanation of *why* these videos would be helpful (e.g., "Given your {exam_mark}% in {chapter_name}, these videos should clarify...", or "To reinforce your understanding of {chapter_name}...").

Then, determine the BEST concise search query for YouTube to find relevant video tutorials or channels. Output this query using the exact tag: [Youtube: <your search query>].

Example:
Explanation: Given your 65% in Algebra, these videos should clarify solving quadratic equations.
[Youtube: Algebra quadratic equations tutorial]

Ensure your response is helpful and directly leads to a relevant YouTube search. The YouTube search query should be specific and effective.
"""
        messages_for_llm = [
            {"role": "system", "content": "You are an expert tutor recommending YouTube videos."},
            {"role": "user", "content": prompt}
        ]
        print(f"DEBUG: YT_RECO: Prompt length: {len(prompt)} characters.")
        llm_max_tokens_calc = app_config.get('LLM_N_CTX', 4096) - len(prompt) - 50
        print(f"DEBUG: YT_RECO: Calculated max_tokens for LLM: {llm_max_tokens_calc}")
        if llm_max_tokens_calc <= 0:
            print("ERROR: YT_RECO: Calculated max_tokens is too low (<=0). LLM call will likely fail or generate nothing.")
            return "Prompt too long for LLM context. Cannot generate recommendations.", []
            

    except Exception as e:
        print(f"ERROR: YT_RECO: Error during prompt construction: {e}")
        return "Sorry, there was an error preparing the recommendation request for the LLM.", []


    llm_response_text = ""
    try:
        print("DEBUG: YT_RECO: Attempting LLM call for query generation.")
        response = llm_instance.create_chat_completion(
            messages=messages_for_llm,
            max_tokens=llm_max_tokens_calc,
            temperature=0.7,
            top_p=0.9,
            stream=False
        )
        llm_response_text = response['choices'][0]['message']['content']
        print(f"DEBUG: YT_RECO: LLM response received: {llm_response_text}")

    except Exception as e:
        print(f"ERROR: YT_RECO: LLM failed to generate YouTube search query: {e}")
        return "Sorry, I couldn't generate video recommendations at this time. The AI tutor encountered an error during LLM processing.", []

    youtube_search_query = None
    explanation_text = llm_response_text
    youtube_match = re.search(r'\[Youtube:\s*(.*?)]', llm_response_text, re.IGNORECASE)
    
    if youtube_match:
        youtube_search_query = youtube_match.group(1).strip()
        explanation_text = re.sub(r'\[Youtube:\s*(.*?)]', '', explanation_text, flags=re.IGNORECASE).strip()
        print(f"DEBUG: YT_RECO: Parsed YouTube search query: '{youtube_search_query}'")
    else:
        print("DEBUG: YT_RECO: LLM did not provide a YouTube search tag. Returning fallback message.")
        explanation_text += "\n\n*(The AI tutor was unable to find a specific YouTube search query. Please try rephrasing your request.)*"
        return explanation_text, []

    if youtube_search_query:
        print(f"DEBUG: YT_RECO: Proceeding to search YouTube with query: '{youtube_search_query}'")
        api_key = get_youtube_api_key(app_config)
        max_results = app_config.get('YOUTUBE_MAX_RESULTS', 3)
        
        videos = search_youtube_videos(youtube_search_query, api_key, max_results)
        
        if videos:
            print(f"DEBUG: YT_RECO: Found {len(videos)} videos. Returning results.")
            return explanation_text, videos
        else:
            print(f"DEBUG: YT_RECO: No videos found by YouTube search for query '{youtube_search_query}'. Returning fallback message.")
            return explanation_text + "\n\n*(No relevant YouTube videos found for this topic.)*", []
    
    print("DEBUG: YT_RECO: Reached final fallback return. This path should ideally not be hit unless previous logic is flawed.")
    return explanation_text, []